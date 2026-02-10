#!/bin/bash
cd /Users/raheel/claude-projects/concordcore
exec .venv/bin/python -W ignore::DeprecationWarning -m apps.mcp "$@"
