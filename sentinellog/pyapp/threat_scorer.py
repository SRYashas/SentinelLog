"""
SentinelLog — Threat Scoring Engine
=====================================
Pattern-based risk scoring for process creation events and PowerShell scripts.
Evaluates command lines and script blocks against detection rules stored in SQLite.
"""

import re
from . import db


def score_event(event_dict):
    """
    Evaluate a single event against all enabled threat rules.

    Args:
        event_dict: Normalized event dictionary with command_line, script_block_text, etc.

    Returns:
        Updated event_dict with 'risk_level' and 'risk_reasons' fields set.
    """
    rules = db.get_threat_rules()
    matched_reasons = []
    highest_level = 'info'

    command_line = event_dict.get('command_line', '')
    script_text = event_dict.get('script_block_text', '')

    for rule in rules:
        pattern = rule.get('pattern', '')
        target_field = rule.get('target_field', 'command_line')
        pattern_type = rule.get('pattern_type', 'regex')
        rule_level = rule.get('risk_level', 'suspicious')

        # Select the text to evaluate
        if target_field == 'script_block_text':
            target_text = script_text
        else:
            target_text = command_line

        if not target_text:
            continue

        matched = False

        if pattern_type == 'regex':
            try:
                if re.search(pattern, target_text):
                    matched = True
            except re.error:
                continue
        elif pattern_type == 'substring':
            if pattern.lower() in target_text.lower():
                matched = True
        elif pattern_type == 'exact':
            if pattern == target_text:
                matched = True

        if matched:
            matched_reasons.append(rule.get('name', 'Unknown Rule'))
            # Escalate risk level
            if rule_level == 'high':
                highest_level = 'high'
            elif rule_level == 'suspicious' and highest_level != 'high':
                highest_level = 'suspicious'

    # Additional heuristic: unresolved origin + non-interactive = suspicious
    if (not event_dict.get('origin_resolved', False) and
            event_dict.get('origin_source', 'unknown') == 'unknown' and
            event_dict.get('event_type') == 'process_create'):
        parent = event_dict.get('parent_process_name', '').lower()
        if parent and parent not in ('explorer.exe', 'cmd.exe', 'powershell.exe', 'pwsh.exe', 'windowsterminal.exe'):
            if highest_level == 'info':
                highest_level = 'suspicious'
            matched_reasons.append('Unresolved origin with non-interactive parent')

    event_dict['risk_level'] = highest_level
    event_dict['risk_reasons'] = matched_reasons
    return event_dict


def score_events_batch(events_list):
    """Score a list of events. Returns the list with risk fields populated."""
    return [score_event(e) for e in events_list]


def resolve_origin(event_dict):
    """
    Attempt to resolve the origin/trigger of a process creation event.
    Cross-references registry Run keys, startup folders, scheduled tasks, and services.

    Args:
        event_dict: Normalized event dictionary.

    Returns:
        Updated event_dict with origin_resolved, origin_source, origin_detail fields.
    """
    import subprocess
    import os

    process_name = event_dict.get('process_name', '').lower()
    command_line = event_dict.get('command_line', '')
    parent_name = event_dict.get('parent_process_name', '').lower()

    # Check 1: Interactive parent (explorer.exe, terminal, shell)
    interactive_parents = {'explorer.exe', 'cmd.exe', 'powershell.exe', 'pwsh.exe',
                           'windowsterminal.exe', 'conhost.exe', 'code.exe'}
    if parent_name in interactive_parents:
        event_dict['origin_resolved'] = True
        event_dict['origin_source'] = 'user_interactive'
        event_dict['origin_detail'] = f'Spawned by interactive parent: {parent_name}'
        return event_dict

    # Check 2: Registry Run keys
    run_keys = [
        r'HKCU\Software\Microsoft\Windows\CurrentVersion\Run',
        r'HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce',
        r'HKLM\Software\Microsoft\Windows\CurrentVersion\Run',
        r'HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    ]

    for key_path in run_keys:
        try:
            result = subprocess.run(
                ['reg', 'query', key_path],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0 and process_name in result.stdout.lower():
                event_dict['origin_resolved'] = True
                event_dict['origin_source'] = 'registry_run'
                event_dict['origin_detail'] = f'Matched in {key_path}'
                return event_dict
        except Exception:
            continue

    # Check 3: Scheduled Tasks
    try:
        result = subprocess.run(
            ['schtasks', '/query', '/fo', 'CSV', '/v'],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0 and process_name in result.stdout.lower():
            event_dict['origin_resolved'] = True
            event_dict['origin_source'] = 'scheduled_task'
            event_dict['origin_detail'] = f'Process "{process_name}" found in scheduled tasks'
            return event_dict
    except Exception:
        pass

    # Check 4: Windows Services
    try:
        result = subprocess.run(
            ['sc', 'query', 'state=', 'all'],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0 and process_name.replace('.exe', '') in result.stdout.lower():
            event_dict['origin_resolved'] = True
            event_dict['origin_source'] = 'service'
            event_dict['origin_detail'] = f'Process matches a registered Windows service'
            return event_dict
    except Exception:
        pass

    # Check 5: Startup folder
    startup_dirs = [
        os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup'),
        os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup'),
    ]
    for startup_dir in startup_dirs:
        if os.path.isdir(startup_dir):
            for item in os.listdir(startup_dir):
                if process_name.replace('.exe', '') in item.lower():
                    event_dict['origin_resolved'] = True
                    event_dict['origin_source'] = 'startup_folder'
                    event_dict['origin_detail'] = f'Matched shortcut in {startup_dir}'
                    return event_dict

    # Unresolved
    event_dict['origin_resolved'] = False
    event_dict['origin_source'] = 'unknown'
    event_dict['origin_detail'] = 'No registry, task, service, or startup folder match found'
    return event_dict
