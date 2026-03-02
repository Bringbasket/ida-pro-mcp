"""Deobfuscation API Functions - OLLVM control flow flattening removal"""

from typing import Annotated, Optional
import ida_hexrays
import idaapi
import ida_funcs

from .rpc import tool
from .sync import idasync
from .utils import parse_address, get_function

# ============================================================================
# OLLVM Deobfuscation Core Logic
# ============================================================================

JMP_OPCODE_HANDLED = [
    ida_hexrays.m_jnz,
    ida_hexrays.m_jz,
    ida_hexrays.m_jae,
    ida_hexrays.m_jb,
    ida_hexrays.m_ja,
    ida_hexrays.m_jbe,
    ida_hexrays.m_jge,
    ida_hexrays.m_jg,
    ida_hexrays.m_jl,
    ida_hexrays.m_jle,
]


def calc_entropy(value: int) -> bool:
    """Calculate entropy - check if value has enough non-zero bytes"""
    count = 0
    for i in range(4):
        if value >> (i * 8) & 0xFF != 0:
            count += 1
    return count >= 4


def get_mreg_name(reg: int, size: int) -> str:
    """Get microcode register name"""
    return ida_hexrays.get_mreg_name(reg, size)


def change_jmp_target(mblock: ida_hexrays.mblock_t, target_mblock_serial: int):
    """Modify jump target in microcode block"""
    minsn = mblock.tail
    if not minsn:
        return

    # If it's a conditional jump, modify its target
    if minsn.opcode in JMP_OPCODE_HANDLED:
        if minsn.d and minsn.d.t == ida_hexrays.mop_b:
            minsn.d.b = target_mblock_serial
    # If it's unconditional goto
    elif minsn.opcode == ida_hexrays.m_goto:
        if minsn.l and minsn.l.t == ida_hexrays.mop_b:
            minsn.l.b = target_mblock_serial


