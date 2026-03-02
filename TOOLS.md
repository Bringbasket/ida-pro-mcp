# IDA Pro MCP Tools Reference

English | [简体中文](./TOOLS.zh-CN.md)

This document provides detailed information about all tools available in the IDA Pro MCP server, including their purpose, parameters, and invocation principles.

## Table of Contents

- [MCP Tool Invocation Principles](#mcp-tool-invocation-principles)
- [Core Functions (6 tools)](#core-functions)
- [Analysis Operations (10 tools)](#analysis-operations)
- [Modification Operations (6 tools)](#modification-operations)
- [Memory Operations (6 tools)](#memory-operations)
- [Type Operations (5 tools)](#type-operations)
- [Stack Frame Operations (3 tools)](#stack-frame-operations)
- [Deobfuscation Operations (2 tools)](#deobfuscation-operations)
- [Python Execution (1 tool)](#python-execution)
- [Debugger Operations (20 tools)](#debugger-operations)

---

## MCP Tool Invocation Principles

### Architecture Design

IDA Pro MCP uses a **modular design** where tools are auto-registered via decorators:

```python
# Define tools in api_*.py files
@tool
@idasync
def lookup_funcs(queries: list[str] | str) -> list[dict]:
    """Get function(s) by address or name"""
    # Implementation
    pass
```

### Invocation Flow

```
AI Client (Claude/Cursor/Windsurf)
    ↓
MCP Protocol (JSON-RPC 2.0)
    ↓
HTTP/SSE Transport (Port 13337)
    ↓
MCP Server (zeromcp framework)
    ↓
@tool decorator routing
    ↓
@idasync sync decorator
    ↓
IDA Pro main thread execution
    ↓
Return results to client
```

### Key Components

1. **@tool decorator**: Auto-registers functions to MCP server
2. **@idasync decorator**: Ensures execution in IDA main thread (required by IDA API)
3. **TypedDict parameters**: Provides type safety and LLM structured output support
4. **Batch-first design**: Most operations support both single items and lists

---

## Core Functions

### 1. lookup_funcs

**Purpose**: Find function information by address or name

**Parameters**:
- `queries`: List of addresses or function names (supports formats like `0x401000`, `sub_401000`, `main`)

**Returns**:
```python
[
    {
        "query": "main",
        "fn": {
            "addr": "0x401000",
            "name": "main",
            "size": 256,
            "prototype": "int __cdecl main(int argc, char **argv)"
        },
        "error": None
    }
]
```

**Example**:
```python
# AI calls via MCP
lookup_funcs(queries=["main", "0x401000"])
```

**Principle**: Uses fast-path parsing (direct address/sub_ prefix) or IDA name lookup API

---

### 2. int_convert

**Purpose**: Convert numbers between formats (decimal, hex, bytes, ASCII, binary)

**Parameters**:
- `inputs`: Number strings or conversion configs
  - `text`: Number string to convert
  - `size`: Optional, byte size (auto-detected)

**Returns**:
```python
[
    {
        "input": "0x41424344",
        "result": {
            "decimal": "1094861636",
            "hexadecimal": "0x41424344",
            "bytes": "44 43 42 41",  # Little-endian
            "ascii": "DCBA",
            "binary": "0b1000001010000100100001101000100"
        },
        "error": None
    }
]
```

**Use Case**: Prevent LLM hallucinations during number conversions

---

### 3. list_funcs

**Purpose**: List all functions (with pagination and filtering)

**Parameters**:
- `queries`: Query configs
  - `offset`: Starting offset (default 0)
  - `count`: Number to return (default 50)
  - `filter`: Wildcard filter (e.g., `sub_*`)

**Returns**: Paginated function list

**Principle**: Iterates `idautils.Functions()`, applies filtering and pagination

---

### 4. list_globals

**Purpose**: List global variables

**Parameters**: Same as `list_funcs`

**Returns**: Global variable list

---

### 5. imports

**Purpose**: List imported symbols

**Parameters**:
- `offset`: Starting offset
- `count`: Number to return (0 for all)

**Returns**:
```python
{
    "items": [
        {
            "addr": "0x403000",
            "imported_name": "printf",
            "module": "msvcrt.dll"
        }
    ],
    "cursor": {"done": True}
}
```

---

### 6. find_regex

**Purpose**: Search strings using regex

**Parameters**:
- `pattern`: Regex pattern (case-insensitive)
- `limit`: Max matches (default 30, max 500)
- `offset`: Skip first N matches

**Returns**: Matched strings and addresses

**Optimization**: Uses cached string list to avoid rebuilding

---

## Analysis Operations

### 7. decompile

**Purpose**: Decompile function to pseudocode

**Parameters**:
- `addr`: Function address

**Returns**:
```python
{
    "addr": "0x401000",
    "code": "int __cdecl main(int argc, char **argv) {\n  printf(\"Hello\\n\");\n  return 0;\n}"
}
```

**Principle**: Calls Hex-Rays decompiler API

**Timeout Protection**: 90 second timeout (`@tool_timeout(90.0)`)

---

### 8. disasm

**Purpose**: Disassemble function to assembly

**Parameters**:
- `addr`: Function address
- `max_instructions`: Max instructions (default 5000, max 50000)
- `offset`: Skip first N instructions
- `include_total`: Whether to compute total instruction count

**Returns**: Assembly code, stack frame, argument info

**Pagination**: Uses `cursor` field for large functions

---

### 9. xrefs_to

**Purpose**: Get all cross-references to address(es)

**Parameters**:
- `addrs`: Address list
- `limit`: Max refs per address (default 100, max 1000)

**Returns**:
```python
[
    {
        "addr": "0x401000",
        "xrefs": [
            {
                "addr": "0x402000",
                "type": "code",  # code or data
                "fn": {"name": "caller_func", ...}
            }
        ],
        "more": False
    }
]
```

---

### 10. xrefs_to_field

**Purpose**: Get cross-references to struct fields

**Parameters**:
- `queries`: Query list
  - `struct`: Structure name
  - `field`: Field name

**Returns**: List of field reference locations

**Use Case**: Track structure member usage

---

### 11. callees

**Purpose**: Get all functions called by a function

**Parameters**:
- `addrs`: Function address list
- `limit`: Max callees per function (default 200, max 500)

**Returns**:
```python
[
    {
        "addr": "0x401000",
        "callees": [
            {
                "addr": "0x402000",
                "name": "printf",
                "type": "external"  # internal or external
            }
        ],
        "more": False
    }
]
```

**Principle**: Scans for call instructions in function

---

### 12. find_bytes

**Purpose**: Search byte patterns (supports wildcards)

**Parameters**:
- `patterns`: Byte pattern list (e.g., `"48 8B ?? ??"`)
- `limit`: Max matches per pattern (default 1000, max 10000)
- `offset`: Skip first N matches

**Returns**: List of matching addresses

**Compatibility**: Auto-adapts to IDA 9.0+ and older API versions

---

### 13. basic_blocks

**Purpose**: Get function's control flow graph basic blocks

**Parameters**:
- `addrs`: Function address list
- `max_blocks`: Max blocks per function (default 1000, max 10000)
- `offset`: Skip first N blocks

**Returns**:
```python
[
    {
        "addr": "0x401000",
        "blocks": [
            {
                "start": "0x401000",
                "end": "0x401010",
                "size": 16,
                "type": 1,  # Block type
                "successors": ["0x401010", "0x401020"],
                "predecessors": []
            }
        ],
        "total_blocks": 10
    }
]
```

**Use Case**: Control flow analysis, path analysis

---

### 14. find

**Purpose**: Advanced search (immediates, strings, references)

**Parameters**:
- `type`: Search type
  - `"string"`: UTF-8 string search
  - `"immediate"`: Immediate value search
  - `"data_ref"`: Data references
  - `"code_ref"`: Code references
- `targets`: Search target list
- `limit`: Max matches per target

**Immediate Search Principle**:
1. Convert value to little-endian bytes
2. Search executable segments for byte pattern
3. Scan backward to find instruction start
4. Verify it's an immediate operand

---

### 15. export_funcs

**Purpose**: Export function information

**Parameters**:
- `addrs`: Function address list
- `format`: Export format
  - `"json"`: JSON format
  - `"c_header"`: C header format
  - `"prototypes"`: Function prototype list

**Use Case**: Batch export signatures for other tools

---

### 16. callgraph

**Purpose**: Build call graph

**Parameters**:
- `roots`: Root function address list
- `max_depth`: Maximum depth
- `max_nodes`: Max nodes (default 1000, max 100000)
- `max_edges`: Max edges (default 5000, max 200000)

**Returns**: Call graph nodes and edges

**Use Case**: Visualize function relationships, impact analysis

---

## Modification Operations

### 17. set_comments

**Purpose**: Set comments in both disassembly and decompiler views

**Parameters**:
- `items`: Comment operation list
  - `addr`: Address
  - `comment`: Comment text

**Principle**: Sets both disassembly and decompiler comments

---

### 18. patch_asm

**Purpose**: Patch assembly instructions

**Parameters**:
- `items`: Patch operation list
  - `addr`: Address
  - `asm`: Assembly instructions (semicolon-separated)

**Returns**: Result and generated bytes for each patch

**Safety**: Auto-verifies patched byte length

---

### 19. rename

**Purpose**: Unified batch rename operation

**Parameters**:
- `batch`: Rename batch
  - `func`: Function rename list
  - `data`: Global variable rename list
  - `local`: Local variable rename list
  - `stack`: Stack variable rename list

**Returns**: Success/failure counts per category

**Advantage**: Complete multiple rename types in single call

---

### 20. define_func

**Purpose**: Define function at address

**Parameters**:
- `items`: Define operation list
  - `addr`: Start address
  - `end`: Optional, end address (IDA auto-detects bounds)

**Use Case**: Convert unrecognized code to function

---

### 21. define_code

**Purpose**: Convert bytes to code instructions

**Parameters**:
- `items`: Define operation list
  - `addr`: Address

**Use Case**: Fix incorrectly disassembled regions

---

### 22. undefine

**Purpose**: Undefine items, convert back to raw bytes

**Parameters**:
- `items`: Undefine operation list
  - `addr`: Address
  - `end` or `size`: Optional, range

**Use Case**: Re-analyze incorrectly defined regions

---

## Memory Operations

### 23. get_bytes

**Purpose**: Read raw bytes

**Parameters**:
- `regions`: Memory region list
  - `addr`: Address
  - `size`: Number of bytes

**Returns**: Hex byte string

---

### 24. get_int

**Purpose**: Read integer values

**Parameters**:
- `queries`: Read request list
  - `addr`: Address
  - `ty`: Integer type (`i8`/`u64`/`i16le`/`i16be`, etc.)

**Supported Types**:
- Signed: `i8`, `i16`, `i32`, `i64`
- Unsigned: `u8`, `u16`, `u32`, `u64`
- Endianness: `le` (little-endian, default), `be` (big-endian)

---

### 25. get_string

**Purpose**: Read null-terminated strings

**Parameters**:
- `addrs`: Address list

**Returns**: String content (auto-detects encoding)

---

### 26. get_global_value

**Purpose**: Read global variable values (compile-time values)

**Parameters**:
- `queries`: Address or variable name list

**Returns**: Variable hex value

**Principle**: Uses type information to calculate size and read memory

---

### 27. patch

**Purpose**: Patch bytes

**Parameters**:
- `patches`: Patch list
  - `addr`: Address
  - `data`: Hex data (space-separated)

**Example**: `patch([{"addr": "0x401000", "data": "90 90 90"}])`

---

### 28. put_int

**Purpose**: Write integer values

**Parameters**:
- `items`: Write request list
  - `addr`: Address
  - `ty`: Integer type
  - `value`: Value string (supports `0x...` and negatives)

**Safety**: Auto-validates value range

---

## Type Operations

### 29. declare_type

**Purpose**: Declare C types to local type library

**Parameters**:
- `decls`: C type declaration list

**Example**:
```python
declare_type(decls=[
    "struct MyStruct { int a; char b[10]; };",
    "typedef unsigned int DWORD;"
])
```

---

### 30. read_struct

**Purpose**: Read struct instance field values

**Parameters**:
- `queries`: Query list
  - `addr`: Memory address
  - `struct`: Structure name (optional, auto-detects)

**Returns**: Structure layout with actual memory values per field

**Use Case**: Debugging, memory forensics

---

### 31. search_structs

**Purpose**: Search structures

**Parameters**:
- `filter`: Case-insensitive substring

**Returns**: Matching structure names and definitions

---

### 32. set_type

**Purpose**: Apply types to functions/variables

**Parameters**:
- `edits`: Type edit list
  - `addr`: Address
  - `kind`: Type (`function`/`global`/`local`/`stack`, auto-detects)
  - `ty`: Type name or declaration
  - `signature`: Function signature (for `kind=function`)
  - `variable`: Local variable name (for `kind=local`)

**Smart Detection**: Auto-identifies function, global, or local variable

---

### 33. infer_types

**Purpose**: Infer types using Hex-Rays or heuristics

**Parameters**:
- `addrs`: Address list

**Principle**: Calls IDA type inference engine

---

## Stack Frame Operations

### 34. stack_frame

**Purpose**: Get function's stack frame variables

**Parameters**:
- `addrs`: Function address list

**Returns**: Stack variable list (name, offset, type, size)

---

### 35. declare_stack

**Purpose**: Create stack variables

**Parameters**:
- `items`: Declaration list
  - `addr`: Function address
  - `offset`: Stack offset
  - `name`: Variable name
  - `ty`: Type name

---

### 36. delete_stack

**Purpose**: Delete stack variables

**Parameters**:
- `items`: Delete list
  - `addr`: Function address
  - `name`: Variable name

---

## Deobfuscation Operations

### 37. unflatten_ollvm

**Purpose**: Remove OLLVM control flow flattening obfuscation

**Parameters**:
- `addr`: Function address
- `remove_dead_code`: Whether to also remove dead code (default True)

**Returns**:
```python
{
    "addr": "0x401000",
    "function": "main",
    "success": True,
    "patches_applied": 15,
    "message": "Applied 15 control flow patches. Refresh decompiler view (F5) to see results."
}
```

**Principle**:
1. **Generate Microcode**: Use Hex-Rays microcode API
2. **Identify Dispatcher**: Find basic block with most predecessors
3. **Analyze State Variables**: Find possible state values via VALRANGES
4. **Match State Assignments**: Scan all blocks for state assignment statements
5. **Rebuild Control Flow**: Modify jump targets to bypass dispatcher
6. **Remove Dead Code**: Optional, eliminate unreachable code

**Use Case**: OLLVM control flow flattening obfuscation

---

### 38. analyze_ollvm_dispatcher

**Purpose**: Analyze OLLVM obfuscation structure (no modifications)

**Parameters**:
- `addr`: Function address

**Returns**:
```python
{
    "addr": "0x401000",
    "function": "main",
    "dispatcher_block": 2,
    "storage_variable": "eax",
    "possible_states": 10,
    "state_assignments": 8,
    "states": [...],      # First 10 possible states
    "assignments": [...]  # First 10 assignments
}
```

**Use Case**: Debug deobfuscation, understand obfuscation structure

---

## Python Execution

### 39. py_eval

**Purpose**: Execute arbitrary Python code in IDA context

**Parameters**:
- `code`: Python code string

**Returns**:
```python
{
    "result": "Execution result",
    "stdout": "Standard output",
    "stderr": "Error output"
}
```

**Safety**: Marked as `@unsafe`, requires user confirmation

**Use Cases**:
- Rapid prototyping
- Custom analysis scripts
- Access full IDA API

**Feature**: Jupyter-style evaluation (last expression auto-returned)

---

## Debugger Operations

**Note**: Debugger tools are hidden by default. Enable with `?ext=dbg` query parameter.

### Control Operations

#### 40. dbg_start
**Purpose**: Start debugger process

#### 41. dbg_exit
**Purpose**: Exit debugger process

#### 42. dbg_continue
**Purpose**: Continue execution

#### 43. dbg_run_to
**Purpose**: Run to address
**Parameters**: `addr`

#### 44. dbg_step_into
**Purpose**: Step into instruction

#### 45. dbg_step_over
**Purpose**: Step over instruction

---

### Breakpoint Operations

#### 46. dbg_bps
**Purpose**: List all breakpoints

#### 47. dbg_add_bp
**Purpose**: Add breakpoints
**Parameters**: `addrs` - Address list

#### 48. dbg_delete_bp
**Purpose**: Delete breakpoints
**Parameters**: `addrs` - Address list

#### 49. dbg_toggle_bp
**Purpose**: Enable/disable breakpoints
**Parameters**: `items` - Breakpoint operation list

---

### Register Operations

#### 50. dbg_regs
**Purpose**: Get all registers (current thread)

#### 51. dbg_regs_all
**Purpose**: Get all registers (all threads)

#### 52. dbg_regs_remote
**Purpose**: Get all registers for specific thread(s)
**Parameters**: `tids` - Thread ID list

#### 53. dbg_gpregs
**Purpose**: Get general-purpose registers (current thread)

#### 54. dbg_gpregs_remote
**Purpose**: Get GP registers for specific thread(s)
**Parameters**: `tids` - Thread ID list

#### 55. dbg_regs_named
**Purpose**: Get named registers (current thread)
**Parameters**: `names` - Register name list

#### 56. dbg_regs_named_remote
**Purpose**: Get named registers for specific thread
**Parameters**: `tid`, `names`

---

### Stack & Memory Operations

#### 57. dbg_stacktrace
**Purpose**: Get call stack (with module/symbol info)

#### 58. dbg_read
**Purpose**: Read memory from debugged process
**Parameters**: `regions` - Memory region list

#### 59. dbg_write
**Purpose**: Write memory to debugged process
**Parameters**: `regions` - Memory regions and data list

---

## Batch Processing & Performance

### Batch Design

Most tools support batching, accepting single items or lists:

```python
# Single
xrefs_to(addrs="0x401000")

# Batch
xrefs_to(addrs=["0x401000", "0x402000", "0x403000"])
```

**Advantages**:
- Reduce MCP call overhead
- Single transaction processing
- Consistent error handling

### Pagination Mechanism

Search and list tools use cursor-based pagination:

```python
{
    "items": [...],
    "cursor": {
        "next": 1000  # Offset for next page
    }
}
# Or
{
    "items": [...],
    "cursor": {
        "done": True  # No more results
    }
}
```

**Limits**:
- Default limit: 1000
- Enforced maximum: 10000 (prevent token overflow)

### Caching Optimization

**String Cache**: 
- Uses MD5 to detect IDB changes
- Avoids repeated `build_strlist` calls
- Significantly improves large project performance

---

## Error Handling

All batch operations return unified error format:

```python
[
    {
        "query": "0x401000",
        "result": {...},
        "error": None  # Success
    },
    {
        "query": "0xBADADDR",
        "result": None,
        "error": "Invalid address"  # Failure
    }
]
```

**Advantages**:
- Partial failures don't affect entire batch
- Detailed error messages
- Easy debugging

---

## Synchronization & Thread Safety

### @idasync Decorator

IDA Pro APIs must be called from main thread. `@idasync` ensures:

1. Detect current thread
2. If not on main thread, schedule to main thread
3. Wait for result
4. Handle exceptions and timeouts

### Timeout Protection

Some operations (like decompilation) may take time:

```python
@tool_timeout(90.0)  # 90 second timeout
def decompile(addr):
    ...
```

---

## Extension Mechanism

### Extension Groups

Some tools (like debugger) can be hidden via extension groups:

```python
@ext("dbg")  # Requires ?ext=dbg to enable
@tool
def dbg_start():
    ...
```

**Use Cases**:
- Reduce tool list complexity
- Load advanced features on-demand
- Keep core tools simple

---

## Developing New Tools

### Minimal Example

```python
# In src/ida_pro_mcp/ida_mcp/api_custom.py

from typing import Annotated
from .rpc import tool
from .sync import idasync

@tool
@idasync
def my_custom_tool(
    addr: Annotated[str, "Function address"],
    option: Annotated[bool, "Some option"] = True
) -> dict:
    """My custom tool"""
    # Implementation
    return {"result": "success"}
```

### Register Tool

Import in `__init__.py`:

```python
from . import api_custom
```

Tool is automatically available, no additional config needed!

---

## Summary

IDA Pro MCP provides **59 tools** covering:
- ✅ Static analysis (decompilation, disassembly, xrefs)
- ✅ Dynamic debugging (breakpoints, registers, memory)
- ✅ Modification operations (patching, renaming, types)
- ✅ Deobfuscation (OLLVM control flow flattening)
- ✅ Batch processing and performance optimization

Through the MCP protocol, AI assistants can operate IDA Pro like human analysts, enabling true AI-assisted reverse engineering!
