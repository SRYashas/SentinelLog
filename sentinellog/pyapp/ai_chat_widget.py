"""
SentinelLog — AI Chat Widget
=============================
Modern chat interface with streaming responses, Markdown rendering,
syntax highlighting for code blocks, and conversation history.
"""

import markdown
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QScrollArea, QLabel, QFrame, QSizePolicy,
    QMessageBox, QSplitter
)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QTextDocument
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

from .groq_client import GroqClient, LogContext, create_log_context_from_event
from .api_key_manager import get_key_manager


class MarkdownRenderer(QWebEngineView):
    """
    Renders Markdown with syntax highlighting using highlight.js.
    Supports streaming updates by appending to content.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.page().setBackgroundColor(QColor("#030712"))

        # Enable local content access for highlight.js
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self._html_template = self._get_html_template()
        self._current_content = ""
        self.setHtml(self._html_template.format(content=""))

    def _get_html_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    background-color: #030712;
                    color: #e2e8f0;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    font-size: 13px;
                    line-height: 1.6;
                    margin: 0;
                    padding: 16px;
                }}
                pre {{ background: #0f172a; border-radius: 6px; padding: 12px; overflow-x: auto; border: 1px solid #1e293b; }}
                code {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }}
                pre code {{ background: transparent; padding: 0; color: #e2e8f0; }}
                .hljs {{ background: transparent; }}
                .hljs-keyword {{ color: #c084fc; }}
                .hljs-string {{ color: #a7f3d0; }}
                .hljs-comment {{ color: #64748b; }}
                .hljs-function {{ color: #60a5fa; }}
                .hljs-number {{ color: #fde047; }}
                .hljs-operator {{ color: #f472b6; }}
                .hljs-punctuation {{ color: #94a3b8; }}
                .hljs-built_in {{ color: #34d399; }}
                .hljs-type {{ color: #fbbf24; }}
                h1, h2, h3, h4 {{ color: #38bdf8; margin-top: 16px; margin-bottom: 8px; }}
                h2 {{ border-bottom: 1px solid #1e293b; padding-bottom: 4px; }}
                strong {{ color: #f8fafc; }}
                em {{ color: #94a3b8; }}
                ul, ol {{ padding-left: 20px; }}
                li {{ margin: 4px 0; }}
                blockquote {{ border-left: 3px solid #06b6d4; padding-left: 12px; color: #94a3b8; margin: 12px 0; }}
                a {{ color: #38bdf8; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                hr {{ border: none; border-top: 1px solid #1e293b; margin: 16px 0; }}
                table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
                th, td {{ border: 1px solid #1e293b; padding: 8px 12px; text-align: left; }}
                th {{ background: #0f172a; color: #38bdf8; }}
                tr:nth-child(even) {{ background: #0f172a; }}
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
            <script>hljs.highlightAll();</script>
        </head>
        <body>
            {content}
            <script>
                // Re-highlight after content updates
                document.querySelectorAll('pre code').forEach((el) => {{
                    hljs.highlightElement(el);
                }});
            </script>
        </body>
        </html>
        """

    def set_markdown(self, markdown_text: str):
        """Render markdown text to HTML."""
        html = markdown.markdown(
            markdown_text,
            extensions=['fenced_code', 'codehilite', 'tables', 'toc']
        )
        self._current_content = html
        self.setHtml(self._html_template.format(content=html))

    def append_markdown(self, markdown_text: str):
        """Append markdown to existing content and re-render."""
        # Convert new markdown to HTML
        new_html = markdown.markdown(
            markdown_text,
            extensions=['fenced_code', 'codehilite', 'tables', 'toc']
        )
        self._current_content += new_html
        self.setHtml(self._html_template.format(content=self._current_content))

    def clear(self):
        """Clear all content."""
        self._current_content = ""
        self.setHtml(self._html_template.format(content=""))


