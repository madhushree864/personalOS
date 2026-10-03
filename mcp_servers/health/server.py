from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

def _synthetic_read(metric: str, context: MCPServerContext) -> dict:
    return {"kind": "health.read", "metric": metric, "records": []}


def create_server(read_handler=_synthetic_read) -> MCPServer:
    server = MCPServer(
        name="personalos-health",
        version="0.1.0",
        instructions="Read-only health data.",
    )

    @server.tool(
        name="health.read",
        description="Read owner-scoped health records.",
    )
    def health_read(metric: str, context: MCPServerContext) -> dict:
        return read_handler(metric, context)

    return server


server = create_server()


def run() -> None:
    server.run_stdio_async()
