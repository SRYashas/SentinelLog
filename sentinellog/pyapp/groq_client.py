"""
SentinelLog — Groq API Client
==============================
Async client for Groq API (Llama 3) with streaming support.
Handles context injection for log analysis with structured prompt engineering.
"""

import json
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    AsyncGroq = None

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class LogContext:
    """Structured log data for AI analysis."""
    event_id: int
    timestamp: str
    event_type: str
    process_name: str
    pid: int
    parent_process_name: str
    parent_pid: int
    user_account: str
    command_line: str
    script_block_text: str
    hash_sha256: str
    risk_level: str
    risk_reasons: List[str]
    origin_resolved: bool
    origin_source: str
    origin_detail: str


class GroqClient:
    """
    Async Groq API client with streaming chat completion.
    Injects log context into system prompt for structured analysis.
    """

    MODEL = "llama3-70b-8192"  # Llama 3 70B on Groq
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3

    def __init__(self, api_key: str):
        if not GROQ_AVAILABLE:
            raise RuntimeError("groq package not installed. Run: pip install groq")

        self.client = AsyncGroq(api_key=api_key)
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt with strict formatting requirements."""
        return """You are SentinelLog AI Assistant, a cybersecurity expert specializing in Windows event log analysis and threat hunting.

When analyzing a log event, you MUST structure your response into EXACTLY FOUR sections with these headers:

## What & Where
Briefly explain what the command/process is and where it executed (system context, user, parent process).

## How
Explain the technical mechanism of how this action was performed. Detail the specific Windows APIs, COM objects, WMI classes, or script engines involved.

## Why (Threat Context)
Explain why an attacker or malware would use this specific technique. Reference MITRE ATT&CK tactics/techniques where applicable (e.g., T1059.001 PowerShell, T1053.005 Scheduled Task).

## Potential Fixes & Remediation
Provide exact, copy-pasteable CMD/PowerShell commands or GUI steps to mitigate the threat. Include detection rules (Sigma/Elastic) where relevant.

FORMATTING RULES:
- Use Markdown for formatting
- Code blocks MUST specify language (powershell, cmd, yaml, json)
- Be concise but technically precise
- Never omit the four section headers
- If information is unavailable, state "Not available in provided context"

You are analyzing Windows Event Logs (Sysmon Event ID 1, 4104, etc.). The user will provide structured log data."""

    def _build_user_prompt(self, context: LogContext) -> str:
        """Build the user prompt with the specific log event data."""
        risk_color = {
            'high': '🔴 CRITICAL/HIGH',
            'suspicious': '🟠 SUSPICIOUS',
            'info': '🟢 INFO'
        }.get(context.risk_level.lower(), '⚪ UNKNOWN')

        return f"""Analyze the following Windows event log entry:

**Event ID:** {context.event_id}
**Timestamp:** {context.timestamp}
**Event Type:** {context.event_type}
**Risk Level:** {risk_color} ({context.risk_level.upper()})
**Risk Reasons:** {', '.join(context.risk_reasons) if context.risk_reasons else 'None'}

**Process:** {context.process_name} (PID: {context.pid})
**Parent Process:** {context.parent_process_name} (PID: {context.parent_pid})
**User Context:** {context.user_account}
**Origin Resolved:** {'Yes - ' + context.origin_source if context.origin_resolved else 'No - ' + context.origin_detail}

**SHA256:** {context.hash_sha256 if context.hash_sha256 else 'N/A'}

**Command Line:**
```
{context.command_line if context.command_line else 'N/A'}
```

**Script Block Content (PowerShell Event ID 4104):**
```
{context.script_block_text if context.script_block_text else 'N/A'}
```

Provide your structured analysis in the four required sections."""

    async def validate_api_key(self) -> tuple[bool, str]:
        """
        Validate the API key by making a minimal test request.
        Returns (success, message).
        """
        try:
            # Minimal completion request to verify key
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=5,
                temperature=0,
            )
            return True, "API key validated successfully"
        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
                return False, "Invalid API key: authentication failed"
            elif "rate_limit" in error_msg.lower() or "429" in error_msg:
                return False, "Rate limited: too many requests"
            return False, f"Validation error: {error_msg}"

    async def stream_chat(
        self,
        context: LogContext,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion for a log analysis request.
        Yields text chunks as they arrive.
        """
        messages = [{"role": "system", "content": self._system_prompt}]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current log analysis request
        messages.append({"role": "user", "content": self._build_user_prompt(context)})

        try:
            stream = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n\n❌ **Error:** {str(e)}"

    async def stream_followup(
        self,
        followup_question: str,
        conversation_history: List[Dict[str, str]],
        original_context: Optional[LogContext] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a follow-up response in an ongoing conversation.
        """
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": followup_question})

        try:
            stream = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n\n❌ **Error:** {str(e)}"


def create_log_context_from_event(event_dict: Dict[str, Any]) -> LogContext:
    """Convert a database event dict to LogContext."""
    return LogContext(
        event_id=event_dict.get('id', 0),
        timestamp=event_dict.get('timestamp', ''),
        event_type=event_dict.get('event_type', ''),
        process_name=event_dict.get('process_name', ''),
        pid=event_dict.get('pid', 0),
        parent_process_name=event_dict.get('parent_process_name', ''),
        parent_pid=event_dict.get('parent_pid', 0),
        user_account=event_dict.get('user_account', ''),
        command_line=event_dict.get('command_line', ''),
        script_block_text=event_dict.get('script_block_text', ''),
        hash_sha256=event_dict.get('hash_sha256', ''),
        risk_level=event_dict.get('risk_level', 'info'),
        risk_reasons=event_dict.get('risk_reasons', []),
        origin_resolved=event_dict.get('origin_resolved', False),
        origin_source=event_dict.get('origin_source', 'unknown'),
        origin_detail=event_dict.get('origin_detail', ''),
    )