from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from klimozawr.config import get_paths
from klimozawr.logging_setup import setup_logging
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.migrations import apply_migrations
from klimozawr.ui.app_controller import AppController


def main() -> None:
    paths = get_paths()
    setup_logging(paths.logs_dir / "klimozawr.log")

    db = SQLiteDatabase(paths.db_path)
    apply_migrations(db)

    app = QApplication(sys.argv)
    app.setApplicationName("klimozawr")

    controller = AppController(db=db, paths=paths)
    controller.start()

    sys.exit(app.exec())
