#!/bin/bash
# Kill existing Reflex processes (backend, frontend, and parent)
pkill -f "mcp-client" 2>/dev/null
sleep 1

uv run reflex run
