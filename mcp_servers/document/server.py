from mcp.server.mcpserver import MCPServer

from mcp_servers.common.context import MCPServerContext

server = MCPServer(
    name="personalos-document",
    version="0.1.0",
    instructions="Read-only synthetic document retrieval.",
)


@server.tool(
    name="document.search",
    description="Search synthetic owned document chunks.",
)
def document_search(
    query: str,
    top_k: int = 5,
    context: MCPServerContext | None = None,
) -> dict:
    return {"kind": "document.search", "query": query, "top_k": top_k, "results": []}


def run() -> None:
    server.run_stdio_async()
