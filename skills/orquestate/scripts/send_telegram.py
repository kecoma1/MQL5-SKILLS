#!/usr/bin/env python3
"""Send a Telegram orchestration message for an MT5 account."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_no}: linea sin '='")
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def resolve_env_file(args: argparse.Namespace) -> Path:
    if args.env_file:
        return Path(args.env_file).expanduser().resolve()
    accounts_dir = Path(args.accounts_dir).expanduser()
    return (accounts_dir / str(args.account_id) / "telegram.env").resolve()


def read_message(args: argparse.Namespace) -> str:
    if args.message_file:
        return Path(args.message_file).read_text(encoding="utf-8")
    if args.message:
        return args.message
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            return data
    raise ValueError("indica --message, --message-file o texto por stdin")


def send_message(api_key: str, target: str, text: str, timeout: float) -> dict[str, object]:
    query = urllib.parse.urlencode({"chat_id": target, "text": text})
    url = f"https://api.telegram.org/bot{api_key}/sendMessage?{query}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"target": target, "status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"target": target, "status": exc.code, "body": body}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send Telegram messages for account orchestration.")
    parser.add_argument("--account-id", help="MT5 account id. Used to resolve accounts/<id>/telegram.env.")
    parser.add_argument("--accounts-dir", default="accounts", help="Accounts directory. Default: accounts.")
    parser.add_argument("--env-file", help="Explicit telegram.env path.")
    parser.add_argument("--message", help="Message text to send.")
    parser.add_argument("--message-file", help="UTF-8 file containing the message text.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and print targets without sending.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.env_file and not args.account_id:
        parser.error("--account-id is required unless --env-file is used")

    try:
        env_file = resolve_env_file(args)
        if not env_file.exists():
            raise FileNotFoundError(f"no existe {env_file}")

        config = parse_env(env_file)
        api_key = config.get("TELEGRAM_API_KEY", "").strip()
        chat = config.get("TELEGRAM_CHAT", "").strip()
        channel = config.get("TELEGRAM_CHANNEL", "").strip()
        if not api_key:
            raise ValueError("TELEGRAM_API_KEY esta vacio o no existe")
        if not chat:
            raise ValueError("TELEGRAM_CHAT esta vacio o no existe")

        message = read_message(args)
        targets = [chat]
        if channel:
            targets.append(channel)

        if args.dry_run:
            print(json.dumps({"env_file": str(env_file), "targets": targets, "sent": False}, ensure_ascii=False))
            return 0

        results = [send_message(api_key, target, message, args.timeout) for target in targets]
        print(json.dumps({"env_file": str(env_file), "results": results}, ensure_ascii=False))
        failed = [result for result in results if int(result["status"]) != 200]
        return 1 if failed else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
