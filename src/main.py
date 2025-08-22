"""
Main ASGI application for Hello World MCP Server with request tracing.
Demonstrates how to set up FastMCP with contextvars-based tracing.
"""
# Import logging configuration first to set up tracing
from . import logging_config

import os
import logging
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport

from .hello_mcp_server import create_hello_mcp_server
from .tracing_middleware import RequestTracingMiddleware
from .request_context import get_request_id, get_session_id

logger = logging.getLogger(__name__)

# Create the MCP server
mcp_server = create_hello_mcp_server()

# Create SSE transport for MCP communication
sse_transport = SseServerTransport("/messages/")

async def handle_sse(request):
    """Handle SSE connections for MCP communication"""
    logger.info("New SSE connection established")
    
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        # Run the MCP server
        await mcp_server.run(
            streams[0], streams[1], 
            mcp_server.create_initialization_options()
        )

async def homepage(request):
    """Simple homepage with server info and tracing demonstration"""
    req_id = get_request_id()
    session_id = get_session_id()
    
    logger.info("Homepage accessed")
    
    return JSONResponse({
        "message": "Hello World MCP Server with Request Tracing! 🚀",
        "trace_info": {
            "request_id": req_id,
            "session_id": session_id[:8] if session_id else None
        },
        "endpoints": {
            "sse": "/sse - MCP Server-Sent Events endpoint",
            "messages": "/messages/ - MCP message handling",
            "health": "/health - Health check",
            "ping": "/ping - Simple ping endpoint"
        },
        "tools": [
            "hello - Say hello with personalized greeting",
            "add_numbers - Add two numbers together",
            "slow_operation - Simulate slow async operation",
            "parallel_tasks - Demonstrate parallel async tasks"
        ]
    })

async def health_check(request):
    """Health check endpoint"""
    logger.info("Health check requested")
    
    return JSONResponse({
        "status": "healthy",
        "server": "hello-world-mcp-server",
        "tracing": "enabled",
        "request_id": get_request_id(),
        "session_id": get_session_id()[:8] if get_session_id() else None
    })

async def ping(request):
    """Simple ping endpoint to test tracing"""
    logger.info("Ping endpoint called")
    
    return PlainTextResponse(
        f"Pong! 🏓 [req={get_request_id()}|session={get_session_id()[:8] if get_session_id() else 'none'}]"
    )

async def demo_async_operations(request):
    """Demonstrate how tracing works across async operations"""
    import asyncio
    
    logger.info("Starting async operations demo")
    
    # These functions will automatically inherit the trace context
    async def task_1():
        logger.info("Task 1 started")
        await asyncio.sleep(0.1)
        logger.info("Task 1 completed")
        return "Task 1 result"
    
    async def task_2():
        logger.info("Task 2 started")
        await asyncio.sleep(0.2)
        logger.info("Task 2 completed")
        return "Task 2 result"
    
    async def task_3():
        logger.info("Task 3 started")
        await asyncio.sleep(0.15)
        logger.info("Task 3 completed")
        return "Task 3 result"
    
    # Run tasks in parallel - all will have the same trace context
    results = await asyncio.gather(task_1(), task_2(), task_3())
    
    logger.info(f"All async tasks completed: {results}")
    
    return JSONResponse({
        "message": "Async operations demo completed",
        "results": results,
        "trace_info": {
            "request_id": get_request_id(),
            "session_id": get_session_id()[:8] if get_session_id() else None
        },
        "note": "Check the logs to see how all async operations share the same trace context!"
    })

# Create the Starlette application with tracing middleware
app = Starlette(
    debug=True,
    routes=[
        Route("/", endpoint=homepage),
        Route("/health", endpoint=health_check),
        Route("/ping", endpoint=ping),
        Route("/demo-async", endpoint=demo_async_operations),
        Route("/sse", endpoint=handle_sse),
        # Mount the SSE message handling
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
    middleware=[
        # CORS middleware for web clients
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"], 
            allow_headers=["*"]
        ),
        # Request tracing middleware - this is the magic! ✨
        Middleware(RequestTracingMiddleware),
    ]
)

def main():
    """Main entry point for the application"""
    import uvicorn
    
    port = int(os.getenv("PORT", "8081"))
    
    print("🚀 Starting Hello World MCP Server with Request Tracing")
    print(f"📡 Server will be available at: http://localhost:{port}")
    print("🔍 Available endpoints:")
    print(f"  - Homepage: http://localhost:{port}/")
    print(f"  - Health: http://localhost:{port}/health")
    print(f"  - Ping: http://localhost:{port}/ping")
    print(f"  - Async Demo: http://localhost:{port}/demo-async")
    print(f"  - MCP SSE: http://localhost:{port}/sse")
    print()
    print("💡 Tips:")
    print("  - Watch the logs to see request tracing in action!")
    print("  - Try making multiple concurrent requests to see isolated contexts")
    print("  - Use the /demo-async endpoint to see async operation tracing")
    print("  - Set LOG_LEVEL=DEBUG for more detailed tracing logs")
    print()
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
