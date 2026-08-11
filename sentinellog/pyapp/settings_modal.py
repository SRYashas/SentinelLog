"""
SentinelLog — API Settings Modal
=================================
Modern modal dialog for Groq API key configuration.
Includes secure password-masked input, connection test, and secure storage.
"""

import asyncio
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QMessageBox, QProgressBar
)
from PyQt6.QtGui import QFont, QIcon

from .api_key_manager import get_key_manager
from .groq_client import GroqClient
from .connectivity_monitor import is_online


class TestConnectionWorker(QThread):
    """Background worker for testing API key connectivity."""

    test_complete = pyqtSignal(bool, str)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        try:
            # First check internet connectivity
            if not is_online(timeout=5):
                self.test_complete.emit(False, "No internet connection detected")
                return

            # Test Groq API key
            client = GroqClient(self.api_key)
            success, message = asyncio.run(client.validate_api_key())
            self.test_complete.emit(success, message)
        except Exception as e:
            self.test_complete.emit(False, f"Test failed: {str(e)}")


class APISettingsDialog(QDialog):
    """
    Settings modal for Groq API configuration.
    Features:
    - Password-masked API key input
    - Test Connection button with validation
    - Secure storage via keyring/encrypted file
    - Shows current key status (masked)
    """

    key_saved = pyqtSignal(str)  # Emitted when key is successfully saved

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_manager = get_key_manager()
        self.test_worker: TestConnectionWorker = None

        self.setWindowTitle("SentinelLog — API Configuration")
        self.setFixedSize(520, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._apply_dark_theme()
        self._init_ui()
        self._load_current_key()

    def _apply_dark_theme(self):
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
            QFrame#cardFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QLineEdit#apiKeyInput {
                background-color: #030712;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit#apiKeyInput:focus {
                border-color: #06b6d4;
            }
            QPushButton#btnPrimary {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #2563eb);
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton#btnPrimary:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #3b82f6);
            }
            QPushButton#btnPrimary:disabled {
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
            QPushButton#btnDanger {
                background-color: #450a0a;
                color: #fca5a5;
                font-weight: 600;
                font-size: 12px;
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #7f1d1d;
            }
            QPushButton#btnDanger:hover {
                background-color: #7f1d1d;
                color: #fecaca;
            }
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 4px;
                background-color: #030712;
                text-align: center;
                color: #f8fafc;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #2563eb);
                border-radius: 3px;
            }
            QLabel#hintLabel {
                color: #64748b;
                font-size: 11px;
            }
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: 600;
            }
        """)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(70)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("⚙️ Groq API Configuration")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")

        subtitle = QLabel("Enter your Groq API key to enable AI-powered threat analysis")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 2px;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header)

        # ── Body ───────────────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(16)

        # Current key status
        self.status_frame = QFrame()
        self.status_frame.setObjectName("cardFrame")
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_key_status = QLabel("No API key configured")
        self.lbl_key_status.setObjectName("statusLabel")
        self.lbl_key_status.setStyleSheet("color: #f59e0b;")
        status_layout.addWidget(self.lbl_key_status)

        self.lbl_key_preview = QLabel("")
        self.lbl_key_preview.setObjectName("hintLabel")
        self.lbl_key_preview.setStyleSheet("color: #64748b; font-family: Consolas; margin-top: 4px;")
        status_layout.addWidget(self.lbl_key_preview)

        body.addWidget(self.status_frame)

        # API Key Input
        input_label = QLabel("Groq API Key (gsk_...)")
        input_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        body.addWidget(input_label)

        self.input_api_key = QLineEdit()
        self.input_api_key.setObjectName("apiKeyInput")
        self.input_api_key.setPlaceholderText("gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.textChanged.connect(self._on_key_changed)
        body.addWidget(self.input_api_key)

        # Show/Hide toggle
        toggle_layout = QHBoxLayout()
        self.btn_toggle_visibility = QPushButton("👁 Show")
        self.btn_toggle_visibility.setObjectName("btnSecondary")
        self.btn_toggle_visibility.setMaximumWidth(100)
        self.btn_toggle_visibility.clicked.connect(self._toggle_visibility)
        toggle_layout.addWidget(self.btn_toggle_visibility)

        hint = QLabel("Get your key at: https://console.groq.com/keys")
        hint.setObjectName("hintLabel")
        hint.setOpenExternalLinks(True)
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setText('Get your key at: <a href="https://console.groq.com/keys" style="color: #38bdf8;">console.groq.com/keys</a>')
        toggle_layout.addWidget(hint)
        toggle_layout.addStretch()
        body.addLayout(toggle_layout)

        # Test Connection Button
        self.btn_test = QPushButton("🔗 Test Connection")
        self.btn_test.setObjectName("btnSecondary")
        self.btn_test.setEnabled(False)
        self.btn_test.clicked.connect(self._test_connection)
        body.addWidget(self.btn_test)

        # Test progress bar
        self.test_progress = QProgressBar()
        self.test_progress.setRange(0, 0)  # Indeterminate
        self.test_progress.setVisible(False)
        body.addWidget(self.test_progress)

        # Test result label
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setObjectName("hintLabel")
        self.lbl_test_result.setWordWrap(True)
        body.addWidget(self.lbl_test_result)

        body.addStretch()
        main_layout.addLayout(body)

        # ── Footer Buttons ─────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setContentsMargins(20, 0, 20, 20)
        footer.setSpacing(10)

        self.btn_delete = QPushButton("🗑 Delete Key")
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.clicked.connect(self._delete_key)
        footer.addWidget(self.btn_delete)

        footer.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save & Enable AI")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_key)
        footer.addWidget(self.btn_save)

        main_layout.addLayout(footer)

    def _load_current_key(self):
        """Load and display current key status."""
        if self.key_manager.has_key():
            key = self.key_manager.get_key()
            if key:
                masked = key[:8] + "*" * (len(key) - 12) + key[-4:] if len(key) > 12 else "****"
                self.lbl_key_status.setText("✅ API Key Configured")
                self.lbl_key_status.setStyleSheet("color: #10b981;")
                self.lbl_key_preview.setText(f"Current key: {masked}")
            else:
                self.lbl_key_status.setText("⚠️ Key Storage Error")
                self.lbl_key_status.setStyleSheet("color: #ef4444;")
        else:
            self.lbl_key_status.setText("🔒 No API Key Configured")
            self.lbl_key_status.setStyleSheet("color: #f59e0b;")
            self.lbl_key_preview.setText("")

    def _on_key_changed(self, text: str):
        """Enable/disable buttons based on input."""
        has_text = len(text.strip()) >= 20 and text.strip().startswith("gsk_")
        self.btn_test.setEnabled(has_text)
        self.btn_save.setEnabled(has_text)

    def _toggle_visibility(self):
        """Toggle password visibility."""
        if self.input_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_visibility.setText("🙈 Hide")
        else:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_visibility.setText("👁 Show")

    def _test_connection(self):
        """Test the API key with Groq."""
        api_key = self.input_api_key.text().strip()
        if not api_key:
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing...")
        self.test_progress.setVisible(True)
        self.lbl_test_result.setText("")

        self.test_worker = TestConnectionWorker(api_key, self)
        self.test_worker.test_complete.connect(self._on_test_complete)
        self.test_worker.start()

    @pyqtSlot(bool, str)
    def _on_test_complete(self, success: bool, message: str):
        """Handle test connection result."""
        self.test_progress.setVisible(False)
        self.btn_test.setEnabled(True)
        self.btn_test.setText("🔗 Test Connection")

        if success:
            self.lbl_test_result.setText(f"✅ {message}")
            self.lbl_test_result.setStyleSheet("color: #10b981; font-size: 12px;")
        else:
            self.lbl_test_result.setText(f"❌ {message}")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-size: 12px;")

    def _save_key(self):
        """Save the API key securely."""
        api_key = self.input_api_key.text().strip()
        if not api_key:
            return

        # Save via key manager
        if self.key_manager.save_key(api_key):
            self.key_saved.emit(api_key)
            QMessageBox.information(
                self,
                "Success",
                "API key saved securely!\n\nAI Assistant is now enabled.",
                QMessageBox.StandardButton.Ok
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to save API key. Check permissions.",
                QMessageBox.StandardButton.Ok
            )

    def _delete_key(self):
        """Delete the stored API key."""
        reply = QMessageBox.question(
            self,
            "Delete API Key",
            "Are you sure you want to delete the stored API key?\nThis will disable AI features.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.key_manager.delete_key():
                self._load_current_key()
                self.input_api_key.clear()
                self.lbl_test_result.clear()
                QMessageBox.information(
                    self,
                    "Deleted",
                    "API key removed. AI features disabled.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to delete API key.",
                    QMessageBox.StandardButton.Ok
                )