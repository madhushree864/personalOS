class MCPError(Exception):
    """Base error for the local MCP integration boundary."""


class MCPRequestError(MCPError):
    """The invocation request is malformed or incomplete."""


class MCPToolNotFoundError(MCPError):
    """The requested server or tool is not registered."""


class MCPAuthorizationError(MCPError):
    """The existing policy decision does not authorize the invocation."""


class MCPToolExecutionError(MCPError):
    """A registered tool could not produce a result."""
