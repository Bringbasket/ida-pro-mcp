# IDA Pro MCP 工具详解

[English](./TOOLS.md) | 简体中文

本文档详细介绍 IDA Pro MCP 服务器提供的所有工具，包括每个工具的作用、参数说明和调用原理。

## 目录

- [MCP 工具调用原理](#mcp-工具调用原理)
- [核心函数 (6个)](#核心函数)
- [分析操作 (10个)](#分析操作)
- [修改操作 (6个)](#修改操作)
- [内存操作 (6个)](#内存操作)
- [类型操作 (5个)](#类型操作)
- [栈帧操作 (3个)](#栈帧操作)
- [反混淆操作 (2个)](#反混淆操作)
- [Python 执行 (1个)](#python-执行)
- [调试器操作 (20个)](#调试器操作)

---

## MCP 工具调用原理

### 架构设计

IDA Pro MCP 采用**模块化设计**，工具通过装饰器自动注册：

```python
# 在 api_*.py 文件中定义工具
@tool
@idasync
def lookup_funcs(queries: list[str] | str) -> list[dict]:
    """通过地址或名称获取函数"""
    # 函数实现
    pass
```

### 调用流程

```
AI 客户端 (Claude/Cursor/Windsurf)
    ↓
MCP 协议 (JSON-RPC 2.0)
    ↓
HTTP/SSE 传输层 (端口 13337)
    ↓
MCP Server (zeromcp 框架)
    ↓
@tool 装饰器路由
    ↓
@idasync 同步装饰器
    ↓
IDA Pro 主线程执行
    ↓
返回结果给客户端
```

### 关键组件

1. **@tool 装饰器**: 自动注册函数到 MCP 服务器
2. **@idasync 装饰器**: 确保在 IDA 主线程中执行（IDA API 要求）
3. **TypedDict 参数**: 提供类型安全和 LLM 结构化输出支持
4. **批处理设计**: 大多数操作同时支持单个项目和列表

---

## 核心函数

### 1. lookup_funcs

**作用**: 通过地址或函数名查找函数信息

**参数**:
- `queries`: 地址列表或函数名列表（支持 `0x401000`、`sub_401000`、`main` 等格式）

**返回**:
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

**调用示例**:
```python
# AI 通过 MCP 调用
lookup_funcs(queries=["main", "0x401000"])
```

**原理**: 使用快速路径解析（直接地址/sub_前缀）或 IDA 名称查找 API

---

### 2. int_convert

**作用**: 数字格式转换（十进制、十六进制、字节、ASCII、二进制）

**参数**:
- `inputs`: 数字字符串或转换配置列表
  - `text`: 要转换的数字字符串
  - `size`: 可选，字节大小（自动检测）

**返回**:
```python
[
    {
        "input": "0x41424344",
        "result": {
            "decimal": "1094861636",
            "hexadecimal": "0x41424344",
            "bytes": "44 43 42 41",  # 小端序
            "ascii": "DCBA",
            "binary": "0b1000001010000100100001101000100"
        },
        "error": None
    }
]
```

**用途**: 防止 LLM 在数字转换时产生幻觉

---

### 3. list_funcs

**作用**: 列出所有函数（支持分页和过滤）

**参数**:
- `queries`: 查询配置
  - `offset`: 起始偏移（默认 0）
  - `count`: 返回数量（默认 50）
  - `filter`: 通配符过滤（如 `sub_*`）

**返回**: 分页的函数列表

**原理**: 遍历 `idautils.Functions()`，应用过滤和分页

---

### 4. list_globals

**作用**: 列出全局变量

**参数**: 同 `list_funcs`

**返回**: 全局变量列表

---

### 5. imports

**作用**: 列出导入符号

**参数**:
- `offset`: 起始偏移
- `count`: 返回数量（0 表示全部）

**返回**:
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

**作用**: 使用正则表达式搜索字符串

**参数**:
- `pattern`: 正则表达式模式（不区分大小写）
- `limit`: 最大匹配数（默认 30，最大 500）
- `offset`: 跳过前 N 个匹配

**返回**: 匹配的字符串和地址

**优化**: 使用缓存的字符串列表，避免重复构建

---

## 分析操作

### 7. decompile

**作用**: 反编译函数为伪代码

**参数**:
- `addr`: 函数地址

**返回**:
```python
{
    "addr": "0x401000",
    "code": "int __cdecl main(int argc, char **argv) {\n  printf(\"Hello\\n\");\n  return 0;\n}"
}
```

**原理**: 调用 Hex-Rays 反编译器 API

**超时保护**: 90 秒超时（`@tool_timeout(90.0)`）

---

### 8. disasm

**作用**: 反汇编函数为汇编指令

**参数**:
- `addr`: 函数地址
- `max_instructions`: 最大指令数（默认 5000，最大 50000）
- `offset`: 跳过前 N 条指令
- `include_total`: 是否计算总指令数

**返回**: 汇编代码、栈帧、参数信息

**分页支持**: 通过 `cursor` 字段实现大函数分页

---

### 9. xrefs_to

**作用**: 获取到指定地址的所有交叉引用

**参数**:
- `addrs`: 地址列表
- `limit`: 每个地址的最大引用数（默认 100，最大 1000）

**返回**:
```python
[
    {
        "addr": "0x401000",
        "xrefs": [
            {
                "addr": "0x402000",
                "type": "code",  # code 或 data
                "fn": {"name": "caller_func", ...}
            }
        ],
        "more": False
    }
]
```

---

### 10. xrefs_to_field

**作用**: 获取结构体字段的交叉引用

**参数**:
- `queries`: 查询列表
  - `struct`: 结构体名称
  - `field`: 字段名称

**返回**: 字段引用位置列表

**用途**: 追踪结构体成员的使用情况

---

### 11. callees

**作用**: 获取函数调用的所有函数

**参数**:
- `addrs`: 函数地址列表
- `limit`: 每个函数的最大被调用者数（默认 200，最大 500）

**返回**:
```python
[
    {
        "addr": "0x401000",
        "callees": [
            {
                "addr": "0x402000",
                "name": "printf",
                "type": "external"  # internal 或 external
            }
        ],
        "more": False
    }
]
```

**原理**: 扫描函数中的 call 指令

---

### 12. find_bytes

**作用**: 搜索字节模式（支持通配符）

**参数**:
- `patterns`: 字节模式列表（如 `"48 8B ?? ??"`）
- `limit`: 每个模式的最大匹配数（默认 1000，最大 10000）
- `offset`: 跳过前 N 个匹配

**返回**: 匹配地址列表

**兼容性**: 自动适配 IDA 9.0+ 和旧版本 API

---

### 13. basic_blocks

**作用**: 获取函数的控制流图基本块

**参数**:
- `addrs`: 函数地址列表
- `max_blocks`: 每个函数的最大块数（默认 1000，最大 10000）
- `offset`: 跳过前 N 个块

**返回**:
```python
[
    {
        "addr": "0x401000",
        "blocks": [
            {
                "start": "0x401000",
                "end": "0x401010",
                "size": 16,
                "type": 1,  # 块类型
                "successors": ["0x401010", "0x401020"],
                "predecessors": []
            }
        ],
        "total_blocks": 10
    }
]
```

**用途**: 控制流分析、路径分析

---

### 14. find

**作用**: 高级搜索（立即数、字符串、引用）

**参数**:
- `type`: 搜索类型
  - `"string"`: UTF-8 字符串搜索
  - `"immediate"`: 立即数搜索
  - `"data_ref"`: 数据引用
  - `"code_ref"`: 代码引用
- `targets`: 搜索目标列表
- `limit`: 每个目标的最大匹配数

**立即数搜索原理**:
1. 将值转换为小端序字节
2. 在可执行段搜索字节模式
3. 反向扫描找到指令起始位置
4. 验证是否为立即数操作数

---

### 15. export_funcs

**作用**: 导出函数信息

**参数**:
- `addrs`: 函数地址列表
- `format`: 导出格式
  - `"json"`: JSON 格式
  - `"c_header"`: C 头文件格式
  - `"prototypes"`: 函数原型列表

**用途**: 批量导出函数签名用于其他工具

---

### 16. callgraph

**作用**: 构建调用图

**参数**:
- `roots`: 根函数地址列表
- `max_depth`: 最大深度
- `max_nodes`: 最大节点数（默认 1000，最大 100000）
- `max_edges`: 最大边数（默认 5000，最大 200000）

**返回**: 调用图的节点和边

**用途**: 可视化函数调用关系、影响分析

---

## 修改操作

### 17. set_comments

**作用**: 在反汇编和反编译视图中设置注释

**参数**:
- `items`: 注释操作列表
  - `addr`: 地址
  - `comment`: 注释文本

**原理**: 同时设置反汇编注释和反编译器注释

---

### 18. patch_asm

**作用**: 补丁汇编指令

**参数**:
- `items`: 补丁操作列表
  - `addr`: 地址
  - `asm`: 汇编指令（分号分隔多条）

**返回**: 每个补丁的结果和生成的字节

**安全性**: 自动验证补丁后的字节长度

---

### 19. rename

**作用**: 统一的批量重命名操作

**参数**:
- `batch`: 重命名批次
  - `func`: 函数重命名列表
  - `data`: 全局变量重命名列表
  - `local`: 局部变量重命名列表
  - `stack`: 栈变量重命名列表

**返回**: 每类重命名的成功/失败计数

**优势**: 单次调用完成多种类型的重命名

---

### 20. define_func

**作用**: 在地址定义函数

**参数**:
- `items`: 定义操作列表
  - `addr`: 起始地址
  - `end`: 可选，结束地址（IDA 自动检测边界）

**用途**: 将未识别代码转换为函数

---

### 21. define_code

**作用**: 将字节转换为代码指令

**参数**:
- `items`: 定义操作列表
  - `addr`: 地址

**用途**: 修复未正确反汇编的区域

---

### 22. undefine

**作用**: 取消定义，转换回原始字节

**参数**:
- `items`: 取消定义操作列表
  - `addr`: 地址
  - `end` 或 `size`: 可选，范围

**用途**: 重新分析错误定义的区域

---

## 内存操作

### 23. get_bytes

**作用**: 读取原始字节

**参数**:
- `regions`: 内存区域列表
  - `addr`: 地址
  - `size`: 字节数

**返回**: 十六进制字节字符串

---

### 24. get_int

**作用**: 读取整数值

**参数**:
- `queries`: 读取请求列表
  - `addr`: 地址
  - `ty`: 整数类型（`i8`/`u64`/`i16le`/`i16be` 等）

**支持的类型**:
- 有符号: `i8`, `i16`, `i32`, `i64`
- 无符号: `u8`, `u16`, `u32`, `u64`
- 字节序: `le`（小端，默认）, `be`（大端）

---

### 25. get_string

**作用**: 读取以 null 结尾的字符串

**参数**:
- `addrs`: 地址列表

**返回**: 字符串内容（自动检测编码）

---

### 26. get_global_value

**作用**: 读取全局变量值（编译时值）

**参数**:
- `queries`: 地址或变量名列表

**返回**: 变量的十六进制值

**原理**: 使用类型信息计算变量大小并读取内存

---

### 27. patch

**作用**: 补丁字节

**参数**:
- `patches`: 补丁列表
  - `addr`: 地址
  - `data`: 十六进制数据（空格分隔）

**示例**: `patch([{"addr": "0x401000", "data": "90 90 90"}])`

---

### 28. put_int

**作用**: 写入整数值

**参数**:
- `items`: 写入请求列表
  - `addr`: 地址
  - `ty`: 整数类型
  - `value`: 值字符串（支持 `0x...` 和负数）

**安全性**: 自动验证值范围

---

## 类型操作

### 29. declare_type

**作用**: 声明 C 类型到本地类型库

**参数**:
- `decls`: C 类型声明列表

**示例**:
```python
declare_type(decls=[
    "struct MyStruct { int a; char b[10]; };",
    "typedef unsigned int DWORD;"
])
```

---

### 30. read_struct

**作用**: 读取结构体实例的字段值

**参数**:
- `queries`: 查询列表
  - `addr`: 内存地址
  - `struct`: 结构体名称（可选，自动检测）

**返回**: 结构体布局和每个字段的实际内存值

**用途**: 调试、内存取证

---

### 31. search_structs

**作用**: 搜索结构体

**参数**:
- `filter`: 不区分大小写的子字符串

**返回**: 匹配的结构体名称和定义

---

### 32. set_type

**作用**: 应用类型到函数/变量

**参数**:
- `edits`: 类型编辑列表
  - `addr`: 地址
  - `kind`: 类型（`function`/`global`/`local`/`stack`，自动检测）
  - `ty`: 类型名称或声明
  - `signature`: 函数签名（仅用于 `kind=function`）
  - `variable`: 局部变量名（仅用于 `kind=local`）

**智能检测**: 自动识别是函数、全局变量还是局部变量

---

### 33. infer_types

**作用**: 使用 Hex-Rays 或启发式方法推断类型

**参数**:
- `addrs`: 地址列表

**原理**: 调用 IDA 类型推断引擎

---

## 栈帧操作

### 34. stack_frame

**作用**: 获取函数的栈帧变量

**参数**:
- `addrs`: 函数地址列表

**返回**: 栈变量列表（名称、偏移、类型、大小）

---

### 35. declare_stack

**作用**: 创建栈变量

**参数**:
- `items`: 声明列表
  - `addr`: 函数地址
  - `offset`: 栈偏移
  - `name`: 变量名
  - `ty`: 类型名

---

### 36. delete_stack

**作用**: 删除栈变量

**参数**:
- `items`: 删除列表
  - `addr`: 函数地址
  - `name`: 变量名

---

## 反混淆操作

### 37. unflatten_ollvm

**作用**: 移除 OLLVM 控制流平坦化混淆

**参数**:
- `addr`: 函数地址
- `remove_dead_code`: 是否同时移除死代码（默认 True）

**返回**:
```python
{
    "addr": "0x401000",
    "function": "main",
    "success": True,
    "patches_applied": 15,
    "message": "应用了 15 个控制流补丁。刷新反编译视图(F5)查看结果。"
}
```

**原理**:
1. **生成微代码**: 使用 Hex-Rays 微代码 API
2. **识别分发器**: 找到入度最多的基本块
3. **分析状态变量**: 通过 VALRANGES 找到可能的状态值
4. **匹配状态赋值**: 扫描所有块中的状态赋值语句
5. **重建控制流**: 修改跳转目标，绕过分发器
6. **移除死代码**: 可选，消除不可达代码

**适用场景**: OLLVM 控制流平坦化混淆

---

### 38. analyze_ollvm_dispatcher

**作用**: 分析 OLLVM 混淆结构（不修改）

**参数**:
- `addr`: 函数地址

**返回**:
```python
{
    "addr": "0x401000",
    "function": "main",
    "dispatcher_block": 2,
    "storage_variable": "eax",
    "possible_states": 10,
    "state_assignments": 8,
    "states": [...],      # 前 10 个可能状态
    "assignments": [...]  # 前 10 个赋值
}
```

**用途**: 调试反混淆、理解混淆结构

---

## Python 执行

### 39. py_eval

**作用**: 在 IDA 上下文中执行任意 Python 代码

**参数**:
- `code`: Python 代码字符串

**返回**:
```python
{
    "result": "执行结果",
    "stdout": "标准输出",
    "stderr": "错误输出"
}
```

**安全性**: 标记为 `@unsafe`，需要用户确认

**用途**:
- 快速原型开发
- 自定义分析脚本
- 访问完整的 IDA API

**支持特性**: Jupyter 风格求值（最后一个表达式自动返回）

---

## 调试器操作

**注意**: 调试器工具默认隐藏，需要使用 `?ext=dbg` 查询参数启用。

### 控制操作

#### 40. dbg_start
**作用**: 启动调试器进程

#### 41. dbg_exit
**作用**: 退出调试器进程

#### 42. dbg_continue
**作用**: 继续执行

#### 43. dbg_run_to
**作用**: 运行到指定地址
**参数**: `addr`

#### 44. dbg_step_into
**作用**: 单步进入

#### 45. dbg_step_over
**作用**: 单步跳过

---

### 断点操作

#### 46. dbg_bps
**作用**: 列出所有断点

#### 47. dbg_add_bp
**作用**: 添加断点
**参数**: `addrs` - 地址列表

#### 48. dbg_delete_bp
**作用**: 删除断点
**参数**: `addrs` - 地址列表

#### 49. dbg_toggle_bp
**作用**: 启用/禁用断点
**参数**: `items` - 断点操作列表

---

### 寄存器操作

#### 50. dbg_regs
**作用**: 获取所有寄存器（当前线程）

#### 51. dbg_regs_all
**作用**: 获取所有寄存器（所有线程）

#### 52. dbg_regs_remote
**作用**: 获取指定线程的所有寄存器
**参数**: `tids` - 线程 ID 列表

#### 53. dbg_gpregs
**作用**: 获取通用寄存器（当前线程）

#### 54. dbg_gpregs_remote
**作用**: 获取指定线程的通用寄存器
**参数**: `tids` - 线程 ID 列表

#### 55. dbg_regs_named
**作用**: 获取命名寄存器（当前线程）
**参数**: `names` - 寄存器名称列表

#### 56. dbg_regs_named_remote
**作用**: 获取指定线程的命名寄存器
**参数**: `tid`, `names`

---

### 栈和内存操作

#### 57. dbg_stacktrace
**作用**: 获取调用栈（带模块/符号信息）

#### 58. dbg_read
**作用**: 从调试进程读取内存
**参数**: `regions` - 内存区域列表

#### 59. dbg_write
**作用**: 向调试进程写入内存
**参数**: `regions` - 内存区域和数据列表

---

## 批处理和性能优化

### 批处理设计

大多数工具支持批处理，接受单个项目或列表：

```python
# 单个
xrefs_to(addrs="0x401000")

# 批处理
xrefs_to(addrs=["0x401000", "0x402000", "0x403000"])
```

**优势**:
- 减少 MCP 调用开销
- 单次事务处理
- 一致的错误处理

### 分页机制

搜索和列表工具使用基于游标的分页：

```python
{
    "items": [...],
    "cursor": {
        "next": 1000  # 下一页的偏移
    }
}
# 或
{
    "items": [...],
    "cursor": {
        "done": True  # 没有更多结果
    }
}
```

**限制**:
- 默认限制: 1000
- 强制最大值: 10000（防止令牌溢出）

### 缓存优化

**字符串缓存**: 
- 使用 MD5 检测 IDB 变化
- 避免重复调用 `build_strlist`
- 显著提升大型项目性能

---

## 错误处理

所有批处理操作返回统一的错误格式：

```python
[
    {
        "query": "0x401000",
        "result": {...},
        "error": None  # 成功
    },
    {
        "query": "0xBADADDR",
        "result": None,
        "error": "Invalid address"  # 失败
    }
]
```

**优势**:
- 部分失败不影响整个批次
- 详细的错误信息
- 易于调试

---

## 同步和线程安全

### @idasync 装饰器

IDA Pro 的 API 必须在主线程调用。`@idasync` 确保：

1. 检测当前线程
2. 如果不在主线程，调度到主线程执行
3. 等待结果返回
4. 处理异常和超时

### 超时保护

某些操作（如反编译）可能耗时较长：

```python
@tool_timeout(90.0)  # 90 秒超时
def decompile(addr):
    ...
```

---

## 扩展机制

### 扩展组

某些工具（如调试器）可以通过扩展组隐藏：

```python
@ext("dbg")  # 需要 ?ext=dbg 启用
@tool
def dbg_start():
    ...
```

**用途**:
- 减少工具列表复杂度
- 按需加载高级功能
- 保持核心工具简洁

---

## 开发新工具

### 最小示例

```python
# 在 src/ida_pro_mcp/ida_mcp/api_custom.py

from typing import Annotated
from .rpc import tool
from .sync import idasync

@tool
@idasync
def my_custom_tool(
    addr: Annotated[str, "Function address"],
    option: Annotated[bool, "Some option"] = True
) -> dict:
    """我的自定义工具"""
    # 实现
    return {"result": "success"}
```

### 注册工具

在 `__init__.py` 中导入：

```python
from . import api_custom
```

工具自动可用，无需额外配置！

---

## 总结

IDA Pro MCP 提供 **59 个工具**，覆盖：
- ✅ 静态分析（反编译、反汇编、交叉引用）
- ✅ 动态调试（断点、寄存器、内存）
- ✅ 修改操作（补丁、重命名、类型）
- ✅ 反混淆（OLLVM 控制流平坦化）
- ✅ 批处理和性能优化

通过 MCP 协议，AI 助手可以像人类分析师一样操作 IDA Pro，实现真正的 AI 辅助逆向工程！
