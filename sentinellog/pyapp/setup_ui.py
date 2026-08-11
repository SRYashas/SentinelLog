"""
SentinelLog — First-Run Setup UI Popup (PyQt6)
================================================
Modern, dark-themed modal dialog that displays missing dependency warnings
and provides a single-click "Install & Configure Requirements" button.
Uses QThread (FirstRunBootstrapper) to keep the UI completely smooth and responsive.
"""

import os
import sys
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QMessageBox, QFrame
)
from PyQt6.QtGui import QFont, QIcon, QColor

from .bootstrapper import FirstRunBootstrapper, ERROR_LOG


class SetupDialog(QDialog):
    """
    Modern Setup Modal Dialog presented on first run.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bootstrapper = None
        self.setup_successful = False

        self.setWindowTitle("SentinelLog — Initial Setup & Configuration")
        self.setFixedSize(650, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._apply_dark_theme()
        self._init_ui()

    def _apply_dark_theme(self):
        """Apply modern dark stylesheet with cyan accents."""
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #f1f5f9;
            }
            QFrame#headerFrame {
                background-color: #111827;
                border-bottom: 1px solid #1f2937;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QPushButton#btnInstall {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #2563eb);
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#btnInstall:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #3b82f6);
            }
            QPushButton#btnInstall:disabled {
                background: #1e293b;
                color: #64748b;
            }
            QPushButton#btnSecondary {
                background-color: #1e293b;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 12px;
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton#btnSecondary:hover {
                background-color: #334155;
                color: #f8fafc;
            }
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 6px;
                background-color: #0f172a;
                text-align: center;
                color: #f8fafc;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #06b6d4;
                border-radius: 5px;
            }
            QTextEdit#logView {
                background-color: #030712;
                color: #38bdf8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px;
            }
        """)

    def _init_ui(self):
        """Construct layout components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header Bar ───────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("🛡️ SentinelLog — First-Run Configuration")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))

        subtitle_label = QLabel(
            "SentinelLog needs to configure its local database and execution environment.\n"
            "Click below to initialize all requirements in a single click."
        )
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet("color: #94a3b8; margin-top: 4px;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_frame)

        # ── Body Content ─────────────────────────────────────────────
        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(14)

        # Single Prominent Install Button
        self.btn_install = QPushButton("⚡ Install & Configure Requirements")
        self.btn_install.setObjectName("btnInstall")
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.clicked.connect(self._start_setup)
        body_layout.addWidget(self.btn_install)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        body_layout.addWidget(self.progress_bar)

        # Live Real-time Terminal Output Log
        log_header = QLabel("Execution Log:")
        log_header.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        body_layout.addWidget(log_header)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.append("Ready to configure. Click 'Install & Configure Requirements' to start.\n")
        body_layout.addWidget(self.log_view)

        # ── Footer Button Area ───────────────────────────────────────
        footer_layout = QHBoxLayout()

        self.btn_view_log = QPushButton("View Full Error Log")
        self.btn_view_log.setObjectName("btnSecondary")
        self.btn_view_log.setVisible(False)
        self.btn_view_log.clicked.connect(self._open_error_log)

        self.btn_retry = QPushButton("Retry Setup")
        self.btn_retry.setObjectName("btnSecondary")
        self.btn_retry.setVisible(False)
        self.btn_retry.clicked.connect(self._start_setup)

        footer_layout.addWidget(self.btn_view_log)
        footer_layout.addWidget(self.btn_retry)
        footer_layout.addStretch()

        body_layout.addLayout(footer_layout)
        main_layout.addLayout(body_layout)

    def _start_setup(self):
        """Disable button, show progress bar, and launch bootstrapper thread."""
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Configuring System...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_view_log.setVisible(False)
        self.btn_retry.setVisible(False)

        self.log_view.clear()

        # Instantiate background worker thread
        self.bootstrapper = FirstRunBootstrapper()
        self.bootstrapper.progress_update.connect(self._on_progress)
        self.bootstrapper.log_message.connect(self._on_log)
        self.bootstrapper.setup_complete.connect(self._on_complete)
        self.bootstrapper.setup_failed.connect(self._on_failed)
        self.bootstrapper.start()

    @pyqtSlot(int)
    def _on_progress(self, val):
        self.progress_bar.setValue(val)

    @pyqtSlot(str)
    def _on_log(self, msg):
        self.log_view.append(msg)
        # Auto-scroll to bottom
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    @pyqtSlot()
    def _on_complete(self):
        self.setup_successful = True
        self.btn_install.setText("✓ Setup Complete")
        self.btn_install.setStyleSheet("""
            QPushButton#btnInstall {
                background: #10b981;
                color: #ffffff;
            }
        """)

        QMessageBox.information(
            self,
            "Setup Complete",
            "SentinelLog configuration finished successfully!\n\nLaunching Dashboard...",
            QMessageBox.StandardButton.Ok
        )
        self.accept()

    @pyqtSlot(str)
    def _on_failed(self, error_msg):
        self.setup_successful = False
        self.btn_install.setText("❌ Setup Failed")
        self.btn_install.setEnabled(False)

        self.btn_view_log.setVisible(True)
        self.btn_retry.setVisible(True)

        QMessageBox.critical(
            self,
            "Setup Error",
            f"An error occurred during initial configuration:\n\n{error_msg}\n\n"
            "Please view the error log or click Retry.",
            QMessageBox.StandardButton.Ok
        )

    def _open_error_log(self):
        """Open setup_error.log file if available."""
        if ERROR_LOG.exists():
            os.system(f'notepad "{ERROR_LOG}"')
        else:
            QMessageBox.information(self, "Log File", "No log file found.")


def run_first_run_setup():
    """
    Utility function to display setup UI dialog.
    Returns True if setup completed successfully, False otherwise.
    """
    dialog = SetupDialog()
    result = dialog.exec()
    return dialog.setup_successful and result == QDialog.DialogCode.Accepted
