# -*- coding: utf-8 -*-
"""
IDA Pro 自动初始化脚本
在 IDA 启动时自动加载中文汉化
直接遍历 Qt Widget 替换文本
"""

import json
import os
import re
import time

def load_chinese_translation():
    """加载中文翻译"""
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        from shiboken6 import isValid
        
        # 加载翻译字典
        trans_file = "/home/xd/ida-pro-9.3/plugins/translations.json"
        missing_log_file = os.path.expanduser("~/.idapro/untranslated_ui_texts.jsonl")
        if not os.path.exists(trans_file):
            print("[IDA汉化] 错误：找不到翻译文件")
            return
        
        with open(trans_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        # 安装 QTranslator（对新创建的 widget 生效）
        class ChineseTranslator(QtCore.QTranslator):
            def __init__(self, trans_dict):
                super().__init__()
                self.trans_dict = trans_dict
            def translate(self, context, sourceText, disambiguation, n):
                if sourceText in self.trans_dict:
                    return self.trans_dict[sourceText]
                return sourceText
        
        app = QtWidgets.QApplication.instance()
        if not app:
            print("[IDA汉化] 警告：QApplication 未就绪")
            return
        
        translator = ChineseTranslator(translations)
        app.installTranslator(translator)
        # 保持 translator 引用，避免函数返回后被 GC 回收。
        app._cn_translator = translator

        logged_missing = set()
        if os.path.exists(missing_log_file):
            try:
                with open(missing_log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            text = item.get("text")
                            if text:
                                logged_missing.add(text)
                        except Exception:
                            continue
            except Exception:
                pass

        def is_alive(obj):
            """判断 Qt/PySide 对象是否仍然有效。"""
            try:
                return obj is not None and isValid(obj)
            except Exception:
                return False

        def is_meaningful_text(text):
            """过滤无意义或高噪音文本，避免日志被路径/符号刷满。"""
            if not text:
                return False
            text = str(text).strip()
            if not text:
                return False
            if len(text) > 400:
                return False
            if text.startswith("/") or text.startswith("\\"):
                return False
            if text.startswith("0x"):
                return False
            if re.search(r"[\u4e00-\u9fff]", text):
                return False
            if "http://" in text or "https://" in text:
                return False
            if re.fullmatch(r"[0-9A-Fa-f: .()_-]+", text):
                return False
            if re.match(r"^IDA v\d", text):
                return False
            if re.match(r"^IDA - .+/.+", text):
                return False
            if re.match(r"^Version \d", text):
                return False
            if re.match(r"^\(c\) \d{4} ", text):
                return False
            if re.match(r"^AU:\s+", text):
                return False
            if re.match(r"^Disk:\s*\d", text):
                return False
            if re.match(r"^Navigator Scale:", text):
                return False
            if re.match(r"^\(Synchronized with ", text):
                return False
            if re.match(r"^[A-Z]{2}:[0-9A-Fa-f]+$", text):
                return False
            if re.search(r"seg[0-9A-Fa-f]+:", text):
                return False
            return any(("a" <= ch.lower() <= "z") for ch in text)

        def lookup_variants(text):
            """生成常见 UI 文本变体，提高匹配率。"""
            if not text:
                return []

            variants = []

            def add_variant(value):
                value = str(value).strip()
                if value and value not in variants:
                    variants.append(value)

            add_variant(text)
            normalized = " ".join(str(text).split()).strip()
            add_variant(normalized)

            dehtml = re.sub(r"<[^>]+>", "", normalized).strip()
            add_variant(dehtml)

            if "&" in normalized:
                add_variant(normalized.replace("&&", "\0").replace("&", "").replace("\0", "&"))
                add_variant(re.sub(r"\(&.\)", "", normalized).replace("&&", "\0").replace("&", "").replace("\0", "&").strip())

            add_variant(re.sub(r"\s*\(&.\)\s*", "", normalized).strip())
            add_variant(re.sub(r"\s*\([A-Z]\)\s*$", "", normalized).strip())
            add_variant(re.sub(r"\s*\([A-Z]\)\.\.\.$", "...", normalized).strip())
            add_variant(re.sub(r"\s*\(&.\)\.\.\.$", "...", normalized).strip())

            if "..." in normalized:
                add_variant(normalized.replace("...", "…"))
            if "…" in normalized:
                add_variant(normalized.replace("…", "..."))

            return variants

        def translate_dynamic_text(text):
            """处理带路径、编号等变量的动态界面文本。"""
            if not text:
                return None

            text = str(text)

            patterns = [
                (
                    r"^String literal at (.+)$",
                    lambda m: f"{m.group(1)} 处的字符串字面量",
                ),
                (
                    r"^TextArrows for (.+)$",
                    lambda m: f"{m.group(1)} 的文本箭头",
                ),
                (
                    r"^Run probe \((\d+)\)$",
                    lambda m: f"运行探测（{m.group(1)}）",
                ),
                (
                    r"^Apply signatures \((\d+)\)$",
                    lambda m: f"应用签名（{m.group(1)}）",
                ),
                (
                    r"^Can't find input file '(.+)'$",
                    lambda m: f"找不到输入文件 '{m.group(1)}'",
                ),
                (
                    r"^Unpacking the database\n(.+)$",
                    lambda m: f"正在解包数据库\n{m.group(1)}",
                ),
                (
                    r"^Database (.+) already exists\.\nDo you want to overwrite it\?$",
                    lambda m: f"数据库 {m.group(1)} 已存在。\n要覆盖它吗？",
                ),
                (
                    r"^Database for file '(.+)' is not closed\. Do you want IDA to repair it\?\n\nPlease note that the repaired database will be upgraded to\nthe current version of IDA and may still have problems\.\nThe best solution is to use the packed database or a backup\.$",
                    lambda m: (
                        f"文件 '{m.group(1)}' 对应的数据库未正常关闭。"
                        "你要让 IDA 修复它吗？\n\n"
                        "请注意，修复后的数据库会被升级到当前 IDA 版本，"
                        "并且仍可能存在问题。\n"
                        "最佳方案是使用打包数据库或备份。"
                    ),
                ),
            ]

            for pattern, repl in patterns:
                match = re.match(pattern, text, re.DOTALL)
                if match:
                    return repl(match)

            return None

        def log_missing_text(text, kind="", owner=""):
            """记录未翻译文本，方便后续补词条。"""
            text = str(text).strip()
            if not is_meaningful_text(text):
                return
            if text in translations or text in logged_missing:
                return

            record = {
                "ts": int(time.time()),
                "kind": kind,
                "owner": owner,
                "text": text,
            }
            try:
                with open(missing_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                logged_missing.add(text)
            except Exception:
                pass

        def translate_text(text, trans, kind="", owner=""):
            """翻译单段文本；未命中时记日志。"""
            if not text:
                return text
            for candidate in lookup_variants(text):
                if candidate in trans:
                    return trans[candidate]
            dynamic = translate_dynamic_text(text)
            if dynamic:
                return dynamic
            log_missing_text(text, kind, owner)
            return text
        
        # 直接遍历已有 Widget 替换文本
        def translate_widget(widget, trans):
            """递归遍历并翻译 widget 文本"""
            if not is_alive(widget):
                return 0

            count = 0
            owner = type(widget).__name__

            # 某些弹窗（如 QMenu）使用 title() 而不是 windowTitle()
            if isinstance(widget, QtWidgets.QMenu):
                try:
                    menu_title = widget.title()
                except RuntimeError:
                    return 0
                new_title = translate_text(menu_title, trans, "menu_title", owner)
                if menu_title and new_title != menu_title:
                    try:
                        widget.setTitle(new_title)
                    except RuntimeError:
                        return count
                    count += 1

            try:
                title = widget.windowTitle()
            except RuntimeError:
                return 0

            # 翻译窗口标题
            new_title = translate_text(title, trans, "window_title", owner)
            if title and new_title != title:
                try:
                    widget.setWindowTitle(new_title)
                except RuntimeError:
                    return count
                count += 1

            # QMessageBox 的正文不是 QLabel 直观可见时，直接处理其专用字段。
            if isinstance(widget, QtWidgets.QMessageBox):
                try:
                    text = widget.text()
                    new_text = translate_text(text, trans, "message_text", owner)
                    if text and new_text != text:
                        widget.setText(new_text)
                        count += 1
                except RuntimeError:
                    return count

                try:
                    info = widget.informativeText()
                    new_info = translate_text(info, trans, "message_info", owner)
                    if info and new_info != info:
                        widget.setInformativeText(new_info)
                        count += 1
                except RuntimeError:
                    return count

                try:
                    detail = widget.detailedText()
                    new_detail = translate_text(detail, trans, "message_detail", owner)
                    if detail and new_detail != detail:
                        widget.setDetailedText(new_detail)
                        count += 1
                except RuntimeError:
                    return count
            
            # 翻译菜单栏
            if isinstance(widget, QtWidgets.QMainWindow):
                try:
                    menubar = widget.menuBar()
                except RuntimeError:
                    menubar = None
                if is_alive(menubar):
                    for action in menubar.actions():
                        count += translate_action(action, trans)

            # 翻译当前 widget 挂载的 action（上下文菜单、弹窗菜单等）
            try:
                actions = widget.actions()
            except RuntimeError:
                actions = []
            for action in actions:
                count += translate_action(action, trans)
            
            # 翻译工具栏
            if isinstance(widget, QtWidgets.QMainWindow):
                for toolbar in widget.findChildren(QtWidgets.QToolBar):
                    if not is_alive(toolbar):
                        continue
                    t = toolbar.windowTitle()
                    new_t = translate_text(t, trans, "toolbar_title", type(toolbar).__name__)
                    if t and new_t != t:
                        try:
                            toolbar.setWindowTitle(new_t)
                        except RuntimeError:
                            continue
                        count += 1
                    for action in toolbar.actions():
                        count += translate_action(action, trans)
            
            # 翻译按钮
            for btn in widget.findChildren(QtWidgets.QAbstractButton):
                if not is_alive(btn):
                    continue
                txt = btn.text()
                new_txt = translate_text(txt, trans, "button_text", type(btn).__name__)
                if txt and new_txt != txt:
                    try:
                        btn.setText(new_txt)
                    except RuntimeError:
                        continue
                    count += 1
            
            # 翻译标签
            for label in widget.findChildren(QtWidgets.QLabel):
                if not is_alive(label):
                    continue
                txt = label.text()
                new_txt = translate_text(txt, trans, "label_text", type(label).__name__)
                if txt and new_txt != txt:
                    try:
                        label.setText(new_txt)
                    except RuntimeError:
                        continue
                    count += 1
            
            # 翻译 Tab 标签
            for tab in widget.findChildren(QtWidgets.QTabBar):
                if not is_alive(tab):
                    continue
                for i in range(tab.count()):
                    txt = tab.tabText(i)
                    new_txt = translate_text(txt, trans, "tab_text", type(tab).__name__)
                    if txt and new_txt != txt:
                        try:
                            tab.setTabText(i, new_txt)
                        except RuntimeError:
                            continue
                        count += 1
            
            return count
        
        def translate_action(action, trans):
            """翻译 QAction"""
            if not is_alive(action):
                return 0

            count = 0
            owner = type(action).__name__
            try:
                txt = action.text()
            except RuntimeError:
                return 0
            new_txt = translate_text(txt, trans, "action_text", owner)
            if txt and new_txt != txt:
                try:
                    action.setText(new_txt)
                except RuntimeError:
                    return count
                count += 1
            
            try:
                tip = action.toolTip()
            except RuntimeError:
                tip = ""
            new_tip = translate_text(tip, trans, "action_tooltip", owner)
            if tip and new_tip != tip:
                try:
                    action.setToolTip(new_tip)
                except RuntimeError:
                    pass
                count += 1
            
            try:
                stip = action.statusTip()
            except RuntimeError:
                stip = ""
            new_stip = translate_text(stip, trans, "action_status_tip", owner)
            if stip and new_stip != stip:
                try:
                    action.setStatusTip(new_stip)
                except RuntimeError:
                    pass
                count += 1
            
            # 递归翻译子菜单
            try:
                menu = action.menu()
            except RuntimeError:
                menu = None
            if is_alive(menu):
                try:
                    t = menu.title()
                except RuntimeError:
                    t = ""
                new_t = translate_text(t, trans, "submenu_title", type(menu).__name__)
                if t and new_t != t:
                    try:
                        menu.setTitle(new_t)
                    except RuntimeError:
                        return count
                    count += 1
                for sub_action in menu.actions():
                    count += translate_action(sub_action, trans)
            
            return count

        class TranslationEventFilter(QtCore.QObject):
            """在弹窗/菜单真正显示时再次做翻译。"""

            def eventFilter(self, watched, event):
                try:
                    if not is_alive(watched):
                        return False

                    event_type = event.type()
                    if event_type in (
                        QtCore.QEvent.Type.Show,
                        QtCore.QEvent.Type.Polish,
                        QtCore.QEvent.Type.WindowActivate,
                    ):
                        if isinstance(watched, QtWidgets.QWidget):
                            translate_widget(watched, translations)
                        elif isinstance(watched, QtGui.QAction):
                            translate_action(watched, translations)
                except RuntimeError:
                    return False
                except Exception:
                    return False
                return False

        def do_translate():
            """执行翻译（延迟调用）"""
            total = 0
            for w in list(app.topLevelWidgets()):
                total += translate_widget(w, translations)
            print(f"[IDA汉化] ✅ 已翻译 {total} 个界面元素")

        event_filter = TranslationEventFilter(app)
        app.installEventFilter(event_filter)
        app._cn_translation_event_filter = event_filter
        
        # 延迟执行，等待 IDA 界面完全加载
        QtCore.QTimer.singleShot(2000, do_translate)
        # 再延迟一次，捕获后加载的元素
        QtCore.QTimer.singleShot(5000, do_translate)
        
        print(f"[IDA汉化] ✅ 已加载 {len(translations)} 条翻译（等待界面加载...）")
        print(f"[IDA汉化] 未翻译文本将记录到: {missing_log_file}")
            
    except ImportError as e:
        print(f"[IDA汉化] PySide6 导入失败: {e}")
    except Exception as e:
        import traceback
        print(f"[IDA汉化] 加载失败: {e}")
        traceback.print_exc()

# 自动执行
load_chinese_translation()
print("[IDA汉化] idapythonrc.py 已执行")
