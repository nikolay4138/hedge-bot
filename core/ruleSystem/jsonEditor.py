import json, sys, os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QAction,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QPlainTextEdit,
    QInputDialog,
    QMenu,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QUndoStack,
    QUndoCommand,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QFont


###########################JSON EDİTOR CLASS STARTS###########################
# ---------- Undo/Redo Command Sınıfları ----------
class AddNodeCommand(QUndoCommand):
    def __init__(self, parent, key, value, editor):
        super().__init__("Node Ekle")
        self.parent = parent
        self.key = key
        self.value = value
        self.editor = editor
        self.node = None

    def redo(self):
        self.node = QTreeWidgetItem(
            [
                self.key,
                self.editor._preview(self.value),
                self.editor._type_of(self.value),
            ]
        )
        self.parent.addChild(self.node)
        if isinstance(self.value, (dict, list)):
            self.editor._build_tree(self.node, self.value)
        self.parent.setExpanded(True)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)

    def undo(self):
        if self.node:
            self.parent.removeChild(self.node)
            self.editor.sync_tree_to_text()
            self.editor.set_modified(True)


class DeleteNodeCommand(QUndoCommand):
    def __init__(self, parent, node, editor):
        super().__init__("Node Sil")
        self.parent = parent
        self.node = node
        self.editor = editor
        self.index = self.parent.indexOfChild(node)

    def redo(self):
        self.parent.takeChild(self.index)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)

    def undo(self):
        self.parent.insertChild(self.index, self.node)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)


class RenameNodeCommand(QUndoCommand):
    def __init__(self, node, old, new, editor):
        super().__init__("Node Yeniden Adlandır")
        self.node = node
        self.old = old
        self.new = new
        self.editor = editor

    def redo(self):
        self.node.setText(0, self.new)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)

    def undo(self):
        self.node.setText(0, self.old)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)


class EditValueCommand(QUndoCommand):
    def __init__(self, node, old, new, editor):
        super().__init__("Değer Düzenle")
        self.node = node
        self.old = old
        self.new = new
        self.editor = editor

    def redo(self):
        self.node.setText(1, self.new)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)

    def undo(self):
        self.node.setText(1, self.old)
        self.editor.sync_tree_to_text()
        self.editor.set_modified(True)


