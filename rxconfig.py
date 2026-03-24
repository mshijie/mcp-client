import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import reflex as rx

config = rx.Config(
    app_name="mcp_client",
    plugins=[rx.plugins.SitemapPlugin()],
)
