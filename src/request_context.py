"""
Request context management for distributed tracing across async operations.
Uses contextvars to maintain request/session state without manual parameter passing.
"""
import contextvars
import uuid
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

# Context variables for request tracing
session_id_ctx = contextvars.ContextVar("session_id", default=None)
request_id_ctx = contextvars.ContextVar("request_id", default=None)
request_metadata_ctx = contextvars.ContextVar("request_metadata", default=None)

@dataclass
class RequestMetadata:
    """Metadata about the current request for tracing purposes"""
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    method: Optional[str] = None
    path: Optional[str] = None
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None
    transport_type: Optional[str] = None  # 'sse', 'stdio', 'http'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "start_time": self.start_time,
            "method": self.method,
            "path": self.path,
            "user_agent": self.user_agent,
            "client_ip": self.client_ip,
            "transport_type": self.transport_type,
            "duration_ms": (time.time() - self.start_time) * 1000
        }

def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())[:8]  # Short UUID for readability

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def set_session_id(session_id: str) -> None:
    """Set the session ID for the current context"""
    session_id_ctx.set(session_id)

def get_session_id() -> Optional[str]:
    """Get the session ID for the current context"""
    return session_id_ctx.get()

def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context"""
    request_id_ctx.set(request_id)

def get_request_id() -> Optional[str]:
    """Get the request ID for the current context"""
    return request_id_ctx.get()

def set_request_metadata(metadata: RequestMetadata) -> None:
    """Set request metadata for the current context"""
    request_metadata_ctx.set(metadata)
    # Also set individual context vars for easier access
    if metadata.session_id:
        set_session_id(metadata.session_id)
    if metadata.request_id:
        set_request_id(metadata.request_id)

def get_request_metadata() -> Optional[RequestMetadata]:
    """Get request metadata for the current context"""
    return request_metadata_ctx.get()

def ensure_request_context() -> RequestMetadata:
    """
    Ensure we have request context, creating minimal context if none exists.
    Useful for operations that might be called outside of a request context.
    """
    metadata = get_request_metadata()
    if metadata is None:
        # Create minimal context with generated IDs
        metadata = RequestMetadata(
            session_id=generate_session_id(),
            request_id=generate_request_id(),
            transport_type="internal"
        )
        set_request_metadata(metadata)
    return metadata

def get_trace_info() -> Dict[str, Any]:
    """
    Get current trace information as a dictionary.
    Returns empty dict if no context is set.
    """
    metadata = get_request_metadata()
    if metadata:
        return metadata.to_dict()
    
    # Fallback to individual context vars if metadata is not set
    session_id = get_session_id()
    request_id = get_request_id()
    
    if session_id or request_id:
        return {
            "session_id": session_id,
            "request_id": request_id
        }
    
    return {}

def with_new_request_context(session_id: Optional[str] = None, **kwargs) -> RequestMetadata:
    """
    Create a new request context with optional session ID.
    If no session_id is provided, generates one.
    Additional kwargs are passed to RequestMetadata.
    """
    if session_id is None:
        session_id = generate_session_id()
    
    metadata = RequestMetadata(
        session_id=session_id,
        request_id=generate_request_id(),
        **kwargs
    )
    set_request_metadata(metadata)
    return metadata
