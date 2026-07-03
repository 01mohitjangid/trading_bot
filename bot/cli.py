"""Command-line interface for the trading bot.

A thin presentation layer over `OrderService`: it parses/validates CLI input,
prints a clear request summary and response, and reports success or failure.
All business logic lives in the domain layer (orders/validators/exchange).

Examples:
    python -m bot.cli order -s BTCUSDT --side BUY  -t MARKET -q 0.002
    python -m bot.cli order -s BTCUSDT --side BUY  -t LIMIT  -q 0.002 -p 55000
    python -m bot.cli order -s BTCUSDT --side SELL -t LIMIT  -q 0.002 -p 70000 --dry-run
    python -m bot.cli balance
"""
from __future__ import annotations

import typer

from .client import BinanceFuturesClient
from .config import Settings, load_settings
from .exceptions import TradingBotError, ValidationError
from .logging_config import get_logger, setup_logging
from .orders import OrderRequest, OrderResult, OrderService
from .validators import plain

app = typer.Typer(
    add_completion=False,
    help="Place orders on the Binance USDT-M Futures testnet.",
)

GREEN = typer.colors.GREEN
RED = typer.colors.RED
YELLOW = typer.colors.YELLOW
CYAN = typer.colors.CYAN

_RULE = "─" * 46


# --------------------------------------------------------------------------- #
# Setup helpers
# --------------------------------------------------------------------------- #
def _bootstrap() -> tuple[Settings, BinanceFuturesClient, OrderService]:
    """Load settings, configure logging, and wire up the service."""
    settings = load_settings()
    logger = setup_logging(settings.log_dir, settings.log_level)
    client = BinanceFuturesClient(settings, logger)
    service = OrderService(client, logger=logger)
    return settings, client, service


def _fail(message: str) -> "typer.Exit":
    """Print a red failure line and return an Exit(1) to raise."""
    typer.secho(f"\n✗ FAILURE — {message}", fg=RED, bold=True, err=True)
    return typer.Exit(code=1)


# --------------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------------- #
def _print_request(request: OrderRequest) -> None:
    typer.secho(f"\n{_RULE}", fg=CYAN)
    typer.secho("  ORDER REQUEST", fg=CYAN, bold=True)
    typer.secho(_RULE, fg=CYAN)
    typer.echo(f"  Symbol         : {request.symbol}")
    typer.echo(f"  Side           : {request.side}")
    typer.echo(f"  Type           : {request.type}")
    typer.echo(f"  Quantity       : {plain(request.quantity)}")
    if request.type == "LIMIT" and request.price is not None:
        typer.echo(f"  Price          : {plain(request.price)}")
        typer.echo(f"  Time in force  : {request.time_in_force}")
    typer.secho(_RULE, fg=CYAN)


def _num_or_dash(value: str) -> str:
    """Render a numeric string, collapsing empty/zero values to an em dash."""
    try:
        return value if value and float(value) != 0 else "—"
    except ValueError:
        return value or "—"


def _print_response(result: OrderResult) -> None:
    typer.secho(f"\n{_RULE}", fg=CYAN)
    typer.secho("  ORDER RESPONSE", fg=CYAN, bold=True)
    typer.secho(_RULE, fg=CYAN)
    typer.echo(f"  Order ID       : {result.order_id}")
    typer.echo(f"  Symbol         : {result.symbol}")
    typer.echo(f"  Side           : {result.side}")
    typer.echo(f"  Type           : {result.type}")
    typer.echo(f"  Status         : {result.status}")
    typer.echo(f"  Orig Qty       : {result.orig_qty}")
    typer.echo(f"  Executed Qty   : {result.executed_qty}")
    typer.echo(f"  Avg Price      : {_num_or_dash(result.avg_price)}")
    if result.type == "LIMIT":
        typer.echo(f"  Limit Price    : {_num_or_dash(result.price)}")
    typer.echo(f"  Cum. Quote     : {_num_or_dash(result.cum_quote)}")
    typer.secho(_RULE, fg=CYAN)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
@app.command()
def order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT"),
    quantity: str = typer.Option(..., "--quantity", "-q", help="Order quantity (base asset)"),
    price: str | None = typer.Option(
        None, "--price", "-p", help="Limit price (required for LIMIT orders)"
    ),
    tif: str = typer.Option("GTC", "--tif", help="Time in force for LIMIT (GTC/IOC/FOK/GTX)"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate and show the request without placing it."
    ),
) -> None:
    """Place a MARKET or LIMIT order (BUY/SELL) on the futures testnet."""
    _settings, client, service = _bootstrap()
    try:
        # 1) Validate input against live exchange filters.
        try:
            request = service.build_request(symbol, side, order_type, quantity, price, tif)
        except ValidationError as exc:
            raise _fail(f"invalid input: {exc}")
        except TradingBotError as exc:
            raise _fail(str(exc))

        _print_request(request)

        # 2) Dry run stops here — nothing is sent to the exchange.
        if dry_run:
            typer.secho("\n• Dry run — order NOT placed.", fg=YELLOW, bold=True)
            typer.echo(f"  Would send params: {request.to_params()}")
            return

        # 3) Place the order.
        typer.echo("\nPlacing order…")
        try:
            result = service.place(request)
        except TradingBotError as exc:
            raise _fail(str(exc))

        _print_response(result)
        typer.secho(
            f"\n✓ SUCCESS — order {result.order_id} accepted (status={result.status}).",
            fg=GREEN,
            bold=True,
        )
    finally:
        client.close()


@app.command()
def balance() -> None:
    """Show your futures USDT balance (a quick signed-request check)."""
    _settings, client, _service = _bootstrap()
    try:
        try:
            usdt = client.get_usdt_balance()
        except TradingBotError as exc:
            raise _fail(str(exc))
        if usdt is None:
            typer.secho("No USDT balance entry found.", fg=YELLOW)
            return
        typer.secho(
            f"USDT balance: {usdt.get('balance')} "
            f"(available: {usdt.get('availableBalance')})",
            fg=GREEN,
        )
    finally:
        client.close()


def main() -> None:
    # Ensure logging is configured even if a command errors during bootstrap.
    get_logger()
    app()


if __name__ == "__main__":
    main()
