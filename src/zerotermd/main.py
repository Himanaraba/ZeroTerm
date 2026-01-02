from __future__ import annotations

import logging

from .config import load_config
from .server import run_server


def main() -> None:
    config = load_config()
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_server(config)


if __name__ == "__main__":
    main()
