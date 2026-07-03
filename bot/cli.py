from __future__ import annotations

import typer

from .client import BinanceFuturesClient
from .config import load_settings
from .exceptions import TradingBotError, ValidationError
from .exchange import ExchangeInfo
from .logging_config import setup_logging
from .orders import OrderRequest, OrderResult, OrderService
from .twap import TwapExecutor, TwapPlan, TwapResult
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


def _bootstrap() -> tuple[BinanceFuturesClient, ExchangeInfo, OrderService]:
    settings = load_settings()
    logger = setup_logging(settings.log_dir, settings.log_level)
    client = BinanceFuturesClient(settings, logger)
    exchange = ExchangeInfo(client)
    service = OrderService(client, exchange, logger=logger)
    return client, exchange, service


def _fail(message: str) -> "typer.Exit":
    typer.secho(f"\n✗ FAILURE — {message}", fg=RED, bold=True, err=True)
    return typer.Exit(code=1)


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
    try:
        client, _exchange, service = _bootstrap()
    except TradingBotError as exc:
        raise _fail(str(exc))
    try:
        try:
            request = service.build_request(symbol, side, order_type, quantity, price, tif)
        except ValidationError as exc:
            raise _fail(f"invalid input: {exc}")
        except TradingBotError as exc:
            raise _fail(str(exc))

        _print_request(request)

        if dry_run:
            typer.secho("\n• Dry run — order NOT placed.", fg=YELLOW, bold=True)
            typer.echo(f"  Would send params: {request.to_params()}")
            return

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
    try:
        client, _exchange, _service = _bootstrap()
    except TradingBotError as exc:
        raise _fail(str(exc))
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


def _print_twap_plan(plan: TwapPlan) -> None:
    typer.secho(f"\n{_RULE}", fg=CYAN)
    typer.secho("  TWAP PLAN", fg=CYAN, bold=True)
    typer.secho(_RULE, fg=CYAN)
    typer.echo(f"  Symbol         : {plan.symbol}")
    typer.echo(f"  Side           : {plan.side}")
    typer.echo(f"  Total Quantity : {plain(plan.total_quantity)}")
    typer.echo(f"  Slices         : {plan.slices}")
    typer.echo(f"  Interval       : {plan.interval_seconds:g}s")
    typer.echo(f"  Slice sizes    : {', '.join(plain(q) for q in plan.slice_quantities)}")
    typer.secho(_RULE, fg=CYAN)


def _print_twap_result(result: TwapResult) -> None:
    avg = result.avg_price
    typer.secho(f"\n{_RULE}", fg=CYAN)
    typer.secho("  TWAP RESULT", fg=CYAN, bold=True)
    typer.secho(_RULE, fg=CYAN)
    typer.echo(f"  Slices filled  : {len(result.orders)}/{result.plan.slices}")
    typer.echo(f"  Total Executed : {plain(result.total_executed)}")
    typer.echo(f"  Total Quote    : {plain(result.total_quote)}")
    typer.echo(f"  Avg Price      : {plain(avg) if avg is not None else '—'}")
    typer.echo(f"  Order IDs      : {', '.join(str(o.order_id) for o in result.orders)}")
    typer.secho(_RULE, fg=CYAN)


@app.command()
def twap(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    quantity: str = typer.Option(..., "--quantity", "-q", help="TOTAL quantity to work"),
    slices: int = typer.Option(3, "--slices", "-n", help="Number of MARKET slices"),
    interval: float = typer.Option(
        1.0, "--interval", "-i", help="Seconds to wait between slices"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the slice schedule without placing anything."
    ),
) -> None:
    try:
        client, exchange, service = _bootstrap()
    except TradingBotError as exc:
        raise _fail(str(exc))
    try:
        executor = TwapExecutor(client, service, exchange)
        try:
            plan = executor.plan(symbol, side, quantity, slices, interval)
        except ValidationError as exc:
            raise _fail(f"invalid input: {exc}")
        except TradingBotError as exc:
            raise _fail(str(exc))

        _print_twap_plan(plan)

        if dry_run:
            typer.secho("\n• Dry run — no slices placed.", fg=YELLOW, bold=True)
            return

        typer.echo(f"\nExecuting TWAP ({plan.slices} slices)…")
        try:
            result = executor.execute(plan)
        except TradingBotError as exc:
            raise _fail(str(exc))

        _print_twap_result(result)
        typer.secho(
            f"\n✓ SUCCESS — TWAP done: {plain(result.total_executed)} filled "
            f"across {len(result.orders)} slices.",
            fg=GREEN,
            bold=True,
        )
    finally:
        client.close()


def main() -> None:
    try:
        app()
    except TradingBotError as exc:
        typer.secho(f"\n✗ FAILURE — {exc}", fg=RED, bold=True, err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
