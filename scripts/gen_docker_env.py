"""Create `.env.docker` from the committed example with strong secrets.

Usage:
    python -m scripts.gen_docker_env          # create, refuse to overwrite
    python -m scripts.gen_docker_env --force  # regenerate

The generated file is gitignored and mode 0600 where the OS supports it.
Secrets are never printed.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.docker.example"
TARGET = ROOT / ".env.docker"


def _replace_value(text: str, key: str, value: str) -> str:
    """Replace `KEY=...` while leaving comments and other keys untouched."""
    lines = text.splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        raise SystemExit(f"{EXAMPLE.name} is missing {key}=...")
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing .env.docker (new secrets!).",
    )
    args = parser.parse_args(argv)

    if not EXAMPLE.exists():
        print(f"missing {EXAMPLE}", file=sys.stderr)
        return 2

    if TARGET.exists() and not args.force:
        print(f"{TARGET.name} already exists — leaving it untouched.")
        print("Use --force to regenerate (this rotates the DB password).")
        return 0

    text = EXAMPLE.read_text(encoding="utf-8")
    text = _replace_value(text, "APP_SECRET_KEY", secrets.token_urlsafe(48))
    text = _replace_value(text, "POSTGRES_PASSWORD", secrets.token_urlsafe(24))

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    try:
        os.chmod(TARGET, 0o600)
    except OSError:
        pass  # Windows ACLs; the file is still gitignored.

    print(f"wrote {TARGET.name} with generated APP_SECRET_KEY and POSTGRES_PASSWORD")
    print("Next: make docker-up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
