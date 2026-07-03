"""Trading bot for the Binance USDT-M Futures testnet.

Package layout (built incrementally across the project's 4 steps):

    config.py          -> settings & secret loading          (Step 1)
    logging_config.py  -> console + rotating-file logging     (Step 1)
    exceptions.py      -> custom exception hierarchy           (Step 1)
    client.py          -> signed REST client wrapper           (Step 1)
    healthcheck.py     -> connectivity smoke test              (Step 1)
    validators.py      -> input validation                     (Step 2)
    orders.py          -> order placement logic                (Step 2)
    cli.py             -> CLI entry point                       (Step 3)
"""

__version__ = "0.1.0"