class MessageWidget(QFrame):
    """A single chat message bubble (user or AI)."""

    def __init__(self, is_user: bool, content: str = "", parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        if is_user:
            layout.addStretch()

        # Message bubble
        self.bubble = QFrame()
        self.bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        self.bubble.setMaximumWidth(700)
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(4)

        if is_user:
            self.bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #2563eb);
                    border-radius: 12px;
                    border-bottom-right-radius: 2px;
                }
            """)
            self.content_label = QLabel(content)
            self.content_label.setStyleSheet("color: white; font-size: 13px;")
            self.content_label.setWordWrap(True)
            self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bubble_layout.addWidget(self.content_label)
        else:
            self.bubble.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #1e293b;
                    border-radius: 12px;
                    border-bottom-left-radius: 2px;
                }
            """)
            self.renderer = MarkdownRenderer()
            self.renderer.setMinimumHeight(60)
            self.renderer.setMaximumHeight(800)
            self.renderer.set_markdown(content)
            bubble_layout.addWidget(self.renderer)

        layout.addWidget(self.bubble)

        if not is_user:
            layout.addStretch()

    def append_content(self, chunk: str):
        """Append streaming content to AI message."""
        if not self.is_user and hasattr(self, 'renderer'):
            self.renderer.append_markdown(chunk)

    def set_content(self, content: str):
        """Set full content (for user messages or final AI message)."""
        if self.is_user:
            self.content_label.setText(content)
        elif hasattr(self, 'renderer'):
            self.renderer.set_markdown(content)


