"""
Centralized logging configuration with request tracing support.
Automatically adds session_id and request_id to all log records.
"""
import logging
import os

# Enhanced log format with tracing information
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [req=%(request_id)s|session=%(session_id)s] - %(message)s'
# Fallback format when no tracing context is available
FALLBACK_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log levels mapping
LOG_LEVEL_MAPPING = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class RequestTracingFilter(logging.Filter):
    """
    Logging filter that adds request tracing information to log records.
    Injects session_id and request_id from context variables into each log record.
    """
    
    def filter(self, record):
        """Add tracing information to the log record"""
        try:
            from src.request_context import get_session_id, get_request_id
            
            # Get current context values
            session_id = get_session_id()
            request_id = get_request_id()
            
            # Add to record, using fallback values if not available
            record.session_id = session_id[:8] if session_id else "none"
            record.request_id = request_id if request_id else "none"
            
        except (ImportError, Exception):
            # Fallback if context module isn't available or there's an error
            record.session_id = "none"
            record.request_id = "none"
        
        return True

class ConditionalFormatter(logging.Formatter):
    """
    Formatter that uses different formats based on whether tracing info is available.
    Falls back to simpler format when session/request IDs are 'none'.
    """
    
    def __init__(self):
        super().__init__()
        self.traced_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        self.fallback_formatter = logging.Formatter(FALLBACK_LOG_FORMAT, DATE_FORMAT)
    
    def format(self, record):
        # Use enhanced format if we have real tracing info
        if (hasattr(record, 'session_id') and hasattr(record, 'request_id') and 
            record.session_id != "none" and record.request_id != "none"):
            return self.traced_formatter.format(record)
        else:
            return self.fallback_formatter.format(record)

def get_log_level(level: str = None):
    """Get the log level from argument or environment variable."""
    if level is not None:
        log_level_str = str(level).upper()
    else:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return LOG_LEVEL_MAPPING.get(log_level_str, logging.INFO)

def configure_logging(level: str = None):
    """
    Configure logging for the application with request tracing support.
    """
    # Get log level
    log_level = get_log_level(level)
    
    # Create trace-aware formatter and filter
    formatter = ConditionalFormatter()
    trace_filter = RequestTracingFilter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with trace formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(trace_filter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("src").setLevel(log_level)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("starlette").setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")

# Auto-configure logging when this module is imported
configure_logging()
