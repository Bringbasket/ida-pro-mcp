# IDA 中文汉化

这个目录存放当前 IDA 本地环境使用的中文汉化资源：

- `idapythonrc.py`：IDA 启动时加载的 Qt 界面文本汉化脚本
- `translations.json`：`idapythonrc.py` 使用的翻译词典

## 安装方法

1. 将 `idapythonrc.py` 复制到 `~/.idapro/idapythonrc.py`
2. 将 `translations.json` 复制到 `<IDA目录>/plugins/translations.json`
3. 重启 IDA

示例：

```bash
cp contrib/ida-chinese-localization/idapythonrc.py ~/.idapro/idapythonrc.py
cp contrib/ida-chinese-localization/translations.json /path/to/ida/plugins/translations.json
```

## 汉化范围

- Qt 主界面控件文本，例如菜单、动作、对话框标题、标签、按钮、标签页
- 由 `idapythonrc.py` 中动态规则处理的可变对话框文本

这套方案不能保证覆盖 IDA 内核或第三方原生插件输出的所有底层控制台日志。

## 兼容性说明

当前验证环境：

- IDA Pro `9.3`
- Linux
- IDAPython `3.11`
- Qt 绑定：`PySide6`

兼容性说明：

- 这不是一个“所有版本通杀”的汉化包。
- 对相邻的 `9.x` 版本，大概率可用，前提是 IDA 仍然使用 `PySide6`，并且界面文本差异不大。
- 对 `8.x` 及更老版本不保证兼容。
  这些版本可能使用不同的 Python/Qt 绑定，也可能有不同的界面文案。
- `translations.json` 对版本比较敏感。
  只要 IDA 或插件修改了界面文本，就需要补充新的词条。
- `idapythonrc.py` 里虽然加入了一部分动态匹配规则，可以提高跨版本兼容性，但它依然不是“一份文件兼容所有版本”。

## 维护方式

当出现新的未翻译界面文本时：

1. 在 IDA 中复现该界面
2. 查看 `~/.idapro/untranslated_ui_texts.jsonl`
3. 将固定文本加入 `translations.json`
4. 如果文本里包含路径、地址、计数器或其他变量部分，就在 `idapythonrc.py` 里补动态规则
