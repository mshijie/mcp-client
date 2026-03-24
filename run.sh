#!/bin/bash
# Kill existing Reflex processes
pkill -f "reflex run" 2>/dev/null
pkill -f "mcp_client" 2>/dev/null
sleep 1

uv run reflex run
