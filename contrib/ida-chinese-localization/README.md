# IDA Chinese Localization

This directory contains the current Chinese localization assets used in the local IDA setup:

- `idapythonrc.py`: Qt UI text translation script loaded by IDA at startup
- `translations.json`: translation dictionary consumed by `idapythonrc.py`

## Install

1. Copy `idapythonrc.py` to `~/.idapro/idapythonrc.py`
2. Copy `translations.json` to `<IDA_DIR>/plugins/translations.json`
3. Restart IDA

Example:

```bash
cp contrib/ida-chinese-localization/idapythonrc.py ~/.idapro/idapythonrc.py
cp contrib/ida-chinese-localization/translations.json /path/to/ida/plugins/translations.json
```

## What It Translates

- Main Qt UI widgets such as menus, actions, dialog titles, labels, buttons, tabs
- Dynamically generated dialog text handled by rules in `idapythonrc.py`

It does not guarantee translation of every low-level console/log message emitted by IDA core or third-party native plugins.

## Compatibility

Tested environment:

- IDA Pro `9.3`
- Linux
- IDAPython `3.11`
- Qt binding: `PySide6`

Compatibility notes:

- This is not a universal "all versions" pack.
- It is most likely to work on nearby `9.x` versions where IDA still uses `PySide6` and similar widget text.
- It is not guaranteed for older branches such as `8.x` and below.
  Those versions may use different Python/Qt bindings and different UI strings.
- `translations.json` is version-sensitive.
  When IDA or plugins change UI wording, new keys must be added.
- `idapythonrc.py` also contains some dynamic translation rules, which improves cross-version tolerance, but it is still not "one file for every version".

## Maintenance

When new untranslated UI text appears:

1. Reproduce it in IDA
2. Check `~/.idapro/untranslated_ui_texts.jsonl`
3. Add fixed strings to `translations.json`
4. If the text contains paths, addresses, counters, or other variable parts, add a dynamic rule to `idapythonrc.py`
