"""Command-line interface for YooMoney API.

Usage examples::

    # Show account info
    yoomoney --token TOKEN account

    # Show last 10 operations
    yoomoney --token TOKEN history --records 10

    # Filter by label
    yoomoney --token TOKEN history --label order_42

    # Check a specific operation
    yoomoney --token TOKEN details --id <operation_id>

    # Watch for a payment (polling)
    yoomoney --token TOKEN watch --label order_42 --amount 500 --timeout 300

    # Check balance only
    yoomoney --token TOKEN balance

Token can also be set via YOOMONEY_TOKEN environment variable
to avoid passing it on every call.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from yoomoney.checker.checker import PaymentChecker
from yoomoney.client import Client


def _get_token(args: argparse.Namespace) -> str:
    token = args.token or os.environ.get("YOOMONEY_TOKEN", "")
    if not token:
        print(
            "Error: token is required. Pass --token TOKEN or set YOOMONEY_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    """Print a simple aligned table."""
    all_rows = [headers, *rows]
    widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    sep = "  ".join("-" * w for w in widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)

    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))


def cmd_account(args: argparse.Namespace) -> None:
    client = Client(token=_get_token(args))
    info = client.account_info()
    print(f"Account:  {info.account}")
    print(f"Balance:  {info.balance} {info.currency}")
    print(f"Type:     {info.account_type}")
    print(f"Status:   {info.account_status}")


def cmd_balance(args: argparse.Namespace) -> None:
    client = Client(token=_get_token(args))
    info = client.account_info()
    print(f"{info.balance} {info.currency}")


def cmd_history(args: argparse.Namespace) -> None:
    client = Client(token=_get_token(args))

    from_date: datetime | None = None
    till_date: datetime | None = None

    if args.from_date:
        from_date = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc)
    if args.till_date:
        till_date = datetime.fromisoformat(args.till_date).replace(tzinfo=timezone.utc)

    history = client.operation_history(
        label=args.label or None,
        type=args.type or None,
        from_date=from_date,
        till_date=till_date,
        records=args.records,
    )

    if not history.operations:
        print("No operations found.")
        return

    rows = [
        [
            op.operation_id or "—",
            str(op.datetime)[:19] if op.datetime else "—",
            op.direction or "—",
            f"{op.amount:.2f}" if op.amount is not None else "—",
            op.status or "—",
            op.label or "—",
            (op.title or "—")[:40],
        ]
        for op in history.operations
    ]
    _print_table(
        rows,
        ["ID", "DateTime", "Direction", "Amount", "Status", "Label", "Title"],
    )

    if history.next_record:
        print(f"\nMore records available. Use --start-record {history.next_record}")


def cmd_details(args: argparse.Namespace) -> None:
    client = Client(token=_get_token(args))
    op = client.operation_details(args.id)
    for field, value in op.model_dump().items():
        if value is not None:
            print(f"{field:<25} {value}")


def cmd_watch(args: argparse.Namespace) -> None:
    token = _get_token(args)
    checker = PaymentChecker(token=token, interval=args.interval)

    print(
        f"Watching for payment: label={args.label!r}, "
        f"amount={args.amount}, timeout={args.timeout}s"
    )
    print("Press Ctrl+C to cancel.")

    def on_payment(op: object) -> None:  
        from yoomoney.operation.operation import Operation  # noqa: PLC0415

        if isinstance(op, Operation):
            print(f"\n✓ Payment received!")
            print(f"  operation_id : {op.operation_id}")
            print(f"  amount       : {op.amount}")
            print(f"  label        : {op.label}")
            print(f"  datetime     : {op.datetime}")

    found = checker.watch(
        label=args.label,
        callback=on_payment,  # type: ignore[arg-type]
        amount=args.amount,
        timeout=args.timeout,
    )
    sys.exit(0 if found else 1)


def cmd_make_label(args: argparse.Namespace) -> None:
    label = PaymentChecker.make_label(prefix=args.prefix)
    print(label)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yoomoney",
        description="YooMoney API command-line tool",
    )
    parser.add_argument(
        "--token",
        metavar="TOKEN",
        help="YooMoney OAuth token (or set YOOMONEY_TOKEN env var)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # account
    sub.add_parser("account", help="Show account info")

    # balance
    sub.add_parser("balance", help="Print balance only")

    # history
    hist = sub.add_parser("history", help="Show operation history")
    hist.add_argument("--label", help="Filter by label")
    hist.add_argument("--type", choices=["payment", "deposition"], help="Filter by type")
    hist.add_argument("--records", type=int, default=30, help="Number of records (default 30)")
    hist.add_argument("--from-date", dest="from_date", metavar="ISO", help="Start date (ISO 8601)")
    hist.add_argument("--till-date", dest="till_date", metavar="ISO", help="End date (ISO 8601)")

    # details
    det = sub.add_parser("details", help="Show operation details")
    det.add_argument("--id", required=True, metavar="OPERATION_ID")

    # watch
    watch = sub.add_parser("watch", help="Poll until payment with label arrives")
    watch.add_argument("--label", required=True, help="Label to watch for")
    watch.add_argument("--amount", type=float, default=None, help="Minimum expected amount")
    watch.add_argument("--timeout", type=float, default=300, help="Timeout in seconds (default 300)")
    watch.add_argument("--interval", type=float, default=10, help="Polling interval (default 10s)")

    # make-label
    ml = sub.add_parser("make-label", help="Generate a unique payment label")
    ml.add_argument("--prefix", default="order", help="Label prefix (default: order)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers: dict[str, object] = {
        "account": cmd_account,
        "balance": cmd_balance,
        "history": cmd_history,
        "details": cmd_details,
        "watch": cmd_watch,
        "make-label": cmd_make_label,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)  # type: ignore[operator]
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
