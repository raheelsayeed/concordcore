#!/bin/bash
cd /Users/raheel/claude-projects/concordcore
exec .venv/bin/python -W ignore::DeprecationWarning -m mcp_server "$@"
