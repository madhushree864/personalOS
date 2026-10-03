# MCP servers

This directory reserves the boundary for future MCP server implementations.
The current MCP foundation intentionally uses only local, deterministic mock
read-only tools registered by `backend/app/mcp/registry.py`.

No external service, broker, banking system, financial credential, or real
financial execution is connected here. The Policy Engine remains outside MCP
and is the authorization boundary.
