"""CLI entrypoint for running Startup Guardian from the command line."""
from __future__ import annotations

import asyncio
import json
import sys

from src.orchestration.run_startup_guardian import run_startup_guardian


def main() -> None:
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    result = asyncio.run(run_startup_guardian(tenant_id))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
