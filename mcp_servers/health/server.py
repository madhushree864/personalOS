from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

server = MCPServer(
    name="personalos-health",
    version="0.1.0",
    instructions="Read-only synthetic health data.",
)


@server.tool(
    name="health.read",
    description="Read synthetic health information.",
)
def health_read(metric: str, context: MCPServerContext) -> dict:
    return {"kind": "health.read", "metric": metric}


def run() -> None:
    server.run_stdio_async()
