"""MarkItDown GUI - a Fluent Design front end for microsoft/markitdown."""
import sys

if len(sys.argv) > 1 and sys.argv[1] in ("--convert", "--convert-batch"):
    import engine  # child-process mode: no Qt imported at all
    engine.cli(sys.argv[1:])
    sys.exit(0)

from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QGuiApplication
from PyQt5.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                             QStackedWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)
from qfluentwidgets import (BodyLabel, ComboBox, FluentIcon as FIF,
                            FluentWindow, InfoBar, InfoBarPosition,
                            LineEdit, NavigationItemPosition, Pivot,
                            PasswordLineEdit, PlainTextEdit, PrimaryPushButton,
                            ProgressBar, PushButton, SettingCard,
                            SubtitleLabel, SwitchButton, TableWidget,
                            TextEdit, Theme, setTheme, setThemeColor,
                            ToolButton, StrongBodyLabel, CaptionLabel,
                            CardWidget)

from core import BatchWorker, SingleWorker, output_path, settings

SUPPORTED = ("PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, images, "
             "audio, ZIP, EPUB, or a URL / YouTube link")


def notify(parent, kind: str, title: str, msg: str = ""):
    getattr(InfoBar, kind)(title=title, content=msg, orient=Qt.Horizontal,
                           isClosable=True, position=InfoBarPosition.TOP_RIGHT,
                           duration=4000, parent=parent)


def page_root(widget: QWidget, name: str, title: str):
    widget.setObjectName(name)
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(36, 24, 36, 24)
    lay.setSpacing(14)
    lay.addWidget(SubtitleLabel(title))
    return lay


class ConvertPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = page_root(self, "convertPage", "Convert")
        self.setAcceptDrops(True)
        self.worker = None

        row = QHBoxLayout()
        self.source = LineEdit()
        self.source.setPlaceholderText("Drop a file here, browse, or paste a URL")
        self.source.setClearButtonEnabled(True)
        self.source.returnPressed.connect(self.start)
        browse = PushButton(FIF.FOLDER, "Browse")
        browse.clicked.connect(self.browse)
        self.go = PrimaryPushButton(FIF.SYNC, "Convert")
        self.go.clicked.connect(self.start)
        row.addWidget(self.source, 1)
        row.addWidget(browse)
        row.addWidget(self.go)
        lay.addLayout(row)
        lay.addWidget(CaptionLabel("Supports " + SUPPORTED))

        self.busy = ProgressBar()
        self.busy.setVisible(False)
        lay.addWidget(self.busy)

        top = QHBoxLayout()
        self.pivot = Pivot()
        self.stack = QStackedWidget()
        self.rendered = TextEdit()
        self.rendered.setReadOnly(True)
        self.raw = PlainTextEdit()
        for key, text, w in (("rendered", "Preview", self.rendered),
                             ("raw", "Markdown", self.raw)):
            self.stack.addWidget(w)
            self.pivot.addItem(key, text, lambda _=None, w=w: self.stack.setCurrentWidget(w))
        self.pivot.setCurrentItem("rendered")
        top.addWidget(self.pivot)
        top.addStretch(1)
        self.copy_btn = ToolButton(FIF.COPY)
        self.copy_btn.setToolTip("Copy Markdown")
        self.copy_btn.clicked.connect(self.copy)
        self.save_btn = ToolButton(FIF.SAVE)
        self.save_btn.setToolTip("Save as .md")
        self.save_btn.clicked.connect(self.save)
        top.addWidget(self.copy_btn)
        top.addWidget(self.save_btn)
        lay.addLayout(top)
        lay.addWidget(self.stack, 1)
        self.raw.textChanged.connect(self._sync_preview)

    # --- input ---
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.source.setText(urls[0].toLocalFile() or urls[0].toString())
            self.start()

    def browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose a file")
        if f:
            self.source.setText(f)
            self.start()

    # --- conversion ---
    def start(self):
        src = self.source.text().strip()
        if not src:
            return notify(self.window(), "warning", "Nothing to convert",
                          "Enter a file path or URL.")
        if self.worker and self.worker.isRunning():
            return
        self.go.setEnabled(False)
        self.busy.setVisible(True)
        self.busy.setRange(0, 0)  # indeterminate
        self.worker = SingleWorker(src, self)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_fail)
        self.worker.start()

    def _finish(self):
        self.go.setEnabled(True)
        self.busy.setVisible(False)

    def on_done(self, text):
        self._finish()
        self.raw.setPlainText(text)
        notify(self.window(), "success", "Converted", f"{len(text):,} characters")

    def on_fail(self, msg):
        self._finish()
        notify(self.window(), "error", "Conversion failed", msg)

    PREVIEW_LIMIT = 200_000

    def _sync_preview(self):
        text = self.raw.toPlainText()
        if len(text) > self.PREVIEW_LIMIT:  # huge documents can freeze/crash the rich-text renderer
            self.rendered.setPlainText(text[:self.PREVIEW_LIMIT] +
                                       "\n\n... preview truncated; use the Markdown tab or Save for the full text.")
        else:
            self.rendered.setMarkdown(text)

    def copy(self):
        QGuiApplication.clipboard().setText(self.raw.toPlainText())
        notify(self.window(), "success", "Copied to clipboard")

    def save(self):
        text = self.raw.toPlainText()
        if not text:
            return
        src = self.source.text().strip()
        stem = Path(src).stem if Path(src).suffix else "output"
        default = str(Path(settings().value("out_dir", "", str) or Path.home()) / f"{stem}.md")
        f, _ = QFileDialog.getSaveFileName(self, "Save Markdown", default, "Markdown (*.md)")
        if f:
            Path(f).write_text(text, encoding="utf-8")
            notify(self.window(), "success", "Saved", f)


class BatchPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = page_root(self, "batchPage", "Batch")
        self.setAcceptDrops(True)
        self.worker = None
        self.files: list[str] = []

        row = QHBoxLayout()
        for icon, text, fn in ((FIF.ADD, "Add files", self.add_files),
                               (FIF.FOLDER_ADD, "Add folder", self.add_folder),
                               (FIF.DELETE, "Clear", self.clear)):
            b = PushButton(icon, text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        self.run_btn = PrimaryPushButton(FIF.PLAY, "Convert all")
        self.run_btn.clicked.connect(self.run)
        self.cancel_btn = PushButton(FIF.CANCEL, "Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        row.addWidget(self.cancel_btn)
        row.addWidget(self.run_btn)
        lay.addLayout(row)

        self.table = TableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Output / error"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 360)
        self.table.setColumnWidth(1, 90)
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setEditTriggers(TableWidget.NoEditTriggers)
        lay.addWidget(self.table, 1)

        self.bar = ProgressBar()
        self.summary = CaptionLabel("Drop files or folders here. Output goes to the folder set in Settings, or next to each source file.")
        lay.addWidget(self.bar)
        lay.addWidget(self.summary)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = Path(u.toLocalFile())
            self.add_paths([p] if p.is_file() else [x for x in p.rglob("*") if x.is_file()])

    def add_files(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Add files")
        self.add_paths([Path(f) for f in fs])

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Add folder")
        if d:
            self.add_paths([p for p in Path(d).rglob("*") if p.is_file()])

    def add_paths(self, paths):
        for p in paths:
            s = str(p)
            if s in self.files:
                continue
            self.files.append(s)
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, t in enumerate((s, "Queued", "")):
                self.table.setItem(r, c, QTableWidgetItem(t))

    def clear(self):
        if self.worker and self.worker.isRunning():
            return
        self.files.clear()
        self.table.setRowCount(0)
        self.bar.setValue(0)

    def run(self):
        if not self.files or (self.worker and self.worker.isRunning()):
            return
        for r in range(self.table.rowCount()):
            self.table.item(r, 1).setText("Queued")
            self.table.item(r, 2).setText("")
        self.done_n = 0
        self.bar.setRange(0, len(self.files))
        self.bar.setValue(0)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker = BatchWorker(list(self.files), settings().value("out_dir", "", str), self)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, row, ok, msg):
        self.table.item(row, 1).setText("Done" if ok else "Failed")
        self.table.item(row, 2).setText(msg)
        self.done_n += 1
        self.bar.setValue(self.done_n)

    def on_finished(self, ok, fail):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.summary.setText(f"{ok} converted, {fail} failed.")
        notify(self.window(), "success" if not fail else "warning",
               "Batch complete", f"{ok} converted, {fail} failed")


class SettingsPage(QFrame):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        lay = page_root(self, "settingsPage", "Settings")
        self.s = settings()

        # Theme
        theme_card = SettingCard(FIF.BRUSH, "Theme", "Light, dark, or follow Windows")
        self.theme = ComboBox()
        self.theme.addItems(["System", "Light", "Dark"])
        self.theme.setCurrentIndex(self.s.value("theme", 0, int))
        self.theme.currentIndexChanged.connect(self.on_theme)
        theme_card.hBoxLayout.addWidget(self.theme, 0, Qt.AlignRight)
        theme_card.hBoxLayout.addSpacing(16)
        lay.addWidget(theme_card)

        # Output dir
        out_card = SettingCard(FIF.FOLDER, "Batch output folder",
                               "Empty = save next to each source file")
        self.out = LineEdit()
        self.out.setMinimumWidth(260)
        self.out.setText(self.s.value("out_dir", "", str))
        self.out.editingFinished.connect(lambda: self.s.setValue("out_dir", self.out.text().strip()))
        pick = PushButton("Browse")
        pick.clicked.connect(self.pick_out)
        for w in (self.out, pick):
            out_card.hBoxLayout.addWidget(w, 0, Qt.AlignRight)
        out_card.hBoxLayout.addSpacing(16)
        lay.addWidget(out_card)

        # Plugins
        plug_card = SettingCard(FIF.APPLICATION, "Enable plugins",
                                "Load third-party markitdown plugins")
        self.plug = SwitchButton()
        self.plug.setChecked(self.s.value("plugins", False, bool))
        self.plug.checkedChanged.connect(lambda v: self.s.setValue("plugins", v))
        plug_card.hBoxLayout.addWidget(self.plug, 0, Qt.AlignRight)
        plug_card.hBoxLayout.addSpacing(16)
        lay.addWidget(plug_card)

        # Azure + OpenAI
        lay.addWidget(StrongBodyLabel("Optional services"))
        lay.addWidget(self._field("Azure Document Intelligence endpoint", "docintel", False,
                                  "https://<resource>.cognitiveservices.azure.com/"))
        lay.addWidget(self._field("OpenAI API key (image descriptions)", "openai_key", True, "sk-..."))
        lay.addWidget(self._field("OpenAI model", "llm_model", False, "gpt-4o"))
        lay.addStretch(1)
        lay.addWidget(CaptionLabel("Keys are stored in the Windows registry for the current user."))

    def _field(self, label, key, secret, placeholder):
        card = CardWidget()
        h = QHBoxLayout(card)
        h.setContentsMargins(16, 10, 16, 10)
        h.addWidget(BodyLabel(label), 1)
        edit = PasswordLineEdit() if secret else LineEdit()
        edit.setMinimumWidth(340)
        edit.setPlaceholderText(placeholder)
        edit.setText(self.s.value(key, "", str))
        edit.editingFinished.connect(lambda e=edit, k=key: self.s.setValue(k, e.text().strip()))
        h.addWidget(edit)
        return card

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d:
            self.out.setText(d)
            self.s.setValue("out_dir", d)

    def on_theme(self, i):
        self.s.setValue("theme", i)
        apply_theme(i)


def apply_theme(i: int):
    setTheme((Theme.AUTO, Theme.LIGHT, Theme.DARK)[i])


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.resize(1100, 740)
        self.setWindowTitle("MarkItDown")
        self.setWindowIcon(FIF.DOCUMENT.icon())
        self.convert = ConvertPage(self)
        self.batch = BatchPage(self)
        self.settings_page = SettingsPage(self, self)
        self.addSubInterface(self.convert, FIF.SYNC, "Convert")
        self.addSubInterface(self.batch, FIF.FOLDER, "Batch")
        self.addSubInterface(self.settings_page, FIF.SETTING, "Settings",
                             NavigationItemPosition.BOTTOM)


def install_crash_logging():
    import faulthandler, traceback
    log = Path.home() / "MarkItDownGUI-crash.log"
    try:
        faulthandler.enable(open(log, "a", buffering=1))  # native crashes (segfaults)
    except Exception:
        pass

    def hook(et, ev, tb):
        text = "".join(traceback.format_exception(et, ev, tb))
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass
        sys.__excepthook__(et, ev, tb)
    sys.excepthook = hook


def main():
    install_crash_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    setThemeColor("#0078D4")  # Windows accent blue
    apply_theme(settings().value("theme", 0, int))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