class Unflattener:
    """OLLVM control flow flattening remover"""

    def __init__(self, mba: ida_hexrays.mba_t, dispatcher_id: int = 0):
        self.mba = mba
        self.dispatcher_id = dispatcher_id
        self.dispatcher_ea = mba.get_mblock(dispatcher_id).start if dispatcher_id > 0 else 0
        self.storage_carrier = None
        self.state_assignments = []
        self.possible_states = []

    def find_dispatcher_id(self):
        """Find dispatcher block by maximum predecessor count"""
        max_input_num = -1
        for i in range(1, self.mba.qty - 1):
            mblock = self.mba.get_mblock(i)
            num_input = mblock.npred()
            if num_input > max_input_num:
                max_input_num = num_input
                self.dispatcher_id = i

    def get_dispatcher_use_compare(self):
        """Find storage variable used in dispatcher comparison"""
        dispatcher_mblock = self.mba.get_mblock(self.dispatcher_id)
        minsn = dispatcher_mblock.tail
        if not minsn or minsn.opcode not in JMP_OPCODE_HANDLED:
            return

        mop_l = minsn.l
        if mop_l.t == ida_hexrays.mop_S:
            self.storage_carrier = f"0x{mop_l.s.off:X}"
        elif mop_l.t == ida_hexrays.mop_r:
            self.storage_carrier = get_mreg_name(mop_l.r, mop_l.size)

    def find_mblock_valranges(self):
        """Find all possible state values from VALRANGES"""

        class ValrangesFilter(ida_hexrays.vd_printer_t):
            def __init__(self):
                ida_hexrays.vd_printer_t.__init__(self)
                self.valranges = []

            def _print(self, indent, line):
                if "VALRANGES" in line or "BLOCK" in line:
                    self.valranges.append(
                        "".join([c if 0x20 <= ord(c) <= 0x7E else "" for c in line])
                    )
                return 1

        vp = ValrangesFilter()
        self.mba._print(vp)

        mblock_id = 0
        for line in vp.valranges:
            if "BLOCK" in line:
                try:
                    mblock_id = int(line.split("BLOCK ")[1].split(" ")[0])
                except:
                    continue
                continue

            if "VALRANGES: " not in line:
                continue

            valranges_value = line.split("VALRANGES: ")[1]
            valranges_list = valranges_value.split(", ")

            for valrange in valranges_list:
                if ":==" not in valrange:
                    continue
                valrange_name = valrange.split(":==")[0]
                try:
                    valrange_value = int(valrange.split(":==")[1], 16)
                except:
                    continue

                if calc_entropy(valrange_value):
                    self.possible_states.append(
                        {
                            "mblock_id": mblock_id,
                            "valrange_name": valrange_name.split(".")[0],
                            "valrange_value": valrange_value,
                        }
                    )

    def find_next_status_in_mblock(self):
        """Find state assignment statements in all blocks"""
        for mblock_id in range(1, self.mba.qty - 1):
            mblock = self.mba.get_mblock(mblock_id)
            minsn = mblock.head

            while minsn:
                if (
                    minsn.opcode == ida_hexrays.m_mov
                    and minsn.l.t == ida_hexrays.mop_n
                    and calc_entropy(minsn.l.nnn.value)
                ):
                    if minsn.d.t == ida_hexrays.mop_r:
                        self.state_assignments.append(
                            {
                                "mblock_id": mblock_id,
                                "storage": get_mreg_name(minsn.d.r, minsn.d.size),
                                "value": minsn.l.nnn.value,
                            }
                        )
                    elif minsn.d.t == ida_hexrays.mop_S:
                        self.state_assignments.append(
                            {
                                "mblock_id": mblock_id,
                                "storage": f"0x{minsn.d.s.off:X}",
                                "value": minsn.l.nnn.value,
                            }
                        )
                minsn = minsn.next

    def find_in_possible_states(
        self, valrange_name: Optional[str] = None, valrange_value: Optional[int] = None
    ):
        """Find matching state in possible states"""
        for flow_block in self.possible_states:
            if valrange_name is not None and valrange_value is not None:
                if (
                    flow_block["valrange_value"] == valrange_value
                    and flow_block["valrange_name"] == valrange_name
                ):
                    return flow_block
            elif valrange_value is not None:
                if flow_block["valrange_value"] == valrange_value:
                    return flow_block
        return None

    def deflat_safe_mode(self):
        """Safe mode: match both storage name and value"""
        patches = 0
        for state_assignment in self.state_assignments:
            flow_block = self.find_in_possible_states(
                valrange_name=state_assignment["storage"],
                valrange_value=state_assignment["value"],
            )
            if flow_block is not None:
                next_mblock_id = flow_block["mblock_id"]
                cur_mblock_id = state_assignment["mblock_id"]
                cur_mblock = self.mba.get_mblock(cur_mblock_id)
                change_jmp_target(cur_mblock, next_mblock_id)
                patches += 1
        return patches

    def deflat(self):
        """Execute deobfuscation"""
        if self.dispatcher_id == 0:
            self.find_dispatcher_id()
        self.get_dispatcher_use_compare()
        self.find_mblock_valranges()
        self.find_next_status_in_mblock()
        return self.deflat_safe_mode()


class RemoveDeadCode(ida_hexrays.minsn_visitor_t):
    """Remove dead code by eliminating unreachable blocks"""

    def __init__(self):
        ida_hexrays.minsn_visitor_t.__init__(self)

    def visit_minsn(self):
        if self.curins.opcode == ida_hexrays.m_jcnd:
            if self.curins.l.t == ida_hexrays.mop_n:
                if self.curins.l.nnn.value == 0:
                    self.curins.opcode = ida_hexrays.m_nop
                    self.curins.l = ida_hexrays.mop_t()
                    self.curins.r = ida_hexrays.mop_t()
                    self.curins.d = ida_hexrays.mop_t()
        return 0


