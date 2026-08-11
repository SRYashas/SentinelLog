"""
SentinelLog — PyQt6 Native Desktop Dashboard
==============================================
Dark-themed native desktop UI with dual-mode operation (Offline/Online).
Includes interactive metrics, pyqtgraph time-series charts, live timeline table,
origin badges, risk indicators, full command line inspection drawer,
and AI-powered threat analysis via Groq API when online.
"""

import sys
import os
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QThread
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QTabWidget, QSplitter, QFrame,
    QScrollArea, QDialog, QTextEdit, QApplication, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

import pyqtgraph as pg

from . import db
from . import event_reader
from . import threat_scorer
from . import connectivity_monitor
from . import ai_chat_widget


class DashboardWindow(QMainWindow):
    """
    Main Application Desktop Window with dual-mode operation.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SentinelLog — Windows Activity Monitor")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 650)

        # Current event context for AI analysis
        self.current_event_context = None

        self._apply_dark_theme()
        self._init_ui()

        # Start 5-second log collection poll timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_event_logs)
        self.poll_timer.start(5000)

        # Initialize connectivity monitor
        self.connectivity_monitor = connectivity_monitor.ConnectivityMonitor()
        self.connectivity_monitor.connectivity_changed.connect(self._on_connectivity_changed)
        self.connectivity_monitor.start()

        # Initial data load
        self._refresh_all_data()
        self._update_mode_display()

    def _apply_dark_theme(self):
        """Apply modern dark CSS stylesheet."""
        self.setStyleSheet("""
            QMainWindow, QWidget#bgWidget {
                background-color: #030712;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QFrame#sidebar {
                background-color: #090d16;
                border-right: 1px solid #1e293b;
            }
            QFrame#card {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QLabel#cardTitle {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }
            QLabel#cardValue {
                color: #f8fafc;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton#navBtn {
                background-color: transparent;
                color: #94a3b8;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#navBtn:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QPushButton#navBtn:checked {
                background-color: #0e7490;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #090d16;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: 1px solid #1e293b;
                border-radius: 8px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #030712;
                color: #94a3b8;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #1e293b;
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #06b6d4;
            }
            QPushButton#btnAction {
                background-color: #0891b2;
                color: #ffffff;
                font-weight: 600;
                padding: 6px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton#btnAction:hover {
                background-color: #06b6d4;
            }
        """)

    def _init_ui(self):
        """Build responsive desktop UI layout."""
        central_widget = QWidget()
        central_widget.setObjectName("bgWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left Navigation Sidebar ──────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(8)

        logo_label = QLabel("���🛡��️ SentinelLog")
        logo_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: #38bdf8;")

        sub_logo = QLabel("PROCESS & LOG MONITOR")
        sub_logo.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; margin-bottom: 16px;")

        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addWidget(sub_logo)

        # Navigation Buttons
        self.btn_nav_overview = QPushButton("���📊 Overview")
        self.btn_nav_overview.setObjectName("navBtn")
        self.btn_nav_overview.setCheckable(True)
        self.btn_nav_overview.setChecked(True)
        self.btn_nav_overview.clicked.connect(lambda: self.switch_tab(0))

        self.btn_nav_timeline = QPushButton("��⚡ Live Timeline")
        self.btn_nav_timeline.setObjectName("navBtn")
        self.btn_nav_timeline.setCheckable(True)
        self.btn_nav_timeline.clicked.connect(lambda: self.switch_tab(1))

        self.btn_nav_unresolved = QPushButton("��❓ Unknown Origins")
        self.btn_nav_unresolved.setObjectName("navBtn")
        self.btn_nav_unresolved.setCheckable(True)
        self.btn_nav_unresolved.clicked.connect(lambda: self.switch_tab(2))

        self.btn_nav_suspicious = QPushButton("���🚨 Suspicious Activity")
        self.btn_nav_suspicious.setObjectName("navBtn")
        self.btn_nav_suspicious.setCheckable(True)
        self.btn_nav_suspicious.clicked.connect(lambda: self.switch_tab(3))

        # AI Assistant Tab Button
        self.btn_nav_ai = QPushButton("���🤖 AI Assistant")
        self.btn_nav_ai.setObjectName("navBtn")
        self.btn_nav_ai.setCheckable(True)
        self.btn_nav_ai.clicked.connect(lambda: self.switch_tab(4))
        self.btn_nav_ai.setEnabled(False)  # Disabled until online

        sidebar_layout.addWidget(self.btn_nav_overview)
        sidebar_layout.addWidget(self.btn_nav_timeline)
        sidebar_layout.addWidget(self.btn_nav_unresolved)
        sidebar_layout.addWidget(self.btn_nav_suspicious)
        sidebar_layout.addWidget(self.btn_nav_ai)
        sidebar_layout.addStretch()

        # Mode indicator badge at bottom of sidebar
        self.mode_badge = QLabel("���🔒 Offline Mode")
        self.mode_badge.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; padding: 8px; background: #0f172a; border-radius: 6px;")
        sidebar_layout.addWidget(self.mode_badge)

        main_layout.addWidget(sidebar)

        # ── Right Main Content Area ──────────────────────────────────
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Tab Widget container (hidden tab bar, controlled by sidebar)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()

        # Build individual view tabs
        self.tab_overview = self._build_overview_tab()
        self.tab_timeline = self._build_timeline_tab()
        self.tab_unresolved = self._build_unresolved_tab()
        self.tab_suspicious = self._build_suspicious_tab()
        self.tab_ai = self._build_ai_tab()

        self.tabs.addTab(self.tab_overview, "Overview")
        self.tabs.addTab(self.tab_timeline, "Timeline")
        self.tabs.addTab(self.tab_unresolved, "Unresolved")
        self.tabs.addTab(self.tab_suspicious, "Suspicious")
        self.tabs.addTab(self.tab_ai, "AI Assistant")

        content_layout.addWidget(self.tabs)
        main_layout.addWidget(content_area)

    def switch_tab(self, index):
        """Switch active view tab from sidebar button clicks."""
        self.tabs.setCurrentIndex(index)
        self.btn_nav_overview.setChecked(index == 0)
        self.btn_nav_timeline.setChecked(index == 1)
        self.btn_nav_unresolved.setChecked(index == 2)
        self.btn_nav_suspicious.setChecked(index == 3)
        self.btn_nav_ai.setChecked(index == 4)
        self._refresh_all_data()

    # ── Tab 1: Overview View ─────────────────────────────────────────

    def _build_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Top Bar
        top_bar = QHBoxLayout()
        header = QLabel("System Activity Overview")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("btnAction")
        btn_refresh.clicked.connect(self._refresh_all_data)

        top_bar.addWidget(header)
        top_bar.addStretch()
        top_bar.addWidget(btn_refresh)
        layout.addLayout(top_bar)

        # Stat Cards Grid
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.card_total = self._create_card("TOTAL EVENTS (24H)", "0")
        self.card_unresolved = self._create_card("UNEXPLAINED ORIGINS", "0", "#f43f5e")
        self.card_high = self._create_card("HIGH RISK FLAGS", "0", "#ef4444")
        self.card_suspicious = self._create_card("SUSPICIOUS COMMANDS", "0", "#f59e0b")

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_unresolved)
        cards_layout.addWidget(self.card_high)
        cards_layout.addWidget(self.card_suspicious)
        layout.addLayout(cards_layout)

        # Chart: 24h Activity Graph using pyqtgraph
        pg.setConfigOption('background', '#0f172a')
        pg.setConfigOption('foreground', '#94a3b8')

        self.graph_widget = pg.PlotWidget(title="Event Activity Frequency (Last 24h)")
        self.graph_widget.showGrid(x=True, y=True, alpha=0.2)
        self.graph_widget.setFixedHeight(220)
        layout.addWidget(self.graph_widget)

        # Table: Recent Activity Preview
        table_header = QLabel("Latest Process Creation & Console Activity")
        table_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(table_header)

        self.table_overview = self._create_event_table()
        layout.addWidget(self.table_overview)

        return widget

    def _create_card(self, title, value, accent_color="#38bdf8"):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("cardTitle")

        lbl_value = QLabel(value)
        lbl_value.setObjectName("cardValue")
        lbl_value.setStyleSheet(f"color: {accent_color};")

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_value)
        card.value_label = lbl_value
        return card

    # ── Tab 2: Timeline View ─────────────────────────────────────────

    def _build_timeline_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Search Toolbar
        toolbar = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Search command lines or script block text...")
        self.input_search.textChanged.connect(self._refresh_timeline)

        self.combo_risk = QComboBox()
        self.combo_risk.addItems(["All Risk Levels", "High Risk Only", "Suspicious Only", "Info Only"])
        self.combo_risk.currentIndexChanged.connect(self._refresh_timeline)

        toolbar.addWidget(self.input_search, stretch=3)
        toolbar.addWidget(self.combo_risk, stretch=1)
        layout.addLayout(toolbar)

        # Table
        self.table_timeline = self._create_event_table()
        layout.addWidget(self.table_timeline)

        return widget

    # ── Tab 3: Unresolved Origins View ───────────────────────────────

    def _build_unresolved_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        info_box = QLabel("❓ Unexplained Popups — Process creations with no registry, task, or service origin match.")
        info_box.setStyleSheet("background: #450a0a; color: #fca5a5; padding: 10px; border-radius: 6px; font-size: 12px;")
        layout.addWidget(info_box)

        self.table_unresolved = self._create_event_table()
        layout.addWidget(self.table_unresolved)

        return widget

    # ── Tab 4: Suspicious Activity View ─────────────────────────────

    def _build_suspicious_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        info_box = QLabel("���🚨 Threat Detection Matches — Events flagged by automated risk scoring rules.")
        info_box.setStyleSheet("background: #451a03; color: #fcd34d; padding: 10px; border-radius: 6px; font-size: 12px;")
        layout.addWidget(info_box)

        self.table_suspicious = self._create_event_table()
        layout.addWidget(self.table_suspicious)

        return widget

    # ── Tab 5: AI Assistant View ──────────────────────────────────────

    def _build_ai_tab(self):
        """Build the AI Assistant tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ai_chat = ai_chat_widget.AIChatWidget()
        layout.addWidget(self.ai_chat)

        return widget

    # ── Event Inspection Drawer Modal ─────────────────────────────────

    def _open_event_detail(self, item):
        table = QTableWidget()
        table.setColumnCount(7)  # Added column for Ask AI button
        table.setHorizontalHeaderLabels(["ID", "Timestamp", "Process", "Command Line / Script", "Origin", "Risk Level", "AI"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.itemDoubleClicked.connect(self._open_event_detail)
        return table

    def _populate_table(self, table, events):
        table.setRowCount(0)
        for row_idx, evt in enumerate(events):
            table.insertRow(row_idx)

            # ID
            table.setItem(row_idx, 0, QTableWidgetItem(str(evt.get('id', ''))))

            # Timestamp formatted
            ts = evt.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                formatted_ts = dt.strftime('%H:%M:%S (%b %d)')
            except Exception:
                formatted_ts = ts
            table.setItem(row_idx, 1, QTableWidgetItem(formatted_ts))

            # Process Name
            proc_item = QTableWidgetItem(evt.get('process_name', 'N/A'))
            proc_item.setForeground(QColor('#38bdf8'))
            table.setItem(row_idx, 2, proc_item)

            # Command Line
            cmd = evt.get('command_line') or evt.get('script_block_text') or 'N/A'
            table.setItem(row_idx, 3, QTableWidgetItem(cmd[:120]))

            # Origin
            origin_str = evt.get('origin_source', 'unknown').upper()
            if not evt.get('origin_resolved', False):
                origin_str = "❓ UNKNOWN"
            table.setItem(row_idx, 4, QTableWidgetItem(origin_str))

            # Risk Level
            risk = evt.get('risk_level', 'info').upper()
            risk_item = QTableWidgetItem(risk)
            if risk == 'HIGH':
                risk_item.setForeground(QColor('#ef4444'))
            elif risk == 'SUSPICIOUS':
                risk_item.setForeground(QColor('#f59e0b'))
            else:
                risk_item.setForeground(QColor('#94a3b8'))

            table.setItem(row_idx, 5, risk_item)

            # Ask AI Button
            if self._is_online:
                btn_ask_ai = QPushButton("���������🤖")
                btn_ask_ai.setToolTip("Ask AI to analyze this log")
                btn_ask_ai.setMaximumWidth(30)
                btn_ask_ai.setMaximumHeight(24)
                btn_ask_ai.setStyleSheet("""
                    QPushButton {
                        background-color: #0f172a;
                        color: #38bdf8;
                        border: 1px solid #1e293b;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #1e293b;
                        color: #06b6d4;
                    }
                    QPushButton:pressed {
                        background-color: #0e7490;
                    }
                """)
                btn_ask_ai.clicked.connect(lambda checked, event=evt: self._on_ask_ai_clicked(event))
                table.setCellWidget(row_idx, 6, btn_ask_ai)
            else:
                # Show disabled button when offline
                btn_ask_ai = QPushButton("���������🔒")
                btn_ask_ai.setToolTip("Go online to use AI analysis")
                btn_ask_ai.setEnabled(False)
                btn_ask_ai.setMaximumWidth(30)
                btn_ask_ai.setMaximumHeight(24)
                btn_ask_ai.setStyleSheet("""
                    QPushButton {
                        background-color: #0f172a;
                        color: #64748b;
                        border: 1px solid #1e293b;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                """)
                table.setCellWidget(row_idx, 6, btn_ask_ai)

    # ── Log Polling Loop ──────────────────────────────────────────────

    def _poll_event_logs(self):
        """Poll Windows Event Logs and insert new events into SQLite."""
        try:
            last_poll = db.get_state('last_poll_time', None)

            # Read events
            sysmon_events = event_reader.poll_sysmon_events(since_time=last_poll)
            ps_events = event_reader.poll_powershell_events(since_time=last_poll)

            new_events = sysmon_events + ps_events
            if new_events:
                # Score and resolve origin
                processed = []
                for evt in new_events:
                    evt = threat_scorer.resolve_origin(evt)
                    evt = threat_scorer.score_event(evt)
                    processed.append(evt)

                db.insert_events_batch(processed)
                db.set_state('last_poll_time', datetime.utcnow().isoformat() + 'Z')
                self._refresh_all_data()

        except Exception as e:
            pass

    # ── Refresh Data ──────────────────────────────────────────────────

    def _refresh_all_data(self):
        """Refresh stats, charts, and visible tables."""
        stats = db.get_stats_summary()

        # Update card values
        self.card_total.value_label.setText(str(stats['recent_total']))
        self.card_unresolved.value_label.setText(str(stats['unresolved_count']))
        self.card_high.value_label.setText(str(stats['risk_counts'].get('high', 0)))
        self.card_suspicious.value_label.setText(str(stats['risk_counts'].get('suspicious', 0)))

        # Update pyqtgraph chart
        hours = [i for i in range(len(stats['events_per_hour']))]
        counts = [item['count'] for item in stats['events_per_hour']]
        self.graph_widget.clear()
        if counts:
            curve = self.graph_widget.plot(hours, counts, pen=pg.mkPen(color='#06b6d4', width=2), fillLevel=0, brush=(6, 182, 212, 50))

        # Populate tables
        events_all = db.query_events(limit=30)['events']
        self._populate_table(self.table_overview, events_all)

        self._refresh_timeline()

        unresolved_events = db.query_events(limit=50, origin_unresolved=True)['events']
        self._populate_table(self.table_unresolved, unresolved_events)

        suspicious_events = db.query_events(limit=50, risk_level='suspicious,high')['events']
        self._populate_table(self.table_suspicious, suspicious_events)

    def _refresh_timeline(self):
        search = self.input_search.text()
        risk_idx = self.combo_risk.currentIndex()
        risk_map = {0: None, 1: 'high', 2: 'suspicious', 3: 'info'}
        risk_val = risk_map.get(risk_idx)

        events = db.query_events(limit=50, search=search, risk_level=risk_val)['events']
        self._populate_table(self.table_timeline, events)

    # ── Event Inspection Drawer Modal ─────────────────────────────────

    def _open_event_detail(self, item):
        row = item.row()
        table = self.sender()
        event_id_item = table.item(row, 0)
        if not event_id_item:
            return

        event_id = int(event_id_item.text())
        evt = db.get_event_by_id(event_id)
        if not evt:
            return

        # Open Detail Modal
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Event Inspection — ID #{event_id}")
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("background: #030712; color: #38bdf8; font-family: Consolas; font-size: 12px;")

        details = f"""=== SENTINELLOG EVENT INSPECTION ===
ID:                 {evt.get('id')}
Timestamp:          {evt.get('timestamp')}
Event Type:         {evt.get('event_type')}
Process Name:       {evt.get('process_name')} (PID: {evt.get('pid')})
Parent Process:     {evt.get('parent_process_name')} (PID: {evt.get('parent_pid')})
User Context:       {evt.get('user_account')}
Risk Level:         {evt.get('risk_level').upper()}
Risk Reasons:       {', '.join(evt.get('risk_reasons', []))}
Origin Resolved:    {evt.get('origin_resolved')} ({evt.get('origin_source')})
Origin Detail:      {evt.get('origin_detail')}
SHA256 Hash:        {evt.get('hash_sha256')}

--- FULL COMMAND LINE ---
{evt.get('command_line')}

--- SCRIPT BLOCK CONTENT (EVENT ID 4104) ---
{evt.get('script_block_text')}
"""
        txt.setText(details)
        layout.addWidget(txt)
        dialog.exec()


def launch_dashboard():
    """Launch main PyQt6 desktop application."""
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
