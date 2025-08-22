# FastMCP Examples

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m src.main
pip install -e .
```

### 2. Run the Server

```bash
uv run python -m src.main
```

The server will start on `http://localhost:8081`

### 3. Test the Endpoints

**Homepage with trace info:**
```bash
curl http://localhost:8081/
```

**Health check:**
```bash
curl http://localhost:8081/health
```

**Async operations demo:**
```bash
curl http://localhost:8081/demo-async
```

**Ping with trace headers:**
```bash
curl -H "X-Session-ID: my-session-123" http://localhost:8080/ping
```

## 📊 Understanding the Logs

When you make requests, you'll see logs like this:

```
2024-01-15 10:30:45 - src.main - INFO - [req=a1b2c3d4|session=550e8400] - Request started: GET /
2024-01-15 10:30:45 - src.main - INFO - [req=a1b2c3d4|session=550e8400] - Homepage accessed
2024-01-15 10:30:45 - src.tracing_middleware - INFO - [req=a1b2c3d4|session=550e8400] - Request completed: 200 in 12.3ms
```