# ============================================================================
# MCP Tools
# ============================================================================


@tool
@idasync
def unflatten_ollvm(
    addr: Annotated[str, "Function address to deobfuscate"],
    remove_dead_code: Annotated[bool, "Also remove dead code (default: true)"] = True,
) -> dict:
    """Remove OLLVM control flow flattening from a function"""
    try:
        ea = parse_address(addr)
        func = idaapi.get_func(ea)

        if not func:
            return {"addr": addr, "success": False, "error": "No function found"}

        # Check if Hex-Rays decompiler is available
        if not ida_hexrays.init_hexrays_plugin():
            return {
                "addr": addr,
                "success": False,
                "error": "Hex-Rays decompiler not available",
            }

        # Get microcode
        mbr = ida_hexrays.mba_ranges_t()
        mbr.ranges.push_back(ida_hexrays.range_t(func.start_ea, func.end_ea))

        hf = ida_hexrays.hexrays_failure_t()
        mba = ida_hexrays.gen_microcode(
            mbr,
            hf,
            None,
            ida_hexrays.DECOMP_NO_WAIT | ida_hexrays.DECOMP_NO_CACHE,
            ida_hexrays.MMAT_GLBOPT1,
        )

        if not mba:
            return {
                "addr": addr,
                "success": False,
                "error": f"Failed to generate microcode: {hf.str}",
            }

        patches = 0

        # Remove dead code first if requested
        if remove_dead_code:
            rdc = RemoveDeadCode()
            mba.for_all_topinsns(rdc)

        # Unflatten OLLVM
        unflat = Unflattener(mba)
        patches = unflat.deflat()

        # Trigger reanalysis
        func_name = ida_funcs.get_func_name(func.start_ea)

        return {
            "addr": addr,
            "function": func_name,
            "success": True,
            "patches_applied": patches,
            "message": f"Applied {patches} control flow patches. Refresh decompiler view (F5) to see results.",
        }

    except Exception as e:
        return {"addr": addr, "success": False, "error": str(e)}


@tool
@idasync
def analyze_ollvm_dispatcher(
    addr: Annotated[str, "Function address to analyze"],
) -> dict:
    """Analyze OLLVM obfuscation structure in a function"""
    try:
        ea = parse_address(addr)
        func = idaapi.get_func(ea)

        if not func:
            return {"addr": addr, "error": "No function found"}

        if not ida_hexrays.init_hexrays_plugin():
            return {"addr": addr, "error": "Hex-Rays decompiler not available"}

        # Get microcode
        mbr = ida_hexrays.mba_ranges_t()
        mbr.ranges.push_back(ida_hexrays.range_t(func.start_ea, func.end_ea))

        hf = ida_hexrays.hexrays_failure_t()
        mba = ida_hexrays.gen_microcode(
            mbr,
            hf,
            None,
            ida_hexrays.DECOMP_NO_WAIT | ida_hexrays.DECOMP_NO_CACHE,
            ida_hexrays.MMAT_GLBOPT1,
        )

        if not mba:
            return {"addr": addr, "error": f"Failed to generate microcode: {hf.str}"}

        unflat = Unflattener(mba)
        unflat.find_dispatcher_id()
        unflat.get_dispatcher_use_compare()
        unflat.find_mblock_valranges()
        unflat.find_next_status_in_mblock()

        func_name = ida_funcs.get_func_name(func.start_ea)

        return {
            "addr": addr,
            "function": func_name,
            "dispatcher_block": unflat.dispatcher_id,
            "storage_variable": unflat.storage_carrier,
            "possible_states": len(unflat.possible_states),
            "state_assignments": len(unflat.state_assignments),
            "states": unflat.possible_states[:10],  # First 10 states
            "assignments": unflat.state_assignments[:10],  # First 10 assignments
        }

    except Exception as e:
        return {"addr": addr, "error": str(e)}
