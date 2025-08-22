"""
Hello World MCP Server with request tracing demonstration.
Shows how contextvars automatically propagate trace information across async operations.
"""
import logging
import asyncio
from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import TextContent, Tool

from .tracing_middleware import MCPRequestTracingMiddleware
from .request_context import get_request_id, get_session_id

logger = logging.getLogger(__name__)

def create_hello_mcp_server() -> Server:
    """
    Create a simple MCP server with several tools to demonstrate tracing.
    """
    app = Server("hello-world-mcp-server")
    
    @app.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available tools - demonstrates tracing in tool listing"""
        MCPRequestTracingMiddleware.ensure_context_for_operation("list_tools")
        logger.info("Client requested list of available tools")
        
        tools = [
            Tool(
                name="hello",
                description="Say hello with a personalized greeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string", 
                            "description": "Name to greet"
                        }
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="add_numbers",
                description="Add two numbers together",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            ),
            Tool(
                name="slow_operation",
                description="Simulates a slow operation with multiple async steps",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "number", 
                            "description": "Number of steps to execute",
                            "default": 3
                        }
                    }
                }
            ),
            Tool(
                name="parallel_tasks",
                description="Demonstrates parallel async operations with shared context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_count": {
                            "type": "number",
                            "description": "Number of parallel tasks to run",
                            "default": 3
                        }
                    }
                }
            )
        ]
        
        logger.info(f"Returning {len(tools)} available tools")
        return tools
    
    @app.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls - demonstrates tracing across different tool implementations"""
        MCPRequestTracingMiddleware.ensure_context_for_operation("call_tool")
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        try:
            if name == "hello":
                result = await handle_hello_tool(arguments)
            elif name == "add_numbers":
                result = await handle_add_numbers_tool(arguments)
            elif name == "slow_operation":
                result = await handle_slow_operation_tool(arguments)
            elif name == "parallel_tasks":
                result = await handle_parallel_tasks_tool(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            logger.info(f"Tool {name} completed successfully")
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}", exc_info=True)
            error_msg = f"Tool '{name}' failed: {str(e)}"
            return [TextContent(type="text", text=error_msg)]
    
    return app

# Tool implementations - notice how they don't need to handle tracing manually!

async def handle_hello_tool(arguments: Dict[str, Any]) -> str:
    """Simple hello tool - shows basic tracing"""
    name = arguments.get("name", "World")
    logger.info(f"Generating greeting for: {name}")
    
    # Simulate some async work
    await asyncio.sleep(0.1)
    
    greeting = f"Hello, {name}! 👋"
    
    # The request_id and session_id are automatically available!
    req_id = get_request_id()
    session_id = get_session_id()
    
    logger.info(f"Generated greeting: {greeting}")
    logger.debug(f"Context info - Request: {req_id}, Session: {session_id[:8] if session_id else 'none'}")
    
    return greeting

async def handle_add_numbers_tool(arguments: Dict[str, Any]) -> str:
    """Add numbers tool - shows tracing with validation and error handling"""
    try:
        a = arguments["a"]
        b = arguments["b"]
        logger.info(f"Adding numbers: {a} + {b}")
        
        # Simulate some processing time
        await asyncio.sleep(0.05)
        
        result = a + b
        logger.info(f"Addition result: {result}")
        
        return f"The sum of {a} and {b} is {result}"
        
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid number format: {e}")
        raise ValueError(f"Invalid number format: {e}")

async def handle_slow_operation_tool(arguments: Dict[str, Any]) -> str:
    """Slow operation tool - demonstrates tracing across multiple async steps"""
    steps = arguments.get("steps", 3)
    logger.info(f"Starting slow operation with {steps} steps")
    
    results = []
    
    for i in range(steps):
        logger.info(f"Executing step {i + 1}/{steps}")
        
        # Each async operation automatically inherits the trace context
        step_result = await execute_step(i + 1)
        results.append(step_result)
        
        # Add some delay between steps
        await asyncio.sleep(0.2)
    
    final_result = f"Completed {steps} steps: {', '.join(results)}"
    logger.info(f"Slow operation completed: {final_result}")
    
    return final_result

async def execute_step(step_number: int) -> str:
    """Helper function that executes a single step - context is automatically inherited"""
    logger.info(f"Processing step {step_number}")
    
    # Simulate some work
    await asyncio.sleep(0.1)
    
    step_result = f"Step {step_number} result"
    logger.debug(f"Step {step_number} completed with result: {step_result}")
    
    return step_result

async def handle_parallel_tasks_tool(arguments: Dict[str, Any]) -> str:
    """Parallel tasks tool - shows how context propagates to concurrent operations"""
    task_count = arguments.get("task_count", 3)
    logger.info(f"Starting {task_count} parallel tasks")
    
    # Create multiple async tasks - they all inherit the same trace context!
    tasks = []
    for i in range(task_count):
        task = asyncio.create_task(parallel_worker(i + 1))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    final_result = f"Completed {task_count} parallel tasks: {', '.join(results)}"
    logger.info(f"All parallel tasks completed: {final_result}")
    
    return final_result

async def parallel_worker(worker_id: int) -> str:
    """Worker function for parallel execution - automatically gets trace context"""
    logger.info(f"Worker {worker_id} started")
    
    # Simulate different amounts of work for each worker
    work_time = 0.1 * worker_id
    await asyncio.sleep(work_time)
    
    result = f"Worker-{worker_id}"
    logger.info(f"Worker {worker_id} completed after {work_time}s")
    
    return result

if __name__ == "__main__":
    # For testing the server directly
    server = create_hello_mcp_server()
    print("Hello World MCP Server created!")
    print("Available tools:")
    print("- hello: Say hello with a personalized greeting")
    print("- add_numbers: Add two numbers together") 
    print("- slow_operation: Simulates a slow operation with multiple steps")
    print("- parallel_tasks: Demonstrates parallel async operations")
