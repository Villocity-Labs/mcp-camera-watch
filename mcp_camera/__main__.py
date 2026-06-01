from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, write_default_config
from .server import CameraMcpServer


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP server for camera watch instructions.")
    parser.add_argument("--config", default="cameras.json", help="Path to camera config JSON.")
    parser.add_argument("--init-config", action="store_true", help="Create an example config and exit.")
    parser.add_argument("--version", action="store_true", help="Print version metadata and exit.")
    args = parser.parse_args()

    if args.version:
        print(json.dumps({"name": "mcp-camera-watch", "credits": "Steve Villari and Villocity Labs"}))
        return 0

    config_path = Path(args.config)
    if args.init_config:
        write_default_config(config_path)
        print(f"Wrote {config_path}")
        return 0

    if not config_path.exists():
        write_default_config(config_path)
        print(
            f"No config found, so an example was written to {config_path}. Edit it, then restart the server.",
            file=sys.stderr,
        )

    CameraMcpServer(load_config(config_path)).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