class ChatInputWidget(QWidget):
    """Chat input area with send button and quick actions."""

    send_message = pyqtSignal(str)
    ask_ai_clicked = pyqtSignal(object)  # LogContext

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # Quick action buttons row
        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(8)

        btn_analyze = QPushButton("🔍 Analyze Selected Log")
        btn_analyze.setObjectName("quickActionBtn")
        btn_analyze.clicked.connect(lambda: self.ask_ai_clicked.emit("analyze_selected"))
        quick_actions.addWidget(btn_analyze)

        btn_remediate = QPushButton("🛡️ Get Remediation")
        btn_remediate.setObjectName("quickActionBtn")
        btn_remediate.clicked.connect(lambda: self.ask_ai_clicked.emit("remediate_selected"))
        quick_actions.addWidget(btn_remediate)

        btn_explain = QPushButton("📖 Explain Technique")
        btn_explain.setObjectName("quickActionBtn")
        btn_explain.clicked.connect(lambda: self.ask_ai_clicked.emit("explain_selected"))
        quick_actions.addWidget(btn_explain)

        quick_actions.addStretch()
        layout.addLayout(quick_actions)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about a threat, request remediation, or continue the conversation...")
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self._on_send)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #06b6d4;
            }
        """)
        input_row.addWidget(self.input_field, stretch=1)

        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("btnAction")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.setMinimumWidth(80)
        self.btn_send.clicked.connect(self._on_send)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.send_message.emit(text)
            self.input_field.clear()

    def set_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.btn_send.setEnabled(enabled)


class AIChatWidget(QWidget):
    """
    Main AI Chat Interface Widget.
    Features:
    - Streaming responses from Groq API
    - Markdown + syntax highlighting
    - Conversation history
    - Context injection for log analysis
    - Quick action buttons
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groq_client: Optional[GroqClient] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.current_context: Optional[LogContext] = None
        self._streaming_worker: Optional[QThread] = None
        self._init_ui()
        self._check_api_key()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🤖 AI Threat Analyst")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("🔒 Offline Mode")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px 10px; background: #0f172a; border-radius: 4px;")
        header.addWidget(self.status_label)

        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_settings.setObjectName("btnSecondary")
        self.btn_settings.setMinimumWidth(100)
        header.addWidget(self.btn_settings)

        layout.addLayout(header)

        # Disclaimer banner (shown once when online mode activates)
        self.disclaimer_banner = QFrame()
        self.disclaimer_banner.setStyleSheet("""
            QFrame {
                background: #451a03;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.disclaimer_banner.setVisible(False)
        disc_layout = QHBoxLayout(self.disclaimer_banner)
        disc_label = QLabel(
            "⚠️ <b>Privacy Notice:</b> AI Analysis sends log data to Groq servers. "
            "Do not use for highly classified environments."
        )
        disc_label.setStyleSheet("color: #fcd34d; font-size: 11px;")
        disc_label.setWordWrap(True)
        self.btn_dismiss_disclaimer = QPushButton("Dismiss")
        self.btn_dismiss_disclaimer.setObjectName("btnSecondary")
        self.btn_dismiss_disclaimer.setMaximumWidth(80)
        self.btn_dismiss_disclaimer.clicked.connect(lambda: self.disclaimer_banner.setVisible(False))
        disc_layout.addWidget(disc_label, stretch=1)
        disc_layout.addWidget(self.btn_dismiss_disclaimer)
        layout.addWidget(self.disclaimer_banner)

        # Chat messages area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #030712;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background: #030712;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #334155;
            }
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # Input area
        self.input_widget = ChatInputWidget()
        self.input_widget.send_message.connect(self._on_user_message)
        self.input_widget.ask_ai_clicked.connect(self._on_quick_action)
        self.input_widget.set_enabled(False)
        layout.addWidget(self.input_widget)

        # Welcome message
        self._add_welcome_message()

    def _add_welcome_message(self):
        welcome = MessageWidget(
            is_user=False,
            content="""## Welcome to SentinelLog AI Assistant 🛡️

I'm your AI-powered threat analyst powered by **Llama 3 on Groq**.

**Capabilities:**
- Analyze suspicious Windows event logs (Sysmon, PowerShell, etc.)
- Explain attack techniques with MITRE ATT&CK mapping
- Provide exact remediation commands (PowerShell/CMD)
- Answer follow-up questions about threats

**To get started:**
1. Click **Settings** to configure your Groq API key
2. Select a log entry in the dashboard
3. Click **Ask AI** buttons or type your question

*Note: AI features require internet connection and a valid Groq API key.*"""
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, welcome)
        self._scroll_to_bottom()

    def _check_api_key(self):
        """Check if API key is configured and update UI accordingly."""
        key_manager = get_key_manager()
        if key_manager.has_key():
            api_key = key_manager.get_key()
            if api_key:
                self._initialize_groq_client(api_key)
                self._set_online_mode(True)
            else:
                self._set_online_mode(False)
        else:
            self._set_online_mode(False)

    def _initialize_groq_client(self, api_key: str):
        """Initialize the Groq client with the API key."""
        try:
            self.groq_client = GroqClient(api_key)
        except Exception as e:
            self._add_system_message(f"Failed to initialize AI client: {e}")

    def _set_online_mode(self, online: bool):
        """Update UI for online/offline mode."""
        if online:
            self.status_label.setText("🟢 Online Mode — AI Ready")
            self.status_label.setStyleSheet("color: #10b981; font-size: 11px; padding: 4px 10px; background: #064e3b; border-radius: 4px;")
            self.input_widget.set_enabled(True)
            self.disclaimer_banner.setVisible(True)
        else:
            self.status_label.setText("🔒 Offline Mode — Configure API Key")
            self.status_label.setStyleSheet("color: #f59e0b; font-size: 11px; padding: 4px 10px; background: #451a03; border-radius: 4px;")
            self.input_widget.set_enabled(False)

    def _add_user_message(self, text: str):
        msg = MessageWidget(is_user=True, content=text)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg)
        self.conversation_history.append({"role": "user", "content": text})
        self._scroll_to_bottom()

    def _add_ai_message(self) -> MessageWidget:
        """Add empty AI message widget for streaming."""
        msg = MessageWidget(is_user=False, content="")
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg)
        return msg

    def _add_system_message(self, text: str):
        """Add a system/status message."""
        msg = MessageWidget(is_user=False, content=f"*{text}*")
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll chat to bottom."""
        QThread.msleep(50)  # Allow layout to update
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    @pyqtSlot(str)
    def _on_user_message(self, text: str):
        """Handle user sending a message."""
        if not self.groq_client:
            self._add_system_message("AI not initialized. Check API key in Settings.")
            return

        self._add_user_message(text)

        # Stream response
        ai_msg = self._add_ai_message()
        self._start_streaming(ai_msg, text)

    def _start_streaming(self, ai_msg: MessageWidget, user_text: str):
        """Start streaming response in background thread."""
        from PyQt6.QtCore import QThread

        class StreamWorker(QThread):
            chunk_received = pyqtSignal(str)
            finished = pyqtSignal(str)
            error = pyqtSignal(str)

            def __init__(self, client, history, context, user_text):
                super().__init__()
                self.client = client
                self.history = history
                self.context = context
                self.user_text = user_text
                self.full_response = ""

            def run(self):
                try:
                    # Check if this is a new log analysis or follow-up
                    if self.context and not self.history:
                        # First message with log context
                        async def stream():
                            async for chunk in self.client.stream_chat(self.context):
                                self.chunk_received.emit(chunk)
                                self.full_response += chunk
                        asyncio.run(stream())
                    else:
                        # Follow-up question
                        async def stream():
                            async for chunk in self.client.stream_followup(
                                self.user_text, self.history, self.context
                            ):
                                self.chunk_received.emit(chunk)
                                self.full_response += chunk
                        asyncio.run(stream())
                    self.finished.emit(self.full_response)
                except Exception as e:
                    self.error.emit(str(e))

        self._streaming_worker = StreamWorker(
            self.groq_client,
            self.conversation_history,
            self.current_context,
            user_text
        )
        self._streaming_worker.chunk_received.connect(ai_msg.append_content)
        self._streaming_worker.finished.connect(lambda full: self._on_stream_finished(ai_msg, full))
        self._streaming_worker.error.connect(lambda err: self._on_stream_error(ai_msg, err))
        self._streaming_worker.start()

    def _on_stream_finished(self, ai_msg: MessageWidget, full_response: str):
        """Handle streaming completion."""
        self.conversation_history.append({"role": "assistant", "content": full_response})
        self._scroll_to_bottom()

    def _on_stream_error(self, ai_msg: MessageWidget, error: str):
        """Handle streaming error."""
        ai_msg.append_content(f"\n\n❌ **Error:** {error}")
        self._scroll_to_bottom()

    @pyqtSlot(object)
    def _on_quick_action(self, action: str):
        """Handle quick action button clicks."""
        if not self.current_context:
            self._add_system_message("No log selected. Click a log entry in the dashboard first.")
            return

        prompts = {
            "analyze_selected": "Analyze this log entry in detail. What happened, how, and why?",
            "remediate_selected": "Provide exact remediation steps and PowerShell/CMD commands to mitigate this threat.",
            "explain_selected": "Explain the specific attack technique used here with MITRE ATT&CK references."
        }

        prompt = prompts.get(action, "Analyze this log.")
        self._on_user_message(prompt)

    def set_log_context(self, event_dict: dict):
        """Set the current log context for analysis."""
        self.current_context = create_log_context_from_event(event_dict)
        self.conversation_history = []  # Reset history for new context
        self._clear_messages()
        self._add_welcome_message()

        # Auto-send analysis prompt
        self._add_system_message(f"📋 **Log Context Loaded:** Event #{self.current_context.event_id} — {self.current_context.process_name} ({self.current_context.risk_level.upper()})")
        self._on_user_message("Analyze this log entry in detail. What happened, how, and why?")

    def _clear_messages(self):
        """Clear all messages except welcome."""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def open_settings(self):
        """Open the API settings modal."""
        from .settings_modal import APISettingsDialog
        dialog = APISettingsDialog(self)
        dialog.key_saved.connect(self._on_key_saved)
        dialog.exec()

    @pyqtSlot(str)
    def _on_key_saved(self, api_key: str):
        """Handle API key saved from settings."""
        self._initialize_groq_client(api_key)
        self._set_online_mode(True)
        self._add_system_message("✅ API key configured. AI Assistant is now online.")