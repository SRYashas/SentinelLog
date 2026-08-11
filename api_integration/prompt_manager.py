"""Prompt management for LLM interactions."""

import json
import logging
from typing import Any, Dict, List, Optional

from .exceptions import PromptError

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages all prompts for LLM interactions.
    
    Centralizes prompt templates and context building logic
    to keep the LLM client clean and allow easy prompt engineering.
    """
    
    SYSTEM_PROMPT = """You are an expert cybersecurity incident responder and threat analyst specializing in Windows Event Log analysis. Your role is to analyze security events, identify threats, and provide actionable remediation guidance.

When analyzing threats, you must structure your response in exactly four sections:

## WHAT HAPPENED
A clear, concise summary of the detected threat activity based on the event logs provided. Explain the attack technique, the actors involved (if identifiable), and the sequence of events.

## HOW IT WORKS
Technical deep-dive into the attack mechanism. Explain the specific Windows APIs, commands, or techniques used. Reference MITRE ATT&CK techniques (T-numbers) where applicable. Include relevant Event IDs and their significance.

## WHY IT MATTERS
Business impact assessment. Explain the risk level, potential data loss, system compromise implications, lateral movement potential, and regulatory/compliance concerns. Connect to the provided threat score.

## REMEDIATION STEPS
Prioritized, actionable remediation steps:
1. **Immediate Containment** - Steps to stop the attack right now
2. **Investigation** - What to check, logs to review, IOCs to hunt
3. **Eradication** - How to remove the threat completely
4. **Recovery** - System restoration and validation steps
5. **Prevention** - Long-term hardening and detection improvements

Be specific. Reference actual Windows tools (PowerShell, Event Viewer, Sysmon, Defender, etc.). Avoid generic advice. If the logs don't support a conclusion, state what additional data would be needed."""

    THREAT_ANALYSIS_TEMPLATE = """Analyze the following Windows Event Log data and provide a structured threat analysis.

**Threat Score:** {threat_score}/100 (Local Heuristic Assessment)

**Event Log Data:**
```json
{log_data}
```

Provide your analysis in the four required sections: WHAT HAPPENED, HOW IT WORKS, WHY IT MATTERS, REMEDIATION STEPS."""

    def __init__(self):
        self._system_prompt = self.SYSTEM_PROMPT
        self._custom_context: Dict[str, Any] = {}
    
    def set_system_prompt(self, prompt: str) -> None:
        """Override the default system prompt."""
        self._system_prompt = prompt
        logger.info("System prompt updated")
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        return self._system_prompt
    
    def add_context(self, key: str, value: Any) -> None:
        """Add custom context that will be included in prompts."""
        self._custom_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get custom context value."""
        return self._custom_context.get(key, default)
    
    def build_threat_analysis_messages(
        self,
        log_data: Dict[str, Any],
        threat_score: float,
    ) -> List[Dict[str, str]]:
        """
        Build the message list for threat analysis.
        
        Args:
            log_data: Raw event log data (will be JSON serialized).
            threat_score: Local heuristic threat score (0-100).
            
        Returns:
            List of message dicts for the chat API.
            
        Raises:
            PromptError: If log data cannot be serialized.
        """
        try:
            # Sanitize and format log data
            formatted_logs = self._format_log_data(log_data)
            
            user_content = self.THREAT_ANALYSIS_TEMPLATE.format(
                threat_score=round(threat_score, 1),
                log_data=formatted_logs,
            )
            
            return [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_content},
            ]
        except Exception as e:
            logger.error(f"Failed to build threat analysis messages: {e}")
            raise PromptError("Failed to build analysis prompt", str(e))
    
    def _format_log_data(self, log_data: Dict[str, Any]) -> str:
        """Format log data for inclusion in prompt."""
        # Create a sanitized copy to avoid circular references
        sanitized = self._sanitize_for_json(log_data)
        
        # Pretty print with indentation
        return json.dumps(sanitized, indent=2, default=str)
    
    def _sanitize_for_json(self, obj: Any, max_depth: int = 10, _depth: int = 0) -> Any:
        """Recursively sanitize object for JSON serialization."""
        if _depth > max_depth:
            return "<max_depth_exceeded>"
        
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item, max_depth, _depth + 1) for item in obj]
        
        if isinstance(obj, dict):
            return {
                str(k): self._sanitize_for_json(v, max_depth, _depth + 1)
                for k, v in obj.items()
            }
        
        # For other objects, try to get a string representation
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"
    
    def build_followup_messages(
        self,
        previous_messages: List[Dict[str, str]],
        followup_question: str,
    ) -> List[Dict[str, str]]:
        """
        Build messages for a follow-up question in an existing conversation.
        
        Args:
            previous_messages: Previous conversation messages.
            followup_question: The follow-up question from the user.
            
        Returns:
            Extended message list.
        """
        return previous_messages + [
            {"role": "user", "content": followup_question}
        ]
    
    def build_summary_prompt(self, analysis_text: str) -> List[Dict[str, str]]:
        """
        Build a prompt to summarize a previous analysis.
        
        Args:
            analysis_text: The full analysis text to summarize.
            
        Returns:
            Message list for summarization.
        """
        return [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": (
                    "Summarize the following threat analysis in 3-4 concise bullet points "
                    "focusing on the key findings and top priority remediation actions:\n\n"
                    f"{analysis_text}"
                ),
            },
        ]