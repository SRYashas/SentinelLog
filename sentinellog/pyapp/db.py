"""
SentinelLog — SQLite Database Layer
====================================
Handles all local database operations using Python's built-in sqlite3.
No external database server required.

Tables:
  - events: Process creation, script block, and module log events
  - threat_rules: Custom pattern-based risk detection rules
  - app_state: Key-value store for collector state (last poll timestamp, etc.)
"""

import sqlite3
import os
import json
from datetime import datetime, timezone


DB_NAME = 'sentinellog.db'


def get_db_path():
    """Return the path to the SQLite database file, co-located with the app."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, DB_NAME)


def get_connection():
    """Create and return a new SQLite connection with WAL mode for concurrency."""
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """
    Initialize the SQLite database with all required tables.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ── Events Table ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('process_create', 'script_block', 'module_log')),
            process_name TEXT DEFAULT '',
            command_line TEXT DEFAULT '',
            pid INTEGER DEFAULT 0,
            parent_process_name TEXT DEFAULT '',
            parent_command_line TEXT DEFAULT '',
            parent_pid INTEGER DEFAULT 0,
            user_account TEXT DEFAULT '',
            script_block_text TEXT DEFAULT '',
            hash_sha256 TEXT DEFAULT '',

            -- Origin resolution fields
            origin_resolved INTEGER DEFAULT 0,
            origin_source TEXT DEFAULT 'unknown',
            origin_detail TEXT DEFAULT '',

            -- Risk scoring fields
            risk_level TEXT DEFAULT 'info' CHECK(risk_level IN ('info', 'suspicious', 'high')),
            risk_reasons TEXT DEFAULT '[]',

            -- Metadata
            raw_xml TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Indexes for fast querying ────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_process ON events(process_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_risk ON events(risk_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_origin ON events(origin_resolved)")

    # ── Threat Rules Table ───────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threat_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            pattern TEXT NOT NULL,
            pattern_type TEXT DEFAULT 'regex' CHECK(pattern_type IN ('regex', 'substring', 'exact')),
            target_field TEXT DEFAULT 'command_line',
            risk_level TEXT DEFAULT 'suspicious' CHECK(risk_level IN ('suspicious', 'high')),
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── App State Table (key-value store) ────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Insert default threat rules if table is empty ────────────────
    cursor.execute("SELECT COUNT(*) FROM threat_rules")
    if cursor.fetchone()[0] == 0:
        _insert_default_rules(cursor)

    conn.commit()
    conn.close()
    return True


def _insert_default_rules(cursor):
    """Insert the built-in threat detection rules."""
    default_rules = [
        # High Risk Rules
        ("Base64 Encoded PowerShell", "Detects -EncodedCommand / -enc flags", r"(?i)-e(nc|ncodedcommand)\s+", "regex", "command_line", "high"),
        ("Hidden Window Execution", "PowerShell with -WindowStyle Hidden + -NoProfile", r"(?i)-windowstyle\s+hidden.*-noprofile|-noprofile.*-windowstyle\s+hidden", "regex", "command_line", "high"),
        ("Download Cradle (WebClient)", "IEX with Net.WebClient download", r"(?i)(iex|invoke-expression).*new-object\s+net\.webclient", "regex", "command_line", "high"),
        ("Download Cradle (DownloadString)", ".DownloadString() or .DownloadFile()", r"(?i)\.(downloadstring|downloadfile|downloaddata)\(", "regex", "command_line", "high"),
        ("Certutil URL Cache", "certutil -urlcache abuse for download", r"(?i)certutil.*-urlcache\s+-f", "regex", "command_line", "high"),
        ("Certutil Decode", "certutil -decode for payload extraction", r"(?i)certutil.*-decode", "regex", "command_line", "high"),
        ("MSHTA Execution", "mshta.exe script host abuse", r"(?i)mshta(\.exe)?\s+", "regex", "command_line", "high"),
        ("WScript/CScript Execution", "Windows Script Host execution", r"(?i)(wscript|cscript)(\.exe)?\s+", "regex", "command_line", "high"),

        # Suspicious Rules
        ("BITS Transfer", "bitsadmin /transfer for file download", r"(?i)bitsadmin.*/(transfer|addfile)", "regex", "command_line", "suspicious"),
        ("Long Base64 String", "Command line contains base64 string >100 chars", r"[A-Za-z0-9+/=]{100,}", "regex", "command_line", "suspicious"),
        ("PowerShell Bypass Policy", "Execution policy bypass flag", r"(?i)-executionpolicy\s+(bypass|unrestricted)", "regex", "command_line", "suspicious"),
        ("Invoke-WebRequest", "PowerShell web request command", r"(?i)invoke-webrequest|wget\s+http|curl\s+http", "regex", "command_line", "suspicious"),
        ("Reg Add/Delete", "Registry modification via reg.exe", r"(?i)reg\s+(add|delete)\s+", "regex", "command_line", "suspicious"),
        ("Schtasks Create", "Scheduled task creation", r"(?i)schtasks\s+/create", "regex", "command_line", "suspicious"),
        ("Net User Commands", "User account manipulation", r"(?i)net\s+(user|localgroup)\s+", "regex", "command_line", "suspicious"),
    ]

    for name, desc, pattern, ptype, target, level in default_rules:
        cursor.execute(
            "INSERT INTO threat_rules (name, description, pattern, pattern_type, target_field, risk_level) VALUES (?, ?, ?, ?, ?, ?)",
            (name, desc, pattern, ptype, target, level)
        )


# ── CRUD Operations ──────────────────────────────────────────────────

def insert_event(event_dict):
    """Insert a single event record. Returns the new row ID."""
    conn = get_connection()
    cursor = conn.cursor()

    risk_reasons = event_dict.get('risk_reasons', [])
    if isinstance(risk_reasons, list):
        risk_reasons = json.dumps(risk_reasons)

    cursor.execute("""
        INSERT INTO events (
            timestamp, event_type, process_name, command_line, pid,
            parent_process_name, parent_command_line, parent_pid,
            user_account, script_block_text, hash_sha256,
            origin_resolved, origin_source, origin_detail,
            risk_level, risk_reasons, raw_xml
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
        event_dict.get('event_type', 'process_create'),
        event_dict.get('process_name', ''),
        event_dict.get('command_line', ''),
        event_dict.get('pid', 0),
        event_dict.get('parent_process_name', ''),
        event_dict.get('parent_command_line', ''),
        event_dict.get('parent_pid', 0),
        event_dict.get('user_account', ''),
        event_dict.get('script_block_text', ''),
        event_dict.get('hash_sha256', ''),
        1 if event_dict.get('origin_resolved', False) else 0,
        event_dict.get('origin_source', 'unknown'),
        event_dict.get('origin_detail', ''),
        event_dict.get('risk_level', 'info'),
        risk_reasons,
        event_dict.get('raw_xml', '')
    ))

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def insert_events_batch(events_list):
    """Insert multiple events in a single transaction for performance."""
    conn = get_connection()
    cursor = conn.cursor()

    for event_dict in events_list:
        risk_reasons = event_dict.get('risk_reasons', [])
        if isinstance(risk_reasons, list):
            risk_reasons = json.dumps(risk_reasons)

        cursor.execute("""
            INSERT INTO events (
                timestamp, event_type, process_name, command_line, pid,
                parent_process_name, parent_command_line, parent_pid,
                user_account, script_block_text, hash_sha256,
                origin_resolved, origin_source, origin_detail,
                risk_level, risk_reasons, raw_xml
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
            event_dict.get('event_type', 'process_create'),
            event_dict.get('process_name', ''),
            event_dict.get('command_line', ''),
            event_dict.get('pid', 0),
            event_dict.get('parent_process_name', ''),
            event_dict.get('parent_command_line', ''),
            event_dict.get('parent_pid', 0),
            event_dict.get('user_account', ''),
            event_dict.get('script_block_text', ''),
            event_dict.get('hash_sha256', ''),
            1 if event_dict.get('origin_resolved', False) else 0,
            event_dict.get('origin_source', 'unknown'),
            event_dict.get('origin_detail', ''),
            event_dict.get('risk_level', 'info'),
            risk_reasons,
            event_dict.get('raw_xml', '')
        ))

    conn.commit()
    conn.close()
    return len(events_list)


def query_events(limit=50, offset=0, risk_level=None, event_type=None,
                 process_name=None, search=None, origin_unresolved=False):
    """Query events with filtering and pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if risk_level:
        levels = [l.strip() for l in risk_level.split(',')]
        placeholders = ','.join('?' * len(levels))
        where_clauses.append(f"risk_level IN ({placeholders})")
        params.extend(levels)

    if event_type:
        where_clauses.append("event_type = ?")
        params.append(event_type)

    if process_name:
        where_clauses.append("process_name LIKE ?")
        params.append(f"%{process_name}%")

    if search:
        where_clauses.append("(command_line LIKE ? OR script_block_text LIKE ? OR process_name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if origin_unresolved:
        where_clauses.append("origin_resolved = 0")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM events {where_sql}", params)
    total = cursor.fetchone()[0]

    # Get paginated results
    cursor.execute(
        f"SELECT * FROM events {where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    rows = [dict(row) for row in cursor.fetchall()]

    # Parse risk_reasons JSON
    for row in rows:
        try:
            row['risk_reasons'] = json.loads(row.get('risk_reasons', '[]'))
        except (json.JSONDecodeError, TypeError):
            row['risk_reasons'] = []

    conn.close()
    return {'events': rows, 'total': total, 'limit': limit, 'offset': offset}


def get_event_by_id(event_id):
    """Get a single event by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        result = dict(row)
        try:
            result['risk_reasons'] = json.loads(result.get('risk_reasons', '[]'))
        except (json.JSONDecodeError, TypeError):
            result['risk_reasons'] = []
        return result
    return None


def get_stats_summary():
    """Get dashboard summary statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total events
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    # Events in last 24h
    cursor.execute("SELECT COUNT(*) FROM events WHERE timestamp >= datetime('now', '-24 hours')")
    recent_total = cursor.fetchone()[0]

    # Risk counts
    risk_counts = {'info': 0, 'suspicious': 0, 'high': 0}
    cursor.execute("SELECT risk_level, COUNT(*) as cnt FROM events GROUP BY risk_level")
    for row in cursor.fetchall():
        risk_counts[row['risk_level']] = row['cnt']

    # Unresolved count
    cursor.execute("SELECT COUNT(*) FROM events WHERE origin_resolved = 0")
    unresolved_count = cursor.fetchone()[0]

    # Top processes
    cursor.execute("""
        SELECT process_name, COUNT(*) as cnt FROM events
        WHERE process_name != ''
        GROUP BY process_name ORDER BY cnt DESC LIMIT 10
    """)
    top_processes = [{'process_name': row['process_name'], 'count': row['cnt']} for row in cursor.fetchall()]

    # Top unresolved processes
    cursor.execute("""
        SELECT process_name, COUNT(*) as cnt FROM events
        WHERE origin_resolved = 0 AND process_name != ''
        GROUP BY process_name ORDER BY cnt DESC LIMIT 5
    """)
    top_unresolved = [{'process_name': row['process_name'], 'count': row['cnt']} for row in cursor.fetchall()]

    # Events per hour (last 24h)
    cursor.execute("""
        SELECT strftime('%H:00', timestamp) as hour, COUNT(*) as cnt
        FROM events
        WHERE timestamp >= datetime('now', '-24 hours')
        GROUP BY hour ORDER BY hour
    """)
    events_per_hour = [{'hour': row['hour'], 'count': row['cnt']} for row in cursor.fetchall()]

    conn.close()
    return {
        'total_events': total_events,
        'recent_total': recent_total,
        'risk_counts': risk_counts,
        'unresolved_count': unresolved_count,
        'top_processes': top_processes,
        'top_unresolved': top_unresolved,
        'events_per_hour': events_per_hour
    }


def get_threat_rules():
    """Get all enabled threat detection rules."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM threat_rules WHERE enabled = 1")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules


def get_state(key, default=''):
    """Get a value from app_state."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_state(key, value):
    """Set a value in app_state (upsert)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, value))
    conn.commit()
    conn.close()
