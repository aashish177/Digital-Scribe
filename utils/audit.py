"""
Audit logging system for pipeline execution tracking.

Provides detailed execution history for debugging and transparency.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field


@dataclass
class AuditEvent:
    """Single audit event."""
    timestamp: str
    agent: str
    action: str  # 'start', 'complete', 'error'
    duration: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Track and log pipeline execution for audit trails."""
    
    def __init__(self, request_id: str, content_request: str):
        """
        Initialize audit logger.
        
        Args:
            request_id: Unique request ID
            content_request: Original content request
        """
        self.request_id = request_id
        self.content_request = content_request
        self.events: List[AuditEvent] = []
        self.started_at = datetime.now().isoformat()
        self.settings: Dict[str, Any] = {}
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set request settings."""
        self.settings = settings or {}
    
    def log_event(
        self,
        agent: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None
    ):
        """
        Log a pipeline event.
        
        Args:
            agent: Agent name
            action: Action type ('start', 'complete', 'error')
            data: Event data
            duration: Duration in seconds (for complete events)
        """
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            action=action,
            duration=duration,
            data=data or {}
        )
        self.events.append(event)
    
    def log_agent_start(self, agent: str):
        """Log agent start."""
        self.log_event(agent, 'start')
    
    def log_agent_complete(
        self,
        agent: str,
        output: Any,
        duration: float,
        tokens_used: Optional[int] = None
    ):
        """
        Log agent completion.
        
        Args:
            agent: Agent name
            output: Agent output (will be truncated for logging)
            duration: Execution duration in seconds
            tokens_used: Number of tokens used
        """
        # Truncate output for logging
        output_preview = self._truncate_output(output)
        
        data = {
            'output_preview': output_preview,
            'tokens_used': tokens_used
        }
        
        self.log_event(agent, 'complete', data, duration)
    
    def log_agent_error(self, agent: str, error: str, duration: float):
        """
        Log agent error.
        
        Args:
            agent: Agent name
            error: Error message
            duration: Duration before error
        """
        self.log_event(
            agent,
            'error',
            {'error': error},
            duration
        )
    
    def log_retrieval(self, agent: str, query: str, doc_count: int, scores: List[float]):
        """
        Log document retrieval.
        
        Args:
            agent: Agent name
            query: Search query
            doc_count: Number of documents retrieved
            scores: Relevance scores
        """
        self.log_event(
            agent,
            'retrieval',
            {
                'query': query[:200],  # Truncate query
                'doc_count': doc_count,
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'max_score': max(scores) if scores else 0
            }
        )
    
    def generate_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate execution summary.
        
        Args:
            result: Final pipeline result
            
        Returns:
            Summary dictionary
        """
        execution_times = result.get('execution_times', {})
        total_time = sum(execution_times.values())
        
        # Count events by type
        event_counts = {}
        for event in self.events:
            key = f"{event.agent}_{event.action}"
            event_counts[key] = event_counts.get(key, 0) + 1
        
        # Calculate token usage
        total_tokens = sum(
            event.data.get('tokens_used', 0)
            for event in self.events
            if event.data.get('tokens_used')
        )
        
        return {
            'request_id': self.request_id,
            'total_execution_time': round(total_time, 2),
            'total_events': len(self.events),
            'event_counts': event_counts,
            'total_tokens': total_tokens,
            'agents_executed': len(execution_times),
            'success': len(result.get('errors', [])) == 0
        }
    
    def save_audit_log(
        self,
        output_path: Path,
        result: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save complete audit log to file.
        
        Args:
            output_path: Path to save audit log
            result: Final pipeline result (optional)
            
        Returns:
            Path to created file
        """
        audit_data = {
            'request_id': self.request_id,
            'content_request': self.content_request,
            'settings': self.settings,
            'started_at': self.started_at,
            'completed_at': datetime.now().isoformat(),
            'events': [
                {
                    'timestamp': event.timestamp,
                    'agent': event.agent,
                    'action': event.action,
                    'duration': event.duration,
                    'data': event.data
                }
                for event in self.events
            ]
        }
        
        # Add summary if result provided
        if result:
            audit_data['summary'] = self.generate_summary(result)
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(audit_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        return output_path
    
    def save_execution_summary(self, output_path: Path, result: Dict[str, Any]) -> Path:
        """
        Save concise execution summary.
        
        Args:
            output_path: Path to save summary
            result: Pipeline result
            
        Returns:
            Path to created file
        """
        summary = self.generate_summary(result)
        
        # Add additional metrics
        summary.update({
            'word_count': len(result.get('final_content', '').split()),
            'execution_times': result.get('execution_times', {}),
            'errors': result.get('errors', [])
        })
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        return output_path
    
    def _truncate_output(self, output: Any, max_length: int = 500) -> str:
        """Truncate output for logging."""
        output_str = str(output)
        if len(output_str) > max_length:
            return output_str[:max_length] + '...'
        return output_str
