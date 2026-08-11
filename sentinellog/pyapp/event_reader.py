"""
SentinelLog — Windows Event Log Reader
========================================
Reads Windows Event Logs via wevtutil subprocess and XML parsing.
Supports both live system log polling and .evtx file analysis.

Channels monitored:
  - Microsoft-Windows-Sysmon/Operational (Event ID 1 — Process Create)
  - Microsoft-Windows-PowerShell/Operational (Event ID 4104 — Script Block, 4103 — Module)
"""

import subprocess
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone


# XML namespace used by Windows Event Log
NS = '{http://schemas.microsoft.com/win/2004/08/events/event}'


def poll_event_log(channel, since_time=None, max_events=500):
    """
    Poll a Windows Event Log channel using wevtutil.

    Args:
        channel: Event log channel name (e.g. 'Microsoft-Windows-Sysmon/Operational')
        since_time: ISO timestamp to filter events after. None = get all.
        max_events: Maximum events to retrieve per poll.

    Returns:
        List of normalized event dicts, or empty list on error.
    """
    try:
        # Build XPath query
        xpath = '*'
        if since_time:
            # wevtutil XPath time filter
            xpath = f"*[System[TimeCreated[@SystemTime>='{since_time}']]]"

        cmd = [
            'wevtutil', 'qe', channel,
            '/q:' + xpath,
            '/f:xml',
            f'/c:{max_events}',
            '/rd:true'  # Reverse direction (newest first)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if 'channel not found' in error_msg.lower() or 'not found' in error_msg.lower():
                return []  # Channel doesn't exist (e.g. Sysmon not installed)
            return []

        # Parse XML events from output
        xml_text = result.stdout.strip()
        if not xml_text:
            return []

        # Wrap in root element for valid XML
        xml_text = f'<Events>{xml_text}</Events>'

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        events = []
        for event_el in root.findall(f'{NS}Event'):
            parsed = _parse_event_xml(event_el, channel)
            if parsed:
                events.append(parsed)

        return events

    except subprocess.TimeoutExpired:
        return []
    except FileNotFoundError:
        # wevtutil not available (not Windows)
        return []
    except Exception:
        return []


def poll_sysmon_events(since_time=None):
    """Poll Sysmon Process Create events (Event ID 1)."""
    channel = 'Microsoft-Windows-Sysmon/Operational'
    events = poll_event_log(channel, since_time)
    # Filter to Event ID 1 only (Process Create)
    return [e for e in events if e.get('_event_id') == '1']


def poll_powershell_events(since_time=None):
    """Poll PowerShell Script Block (4104) and Module (4103) events."""
    channel = 'Microsoft-Windows-PowerShell/Operational'
    events = poll_event_log(channel, since_time)
    # Filter to Event ID 4104 and 4103
    return [e for e in events if e.get('_event_id') in ('4104', '4103')]


def _parse_event_xml(event_el, channel):
    """Parse a single <Event> XML element into a normalized dict."""
    try:
        system = event_el.find(f'{NS}System')
        event_data = event_el.find(f'{NS}EventData')

        if system is None:
            return None

        # Extract System fields
        event_id_el = system.find(f'{NS}EventID')
        event_id = event_id_el.text if event_id_el is not None else ''

        time_created = system.find(f'{NS}TimeCreated')
        timestamp = time_created.get('SystemTime', '') if time_created is not None else ''

        # Build data dict from EventData
        data = {}
        if event_data is not None:
            for data_el in event_data.findall(f'{NS}Data'):
                name = data_el.get('Name', '')
                value = data_el.text or ''
                if name:
                    data[name] = value

        # Determine event type and normalize based on channel/event ID
        if 'Sysmon' in channel and event_id == '1':
            return _normalize_sysmon_event(timestamp, data, event_id, event_el)
        elif 'PowerShell' in channel and event_id == '4104':
            return _normalize_script_block(timestamp, data, event_id, event_el)
        elif 'PowerShell' in channel and event_id == '4103':
            return _normalize_module_log(timestamp, data, event_id, event_el)

        return None

    except Exception:
        return None


def _normalize_sysmon_event(timestamp, data, event_id, event_el):
    """Normalize a Sysmon Event ID 1 (Process Create)."""
    image = data.get('Image', '')
    process_name = os.path.basename(image) if image else data.get('OriginalFileName', '')

    parent_image = data.get('ParentImage', '')
    parent_name = os.path.basename(parent_image) if parent_image else ''

    return {
        '_event_id': event_id,
        'timestamp': timestamp,
        'event_type': 'process_create',
        'process_name': process_name,
        'command_line': data.get('CommandLine', ''),
        'pid': _safe_int(data.get('ProcessId', '0')),
        'parent_process_name': parent_name,
        'parent_command_line': data.get('ParentCommandLine', ''),
        'parent_pid': _safe_int(data.get('ParentProcessId', '0')),
        'user_account': data.get('User', ''),
        'hash_sha256': _extract_sha256(data.get('Hashes', '')),
        'raw_xml': ET.tostring(event_el, encoding='unicode', method='xml')
    }


def _normalize_script_block(timestamp, data, event_id, event_el):
    """Normalize a PowerShell Event ID 4104 (Script Block Logging)."""
    script_text = data.get('ScriptBlockText', '')
    # Try to extract the process name from the script path
    path = data.get('Path', '')
    process_name = 'powershell.exe'

    return {
        '_event_id': event_id,
        'timestamp': timestamp,
        'event_type': 'script_block',
        'process_name': process_name,
        'command_line': path,
        'pid': _safe_int(data.get('ProcessId', '0')),
        'parent_process_name': '',
        'parent_command_line': '',
        'parent_pid': 0,
        'user_account': '',
        'script_block_text': script_text,
        'hash_sha256': '',
        'raw_xml': ET.tostring(event_el, encoding='unicode', method='xml')
    }


def _normalize_module_log(timestamp, data, event_id, event_el):
    """Normalize a PowerShell Event ID 4103 (Module Logging)."""
    payload = data.get('Payload', '')

    return {
        '_event_id': event_id,
        'timestamp': timestamp,
        'event_type': 'module_log',
        'process_name': 'powershell.exe',
        'command_line': payload[:500] if payload else '',
        'pid': 0,
        'parent_process_name': '',
        'parent_command_line': '',
        'parent_pid': 0,
        'user_account': '',
        'script_block_text': payload,
        'hash_sha256': '',
        'raw_xml': ET.tostring(event_el, encoding='unicode', method='xml')
    }


def _extract_sha256(hashes_str):
    """Extract SHA256 hash from Sysmon Hashes field (format: 'SHA256=abc123,...')."""
    if not hashes_str:
        return ''
    match = re.search(r'SHA256=([A-Fa-f0-9]+)', hashes_str)
    return match.group(1) if match else ''


def _safe_int(val):
    """Safely convert a value to int, defaulting to 0."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def read_evtx_file(filepath):
    """
    Read events from a .evtx file using python-evtx library.
    Returns list of normalized event dicts.
    """
    try:
        import Evtx.Evtx as evtx
        import Evtx.Views as views

        events = []
        with evtx.Evtx(filepath) as log:
            for record in log.records():
                try:
                    xml_str = record.xml()
                    root = ET.fromstring(xml_str)

                    system = root.find(f'{NS}System')
                    if system is None:
                        continue

                    event_id_el = system.find(f'{NS}EventID')
                    event_id = event_id_el.text if event_id_el is not None else ''

                    channel_el = system.find(f'{NS}Channel')
                    channel = channel_el.text if channel_el is not None else ''

                    parsed = _parse_event_xml(root, channel)
                    if parsed:
                        events.append(parsed)

                except Exception:
                    continue

        return events

    except ImportError:
        return []
    except Exception:
        return []
