"""
ASGI middleware for request tracing and session management.
Extracts session/correlation IDs from various sources and sets up request context.
"""
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.request_context import (
    RequestMetadata, 
    set_request_metadata, 
    generate_session_id, 
    generate_request_id,
    get_trace_info
)

logger = logging.getLogger(__name__)

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts and sets up request tracing context.
    
    Looks for session/correlation IDs in:
    1. X-Session-ID header
    2. X-Correlation-ID header  
    3. session_id query parameter
    4. Authorization header (for long-lived SSE connections)
    
    If no session ID is found, generates a new one.
    Always generates a unique request ID for each request.
    """
    
    def __init__(self, app, session_header: str = "X-Session-ID", 
                 correlation_header: str = "X-Correlation-ID"):
        super().__init__(app)
        self.session_header = session_header
        self.correlation_header = correlation_header
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract session ID from various sources
        session_id = self._extract_session_id(request)
        
        # Always generate a unique request ID
        request_id = generate_request_id()
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        
        # Determine transport type based on path and content
        transport_type = self._determine_transport_type(request)
        
        # Create request metadata
        metadata = RequestMetadata(
            session_id=session_id,
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            user_agent=user_agent,
            client_ip=client_ip,
            transport_type=transport_type
        )
        
        # Set the context for this request
        set_request_metadata(metadata)
        
        # Log the start of the request
        logger.info(f"Request started: {request.method} {request.url.path}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add tracing headers to response
            response.headers["X-Request-ID"] = request_id
            if session_id:
                response.headers["X-Session-ID"] = session_id
                
            # Log successful completion
            trace_info = get_trace_info()
            duration_ms = trace_info.get('duration_ms', 0)
            logger.info(f"Request completed: {response.status_code} in {duration_ms:.1f}ms")
            
            return response
            
        except Exception as e:
            # Log error with trace context
            trace_info = get_trace_info()
            duration_ms = trace_info.get('duration_ms', 0)
            logger.error(f"Request failed after {duration_ms:.1f}ms: {str(e)}", exc_info=True)
            raise
    
    def _extract_session_id(self, request: Request) -> str:
        """
        Extract session ID from request, generating one if not found.
        
        Priority order:
        1. X-Session-ID header
        2. X-Correlation-ID header
        3. session_id query parameter
        4. Extract from Authorization Bearer token (for SSE)
        5. Generate new session ID
        """
        # Check headers first
        session_id = request.headers.get(self.session_header.lower())
        if session_id:
            logger.debug(f"Session ID from {self.session_header} header: {session_id[:8]}...")
            return session_id
        
        # Check correlation ID header
        session_id = request.headers.get(self.correlation_header.lower())
        if session_id:
            logger.debug(f"Session ID from {self.correlation_header} header: {session_id[:8]}...")
            return session_id
        
        # Check query parameters
        session_id = request.query_params.get("session_id")
        if session_id:
            logger.debug(f"Session ID from query param: {session_id[:8]}...")
            return session_id
        
        # For SSE connections, try to extract from auth token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # For development, the token might be used as session ID
            # In production, you'd decode the JWT and extract user/session info
            if len(token) > 8:  # Basic validation
                logger.debug(f"Session ID from Bearer token: {token[:8]}...")
                return token
        
        # Generate new session ID if none found
        new_session_id = generate_session_id()
        logger.debug(f"Generated new session ID: {new_session_id[:8]}...")
        return new_session_id
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address considering proxies"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client address from connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    def _determine_transport_type(self, request: Request) -> str:
        """Determine the type of transport/connection based on request"""
        path = request.url.path
        
        # SSE endpoints
        if "/sse" in path or "/messages/" in path:
            return "sse"
        
        # Health and utility endpoints
        if path in ["/health", "/", "/ping"]:
            return "http"
        
        # MCP-related endpoints
        if "/mcp/" in path:
            return "mcp_sse"
        
        # Default
        return "http"

class MCPRequestTracingMiddleware:
    """
    Special middleware for MCP server operations that don't go through HTTP.
    This is used to ensure MCP operations (like tool calls) have tracing context.
    """
    
    @staticmethod
    def ensure_context_for_operation(operation_name: str, session_id: Optional[str] = None):
        """
        Ensure we have request context for MCP operations.
        Used in MCP server handlers to maintain tracing.
        """
        from src.request_context import get_request_metadata, with_new_request_context
        
        # If we already have context, use it
        existing_metadata = get_request_metadata()
        if existing_metadata:
            logger.debug(f"Using existing context for {operation_name}")
            return existing_metadata
        
        # Create new context for this operation
        logger.debug(f"Creating new context for {operation_name}")
        metadata = with_new_request_context(
            session_id=session_id,
            method="MCP",
            path=f"/mcp/{operation_name}",
            transport_type="mcp"
        )
        
        logger.info(f"MCP operation started: {operation_name}")
        
        return metadata
