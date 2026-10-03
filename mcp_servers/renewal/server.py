from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

server = MCPServer(
    name="personalos-renewal",
    version="0.1.0",
    instructions="Read-only synthetic renewal data.",
)


@server.tool(
    name="renewal.read",
    description="Read synthetic renewal information.",
)
def renewal_read(query: str, context: MCPServerContext) -> dict:
    return {"kind": "renewal.read", "query": query}


def run() -> None:
    server.run_stdio_async()
