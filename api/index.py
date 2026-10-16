import hashlib
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

EMAIL = "25ds3000041@ds.study.iitm.ac.in".strip().lower()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

TOOLS = [{
    "name": "solve_challenge",
    "description": "Returns the first 16 hex chars of SHA-256('<X-Exam-Challenge>:<email>').",
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": True},
}]


def solve(challenge: str) -> str:
    return hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]


def handle(msg: dict, req: Request):
    method, msg_id = msg.get("method"), msg.get("id")
    params = msg.get("params") or {}
    if msg_id is None:                      # notification, e.g. notifications/initialized
        return None
    if method == "initialize":
        result = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        if params.get("name") != "solve_challenge":
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": "Unknown tool"}}
        challenge = req.headers.get("x-exam-challenge", "")   # raw value, this call only
        result = {"content": [{"type": "text", "text": solve(challenge)}], "isError": False}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


@app.post("/")
@app.post("/mcp")
async def mcp(req: Request):
    body = await req.json()
    if isinstance(body, list):              # JSON-RPC batch
        out = [r for r in (handle(m, req) for m in body) if r is not None]
        return out if out else Response(status_code=202)
    out = handle(body, req)
    return out if out is not None else Response(status_code=202)


@app.get("/")
@app.get("/mcp")
async def info():
    return Response(status_code=405, headers={"Allow": "POST"})
