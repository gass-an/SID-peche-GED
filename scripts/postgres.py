from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def start() -> None:
    """Démarre PostgreSQL et attend que son healthcheck soit valide."""
    subprocess.run(
        ["docker", "compose", "up", "-d", "--wait", "postgres"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def stop() -> None:
    """Arrête PostgreSQL sans supprimer son volume de données."""
    subprocess.run(
        ["docker", "compose", "stop", "postgres"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestion du PostgreSQL local")
    parser.add_argument("action", choices=("start", "stop"))
    args = parser.parse_args()

    if args.action == "start":
        start()
    else:
        stop()


if __name__ == "__main__":
    main()
