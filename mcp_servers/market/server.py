from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

server = MCPServer(
    name="personalos-market",
    version="0.1.0",
    instructions="Read-only synthetic market data.",
)


@server.tool(
    name="market.read",
    description="Read synthetic market information.",
)
def market_read(symbol: str, context: MCPServerContext) -> dict:
    return {"kind": "market.read", "symbol": symbol}


def run() -> None:
    server.run_stdio_async()
