#!/usr/bin/env python3
"""Entry point for running the Concord MCP server.

Usage:
    python -m mcp_server                                   # stdio (default)
    python -m mcp_server --transport streamable-http       # HTTP on port 3001
    python -m mcp_server --transport streamable-http --port 8080
"""

from .server import main

if __name__ == "__main__":
    main()
