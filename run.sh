#!/bin/bash
# Kill existing Reflex processes
lsof -i :3000 -t 2>/dev/null | xargs kill 2>/dev/null
lsof -i :8000 -t 2>/dev/null | xargs kill 2>/dev/null
sleep 1

uv run reflex run