# ---------- JSON Editor ----------
class JsonEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON Editor (PyQt5)")
        self.resize(1100, 700)

        self._filepath = None
        self._modified = False
        self._font_size = 11
        self.undo_stack = QUndoStack(self)

        self._build_ui()
        self._setup_shortcuts()
        self.load_json({})

    def _build_ui(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("Dosya")
        editMenu = menubar.addMenu("Düzen")
        syncMenu = menubar.addMenu("Senkron")

        self.actNew = QAction("Yeni", self)
        self.actNew.triggered.connect(self.new_file)
        self.actOpen = QAction("Aç…", self)
        self.actOpen.triggered.connect(self.open_file)
        self.actSave = QAction("Kaydet", self)
        self.actSave.triggered.connect(self.save_file)
        self.actSaveAs = QAction("Farklı Kaydet…", self)
        self.actSaveAs.triggered.connect(self.save_file_as)

        self.actValidate = QAction("Doğrula", self)
        self.actValidate.triggered.connect(self.validate_json)
        self.actPretty = QAction("Pretty Print", self)
        self.actPretty.triggered.connect(self.pretty_print)
        self.actMinify = QAction("Minify", self)
        self.actMinify.triggered.connect(self.minify)

        self.actSyncTextToTree = QAction("Metinden → Ağaç", self)
        self.actSyncTextToTree.triggered.connect(self.sync_text_to_tree)
        self.actSyncTreeToText = QAction("Ağaçtan → Metin", self)
        self.actSyncTreeToText.triggered.connect(self.sync_tree_to_text)

        fileMenu.addActions([self.actNew, self.actOpen, self.actSave, self.actSaveAs])
        editMenu.addActions([self.actValidate, self.actPretty, self.actMinify])
        syncMenu.addActions([self.actSyncTextToTree, self.actSyncTreeToText])

        splitter = QSplitter(self)
        self.setCentralWidget(splitter)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key/Index", "Value", "Type"])
        self.tree.itemDoubleClicked.connect(self.on_tree_double_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)

        self.text = QPlainTextEdit()
        self.text.setUndoRedoEnabled(True)
        self.text.setReadOnly(True)
        self.text.textChanged.connect(lambda: self.set_modified(True))
        self.text.setFont(QFont("Consolas", self._font_size))

        splitter.addWidget(self.tree)
        splitter.addWidget(self.text)
        splitter.setSizes([400, 700])

        self.statusBar().showMessage("Hazır")

    def _setup_shortcuts(self):
        self.actSave.setShortcut(QKeySequence.Save)
        self.actOpen.setShortcut(QKeySequence.Open)
        self.actNew.setShortcut(QKeySequence.New)

        self.addAction(
            QAction(
                "Kopyala", self, shortcut=QKeySequence.Copy, triggered=self.text.copy
            )
        )
        self.addAction(
            QAction(
                "Yapıştır", self, shortcut=QKeySequence.Paste, triggered=self.text.paste
            )
        )
        self.addAction(
            QAction("Kes", self, shortcut=QKeySequence.Cut, triggered=self.text.cut)
        )

        self.addAction(
            QAction("Bul", self, shortcut=QKeySequence.Find, triggered=self.find_dialog)
        )

        self.addAction(
            QAction(
                "Zoom In", self, shortcut=QKeySequence("Ctrl++"), triggered=self.zoom_in
            )
        )
        self.addAction(
            QAction(
                "Zoom Out",
                self,
                shortcut=QKeySequence("Ctrl+-"),
                triggered=self.zoom_out,
            )
        )
        self.addAction(
            QAction(
                "Zoom Reset",
                self,
                shortcut=QKeySequence("Ctrl+0"),
                triggered=self.zoom_reset,
            )
        )

        self.addAction(
            QAction(
                "Undo", self, shortcut=QKeySequence.Undo, triggered=self.undo_stack.undo
            )
        )
        self.addAction(
            QAction(
                "Redo", self, shortcut=QKeySequence.Redo, triggered=self.undo_stack.redo
            )
        )

    # ---------- Zoom ----------
    def zoom_in(self):
        self._font_size += 1
        self.text.setFont(QFont("Consolas", self._font_size))

    def zoom_out(self):
        if self._font_size > 6:
            self._font_size -= 1
            self.text.setFont(QFont("Consolas", self._font_size))

    def zoom_reset(self):
        self._font_size = 11
        self.text.setFont(QFont("Consolas", self._font_size))

    # ---------- Bul ----------
    def find_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Bul")
        layout = QVBoxLayout(dlg)
        line = QLineEdit(dlg)
        layout.addWidget(line)

        def do_find():
            text = line.text()
            if not text:
                return
            cursor = self.text.textCursor()
            found = self.text.find(text)
            if not found:
                self.text.moveCursor(cursor.Start)
                self.text.find(text)

        line.returnPressed.connect(do_find)
        dlg.exec_()

    # ---------- Dosya ----------
    def new_file(self):
        self._filepath = None
        self.load_json({})
        self.set_modified(False)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "JSON aç", "", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._filepath = path
            self.load_json(data)
            self.set_modified(False)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def save_file(self):
        if not self._filepath:
            return self.save_file_as()
        try:
            self.sync_tree_to_text()
            data = self.get_text_json(strict=True)
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.set_modified(False)
            self.statusBar().showMessage("Kaydedildi")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Kaydet", "", "JSON Files (*.json)")
        if not path:
            return
        # Uzantı kontrolü
        if not path.lower().endswith(".json"):
            path += ".json"

        self._filepath = path
        self.save_file()

    # ---------- JSON ----------
    def load_json(self, data):
        self.text.blockSignals(True)
        self.text.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        self.text.blockSignals(False)
        self.tree.clear()
        root = QTreeWidgetItem(["root", self._preview(data), self._type_of(data)])
        self.tree.addTopLevelItem(root)
        self._build_tree(root, data)
        root.setExpanded(True)

    def get_text_json(self, strict=False):
        try:
            return json.loads(self.text.toPlainText())
        except Exception as e:
            if strict:
                raise
            return {}

    def validate_json(self):
        try:
            json.loads(self.text.toPlainText())
            QMessageBox.information(self, "JSON", "Geçerli ✅")
        except Exception as e:
            QMessageBox.critical(self, "Geçersiz JSON", str(e))

    def pretty_print(self):
        try:
            data = self.get_text_json(strict=True)
            self.text.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def minify(self):
        try:
            data = self.get_text_json(strict=True)
            self.text.setPlainText(
                json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ---------- Senkron ----------
    def sync_text_to_tree(self):
        try:
            data = self.get_text_json(strict=True)
            self.load_json(data)
            self.statusBar().showMessage("Metinden → Ağaç güncellendi")
        except Exception as e:
            QMessageBox.critical(self, "Geçersiz JSON", str(e))

    def sync_tree_to_text(self):
        try:
            root = self.tree.topLevelItem(0)
            data = self._data_from_tree(root)
            self.text.blockSignals(True)
            self.text.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
            self.text.blockSignals(False)
            self.statusBar().showMessage("Ağaçtan → Metin güncellendi")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ---------- Tree Helpers ----------
    def _build_tree(self, parent, data):
        if isinstance(data, dict):
            for k, v in data.items():
                node = QTreeWidgetItem([k, self._preview(v), self._type_of(v)])
                parent.addChild(node)
                self._build_tree(node, v)
        elif isinstance(data, list):
            for i, v in enumerate(data):
                node = QTreeWidgetItem([f"[{i}]", self._preview(v), self._type_of(v)])
                parent.addChild(node)
                self._build_tree(node, v)

    def _data_from_tree(self, item):
        t = item.text(2)
        if t == "object":
            obj = {}
            for i in range(item.childCount()):
                c = item.child(i)
                obj[c.text(0)] = self._data_from_tree(c)
            return obj
        elif t == "array":
            arr = []
            for i in range(item.childCount()):
                arr.append(self._data_from_tree(item.child(i)))
            return arr
        else:
            return self._parse_scalar(item.text(1))

    def _type_of(self, v):
        if isinstance(v, dict):
            return "object"
        if isinstance(v, list):
            return "array"
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "boolean"
        if isinstance(v, (int, float)):
            return "number"
        return "string"

    def _preview(self, v):
        if isinstance(v, dict):
            return "{...}"
        if isinstance(v, list):
            return "[...]"
        return json.dumps(v, ensure_ascii=False)

    def _parse_scalar(self, s):
        try:
            return json.loads(s)
        except:
            return s

    # ---------- Tree Etkileşim ----------
    def on_tree_double_click(self, item, col):
        if item.text(2) in ("object", "array"):
            return
        old = item.text(1)
        new, ok = QInputDialog.getText(self, "Değer Düzenle", "Yeni değer:", text=old)
        if ok:
            cmd = EditValueCommand(item, old, new, self)
            self.undo_stack.push(cmd)

    def on_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        menu.addAction("Ekle", lambda: self.ctx_add(item))
        menu.addAction("Sil", lambda: self.ctx_delete(item))
        menu.addAction("Yeniden Adlandır", lambda: self.ctx_rename(item))
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def ctx_add(self, item):
        parent_type = item.text(2)
        if parent_type not in ("object", "array"):
            QMessageBox.information(
                self, "Bilgi", "Yalnızca object/array içine eklenebilir."
            )
            return

        types = ["object", "array", "string", "number", "boolean", "null"]
        t, ok = QInputDialog.getItem(self, "Tip Seç", "Yeni öğe tipi:", types, 0, False)
        if not ok:
            return

        if parent_type == "object":
            key, ok = QInputDialog.getText(self, "Anahtar", "Anahtar adı:")
            if not ok or not key:
                return
        else:
            key = f"[{item.childCount()}]"

        if t == "object":
            val = {}
        elif t == "array":
            val = []
        elif t == "string":
            val, ok = QInputDialog.getText(self, "Değer", "String değer:", text="")
            if not ok:
                return
        elif t == "number":
            val, ok = QInputDialog.getDouble(self, "Değer", "Sayı:", 0)
            if not ok:
                return
        elif t == "boolean":
            val, ok = QInputDialog.getItem(
                self, "Değer", "Boolean:", ["true", "false"], 0, False
            )
            if not ok:
                return
            val = True if val == "true" else False
        elif t == "null":
            val = None
        else:
            val = None

        cmd = AddNodeCommand(item, key, val, self)
        self.undo_stack.push(cmd)

    def ctx_delete(self, item):
        parent = item.parent()
        if not parent:
            return
        cmd = DeleteNodeCommand(parent, item, self)
        self.undo_stack.push(cmd)

    def ctx_rename(self, item):
        parent = item.parent()
        if not parent:
            return
        if parent.text(2) != "object":
            QMessageBox.information(
                self, "Bilgi", "Yeniden adlandırma sadece object içindeki key'ler için."
            )
            return
        old = item.text(0)
        new, ok = QInputDialog.getText(
            self, "Yeniden Adlandır", "Yeni anahtar:", text=old
        )
        if ok and new:
            cmd = RenameNodeCommand(item, old, new, self)
            self.undo_stack.push(cmd)

    # ---------- Yardımcı ----------
    def set_modified(self, val=True):
        self._modified = val
        title = os.path.basename(self._filepath) if self._filepath else "isimsiz.json"
        self.setWindowTitle(f"JSON Editor (PyQt5) - {title}{'*' if val else ''}")


class jsonEditorGetter:
    def __init__(self) -> None:
        pass

    def main(self):
        app = QApplication(sys.argv)
        win = JsonEditor()
        win.show()
        sys.exit(app.exec_())
jj=jsonEditorGetter()
if __name__=="__main__":
    jj.main()