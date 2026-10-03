from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

def _synthetic_read(query: str, context: MCPServerContext) -> dict:
    return {"kind": "renewal.read", "query": query, "renewals": []}


def create_server(read_handler=_synthetic_read) -> MCPServer:
    server = MCPServer(
        name="personalos-renewal",
        version="0.1.0",
        instructions="Read-only renewal data.",
    )

    @server.tool(
        name="renewal.read",
        description="Read owner-scoped renewal information.",
    )
    def renewal_read(query: str, context: MCPServerContext) -> dict:
        return read_handler(query, context)

    return server


server = create_server()


def run() -> None:
    server.run_stdio_async()
