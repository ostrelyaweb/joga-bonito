from PySide6.QtCore import QThread, Signal


class UpdateWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, client, mode, manifest=None, parent=None):
        super().__init__(parent)
        self.client, self.mode, self.manifest = client, mode, manifest

    def run(self):
        try:
            result = self.client.check() if self.mode == "check" else self.client.download(self.manifest)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
