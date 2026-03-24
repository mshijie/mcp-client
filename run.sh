#!/bin/bash
# Kill existing Reflex processes (backend, frontend, and parent)
pkill -f "bin/reflex run" 2>/dev/null
pkill -f "react-router dev" 2>/dev/null
pkill -f "uv run reflex" 2>/dev/null
sleep 1

uv run reflex run
