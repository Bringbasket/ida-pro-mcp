# IDA Pro MCP

[English](./README.md) | 简体中文

简单的 [MCP 服务器](https://modelcontextprotocol.io/introduction)，让 AI 助手能够在 IDA Pro 中进行逆向分析。

https://github.com/user-attachments/assets/6ebeaa92-a9db-43fa-b756-eececce2aca0

视频中使用的二进制文件和提示词可在 [mcp-reversing-dataset](https://github.com/mrexodia/mcp-reversing-dataset) 仓库获取。

## 文档

- **[工具参考手册](./TOOLS.zh-CN.md)**：所有 59 个 MCP 工具的详细文档，包含使用示例和调用原理

## 环境要求

- [Python](https://www.python.org/downloads/) (**3.11 或更高版本**)
  - 使用 `idapyswitch` 切换到最新的 Python 版本
- [IDA Pro](https://hex-rays.com/ida-pro) (8.3 或更高版本，推荐 9.x)，**不支持 IDA Free**
- 支持的 MCP 客户端（选择一个你喜欢的）
  - [Amazon Q Developer CLI](https://aws.amazon.com/q/developer/)
  - [Augment Code](https://www.augmentcode.com/)
  - [Claude](https://claude.ai/download)
  - [Claude Code](https://www.anthropic.com/code)
  - [Cline](https://cline.bot)
  - [Codex](https://github.com/openai/codex)
  - [Copilot CLI](https://docs.github.com/en/copilot)
  - [Crush](https://github.com/charmbracelet/crush)
  - [Cursor](https://cursor.com)
  - [Gemini CLI](https://google-gemini.github.io/gemini-cli/)
  - [Kilo Code](https://www.kilocode.com/)
  - [Kiro](https://kiro.dev/)
  - [LM Studio](https://lmstudio.ai/)
  - [Opencode](https://opencode.ai/)
  - [Qodo Gen](https://www.qodo.ai/)
  - [Qwen Coder](https://qwenlm.github.io/qwen-code-docs/)
  - [Roo Code](https://roocode.com)
  - [Trae](https://trae.ai/)
  - [VS Code](https://code.visualstudio.com/)
  - [VS Code Insiders](https://code.visualstudio.com/insiders)
  - [Warp](https://www.warp.dev/)
  - [Windsurf](https://windsurf.com)
  - [Zed](https://zed.dev/)
  - [其他 MCP 客户端](https://modelcontextprotocol.io/clients#example-clients)：运行 `ida-pro-mcp --config` 获取客户端的 JSON 配置。

## 安装

安装最新版本的 IDA Pro MCP 包：

```sh
pip uninstall ida-pro-mcp
pip install https://github.com/Bringbasket/ida-pro-mcp/archive/refs/heads/main.zip
```

配置 MCP 服务器并安装 IDA 插件：

```
ida-pro-mcp --install
```

**重要**：确保完全重启 IDA 和你的 MCP 客户端以使安装生效。某些客户端（如 Claude）在后台运行，需要从托盘图标退出。

https://github.com/user-attachments/assets/65ed3373-a187-4dd5-a807-425dca1d8ee9

_注意_：你需要在 IDA 中加载二进制文件后，插件菜单才会显示。

## 提示词工程

大语言模型容易产生幻觉，你需要在提示词中明确指示。对于逆向工程，整数和字节之间的转换尤其容易出问题。以下是一个最小示例提示词，如果你有更好的提示词效果，欢迎讨论或提交 issue：

```md
你的任务是在 IDA Pro 中分析一个 crackme。你可以使用 MCP 工具获取信息。一般使用以下策略：

- 检查反编译结果并添加注释记录你的发现
- 将变量重命名为更有意义的名称
- 必要时修改变量和参数类型（特别是指针和数组类型）
- 将函数名改为更具描述性的名称
- 如果需要更多细节，反汇编函数并添加注释记录你的发现
- 永远不要自己转换数字进制。必要时使用 `int_convert` MCP 工具！
- 不要尝试暴力破解，纯粹从反汇编和简单的 Python 脚本推导出解决方案
- 在最后创建 report.md 记录你的发现和采取的步骤
- 当你找到解决方案时，向用户提示反馈你找到的密码
```

这个提示词只是第一次实验，如果你找到改进输出的方法，请分享！

另一个由 [@can1357](https://github.com/can1357) 提供的提示词：

```md
你的任务是创建完整而全面的逆向工程分析。参考 AGENTS.md 了解项目目标，并确保分析符合我们的目的。

使用以下系统方法：

1. **反编译分析**
   - 彻底检查反编译器输出
   - 添加详细注释记录你的发现
   - 专注于理解每个组件的实际功能和目的（不要依赖旧的、不正确的注释）

2. **提高数据库可读性**
   - 将变量重命名为合理的、描述性的名称
   - 必要时纠正变量和参数类型（特别是指针和数组类型）
   - 更新函数名以描述其实际目的

3. **必要时深入研究**
   - 如果需要更多细节，检查反汇编并添加注释记录发现
   - 记录反编译中不清楚的任何底层行为
   - 使用子代理执行详细分析

4. **重要约束**
   - 永远不要自己转换数字进制 - 必要时使用 int_convert MCP 工具
   - 根据需要使用 MCP 工具获取信息
   - 从实际分析中得出所有结论，而不是假设

5. **文档**
   - 生成全面的 RE/*.md 文件记录你的发现
   - 记录采取的步骤和使用的方法
   - 当用户要求时，确保准确性优先于先前的分析文件
   - 以符合 AGENTS.md 或 CLAUDE.md 中概述的项目目标的方式组织发现
```

讨论提示词并展示真实恶意软件分析的直播：

[![](https://img.youtube.com/vi/iFxNuk3kxhk/0.jpg)](https://www.youtube.com/watch?v=iFxNuk3kxhk)

## 提高 LLM 准确性的技巧

大语言模型（LLM）是强大的工具，但它们有时在复杂的数学计算中会遇到困难，或表现出"幻觉"（编造事实）。确保告诉 LLM 使用 `int_convert` MCP 工具，某些操作你可能还需要 [math-mcp](https://github.com/EthanHenrickson/math-mcp)。

另一个需要记住的是，LLM 在混淆代码上表现不佳。在尝试使用 LLM 解决问题之前，先查看二进制文件，花些时间（自动）移除以下内容：

- 字符串加密
- 导入哈希
- 控制流平坦化
- 代码加密
- 反反编译技巧

你还应该使用 Lumina 或 FLIRT 等工具尝试解析所有开源库代码和 C++ STL，这将进一步提高准确性。

## SSE 传输和无头 MCP

你可以运行 SSE 服务器连接到用户界面，如下所示：

```sh
uv run ida-pro-mcp --transport http://127.0.0.1:8744/sse
```

安装 [`idalib`](https://docs.hex-rays.com/user-guide/idalib) 后，你还可以运行无头 SSE 服务器：

```sh
uv run idalib-mcp --host 127.0.0.1 --port 8745 path/to/executable
```

_注意_：`idalib` 功能由 [Willi Ballenthin](https://github.com/williballenthin) 贡献。


## MCP 资源

**资源**代表可浏览的状态（只读数据），遵循 MCP 的哲学。

**核心 IDB 状态：**
- `ida://idb/metadata` - IDB 文件信息（路径、架构、基址、大小、哈希）
- `ida://idb/segments` - 带权限的内存段
- `ida://idb/entrypoints` - 入口点（main、TLS 回调等）

**UI 状态：**
- `ida://cursor` - 当前光标位置和函数
- `ida://selection` - 当前选择范围

**类型信息：**
- `ida://types` - 所有本地类型
- `ida://structs` - 所有结构体/联合体
- `ida://struct/{name}` - 带字段的结构体定义

**查找：**
- `ida://import/{name}` - 按名称查找导入详情
- `ida://export/{name}` - 按名称查找导出详情
- `ida://xrefs/from/{addr}` - 从地址的交叉引用

## 核心函数

- `lookup_funcs(queries)`：按地址或名称获取函数（自动检测，接受列表或逗号分隔的字符串）。
- `int_convert(inputs)`：将数字转换为不同格式（十进制、十六进制、字节、ASCII、二进制）。
- `list_funcs(queries)`：列出函数（分页、过滤）。
- `list_globals(queries)`：列出全局变量（分页、过滤）。
- `imports(offset, count)`：列出所有导入符号及模块名称（分页）。
- `decompile(addr)`：反编译给定地址的函数。
- `disasm(addr)`：反汇编函数及完整详情（参数、栈帧等）。
- `xrefs_to(addrs)`：获取到地址的所有交叉引用。
- `xrefs_to_field(queries)`：获取到特定结构体字段的交叉引用。
- `callees(addrs)`：获取函数调用的函数。

## 修改操作

- `set_comments(items)`：在反汇编和反编译视图中的地址设置注释。
- `patch_asm(items)`：在地址补丁汇编指令。
- `declare_type(decls)`：在本地类型库中声明 C 类型。
- `define_func(items)`：在地址定义函数。可选指定 `end` 以明确边界。
- `define_code(items)`：在地址将字节转换为代码指令。
- `undefine(items)`：在地址取消定义项目，转换回原始字节。可选指定 `end` 或 `size`。

## 内存读取操作

- `get_bytes(addrs)`：读取地址的原始字节。
- `get_int(queries)`：使用 ty（i8/u64/i16le/i16be等）读取整数值。
- `get_string(addrs)`：读取以 null 结尾的字符串。
- `get_global_value(queries)`：按地址或名称读取全局变量值（自动检测，编译时值）。

## 栈帧操作

- `stack_frame(addrs)`：获取函数的栈帧变量。
- `declare_stack(items)`：在指定偏移创建栈变量。
- `delete_stack(items)`：按名称删除栈变量。

## 结构体操作

- `read_struct(queries)`：读取特定地址的结构体字段值。
- `search_structs(filter)`：按名称模式搜索结构体。

## 反混淆操作

- `unflatten_ollvm(addr, remove_dead_code=True)`：从函数移除 OLLVM 控制流平坦化。分析分发器块并重建原始控制流。
- `analyze_ollvm_dispatcher(addr)`：分析 OLLVM 混淆结构，返回分发器块信息、存储变量和状态信息。

## 调试器操作（扩展）

调试器工具默认隐藏。使用 `?ext=dbg` 查询参数启用：

```
http://127.0.0.1:13337/mcp?ext=dbg
```

**控制：**
- `dbg_start()`：启动调试器进程。
- `dbg_exit()`：退出调试器进程。
- `dbg_continue()`：继续执行。
- `dbg_run_to(addr)`：运行到地址。
- `dbg_step_into()`：单步进入指令。
- `dbg_step_over()`：单步跳过指令。

**断点：**
- `dbg_bps()`：列出所有断点。
- `dbg_add_bp(addrs)`：添加断点。
- `dbg_delete_bp(addrs)`：删除断点。
- `dbg_toggle_bp(items)`：启用/禁用断点。

**寄存器：**
- `dbg_regs()`：所有寄存器，当前线程。
- `dbg_regs_all()`：所有寄存器，所有线程。
- `dbg_regs_remote(tids)`：所有寄存器，特定线程。
- `dbg_gpregs()`：通用寄存器，当前线程。
- `dbg_gpregs_remote(tids)`：通用寄存器，特定线程。
- `dbg_regs_named(names)`：命名寄存器，当前线程。
- `dbg_regs_named_remote(tid, names)`：命名寄存器，特定线程。

**栈和内存：**
- `dbg_stacktrace()`：带模块/符号信息的调用栈。
- `dbg_read(regions)`：从调试进程读取内存。
- `dbg_write(regions)`：向调试进程写入内存。

## 高级分析操作

- `py_eval(code)`：在 IDA 上下文中执行任意 Python 代码（返回包含 result/stdout/stderr 的字典，支持 Jupyter 风格求值）。
- `analyze_funcs(addrs)`：全面的函数分析（反编译、汇编、交叉引用、被调用者、调用者、字符串、常量、基本块）。

## 模式匹配和搜索

- `find_regex(queries)`：用不区分大小写的正则表达式搜索字符串（分页）。
- `find_bytes(patterns, limit=1000, offset=0)`：在二进制中查找字节模式（例如 "48 8B ?? ??"）。最大限制：10000。
- `find_insns(sequences, limit=1000, offset=0)`：在代码中查找指令序列。最大限制：10000。
- `find(type, targets, limit=1000, offset=0)`：高级搜索（立即数、字符串、数据/代码引用）。最大限制：10000。

## 控制流分析

- `basic_blocks(addrs)`：获取带后继和前驱的基本块。

## 类型操作

- `set_type(edits)`：将类型应用于函数、全局变量、局部变量或栈变量。
- `infer_types(addrs)`：使用 Hex-Rays 或启发式方法推断地址的类型。

## 导出操作

- `export_funcs(addrs, format)`：以指定格式导出函数（json、c_header 或 prototypes）。

## 图操作

- `callgraph(roots, max_depth)`：从根函数构建可配置深度的调用图。

## 批处理操作

- `rename(batch)`：统一的批量重命名操作，用于函数、全局变量、局部变量和栈变量（接受带可选 `func`、`data`、`local`、`stack` 键的字典）。
- `patch(patches)`：一次补丁多个字节序列。
- `put_int(items)`：使用 ty（i8/u64/i16le/i16be等）写入整数值。

**主要特性：**

- **类型安全 API**：所有函数使用强类型参数和 TypedDict 模式，以获得更好的 IDE 支持和 LLM 结构化输出
- **批处理优先设计**：大多数操作同时接受单个项目和列表
- **一致的错误处理**：所有批处理操作返回 `[{..., error: null|string}, ...]`
- **基于游标的分页**：搜索函数返回 `cursor: {next: offset}` 或 `{done: true}`（默认限制：1000，强制最大值：10000 以防止令牌溢出）
- **性能**：字符串使用基于 MD5 的失效缓存，避免在大型项目中重复调用 `build_strlist`

## 与其他 MCP 服务器的比较

有几个 IDA Pro MCP 服务器，但我创建了自己的版本，原因如下：

1. 安装应该完全自动化。
2. 其他插件的架构使得快速添加新功能变得困难（太多不必要依赖的样板代码）。
3. 学习新技术很有趣！

如果你想查看它们，这里有一个列表（按我发现它们的顺序）：

- https://github.com/taida957789/ida-mcp-server-plugin（仅 SSE 协议，需要在 IDAPython 中安装依赖项）。
- https://github.com/fdrechsler/mcp-server-idapro（TypeScript 中的 MCP Server，添加新功能需要过多的样板代码）。
- https://github.com/MxIris-Reverse-Engineering/ida-mcp-server（自定义 socket 协议，样板代码）。

欢迎提交 PR 将你的 IDA Pro MCP 服务器添加到此处。

## 开发

添加新功能是一个超级简单和流畅的过程。你只需在 `src/ida_pro_mcp/ida_mcp/api_*.py` 的模块化 API 文件中添加一个新的 `@tool` 函数，你的函数就可以在 MCP 服务器中使用，无需任何额外的样板代码！下面是一个视频，我在不到 2 分钟内添加了 `get_metadata` 函数（包括测试）：

https://github.com/user-attachments/assets/951de823-88ea-4235-adcb-9257e316ae64

测试 MCP 服务器本身：

```sh
npx -y @modelcontextprotocol/inspector
```

这将在 http://localhost:5173 打开一个 Web 界面，允许你与 MCP 工具交互进行测试。

对于测试，我创建了一个指向 IDA 插件的符号链接，然后直接向 `http://localhost:13337/mcp` 发送 JSON-RPC 请求。在[启用符号链接](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development)后，你可以运行以下命令：

```sh
uv run ida-pro-mcp --install
```

生成直接提交到 `main` 的变更日志：

```sh
git log --first-parent --no-merges 1.2.0..main "--pretty=- %s"
```
