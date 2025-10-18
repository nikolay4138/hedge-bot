## Binance Futures Hedge/Breakout Bot – Repository Documentation

This repository implements a modular, async trading system for Binance USDT-Margined Futures with:
- Rule-based signal evaluation (breakouts, momentum, ATR, volume, EMA conditions)
- Hedging logic with coordinated open/close controllers
- Leverage management
- Profit/stop controllers
- Data ingestion (OHLCV, positions, balance) into SQLite
- Async task orchestration and an interactive CLI
- Telegram integration for start/stop and notifications

The codebase is written in Python (async-first), uses CCXT for exchange access, sqlite3 for local state, pandas/numpy/ta for analysis, and websockets/aiohttp for streaming and HTTP.


### Tech stack
- **Python**: asyncio, sqlite3, pandas, numpy, ta, aiohttp, websockets, requests, psutil
- **CCXT (async)**: Binance USDⓈ-M Futures trading
- **SQLite (WAL mode)**: local state and telemetry
- **Telegram**: python-telegram-bot or direct HTTP (sender) for notifications

Install base deps:
```bash
pip install -r requirements.txt
# extras likely needed (not pinned in requirements):
pip install python-telegram-bot==20.* nest-asyncio
```


## Repository structure
- `main/`
  - `task_manager/` async worker, interactive CLI task manager
    - `worker_manager.py`: `AdvancedAsyncWorker` – a cancellable, retrying async queue/worker
    - `task_manager.py`: wraps global worker, exposes start/stop/list
    - `task_library.py`: demo tasks (Balance/Position/Price/Analyzer simulators)
    - `main.py`: interactive console controller entrypoint
  - `asenkron_manager.py`: example that starts real collectors with the worker
  - `telegram_listener.py`: Telegram bot `/start` and `/stop`
  - `logger.py`, `killer.py`: scaffolding utilities
- `core/`
  - `trading.py`: `BinanceFuturesTrader` thin wrapper around `ccxt.async_support`
  - `getIndicators.py`: advanced indicator pipeline incl. RSI/EMA/ATR/volume dev and Fibonacci-level analysis
  - `ruleSystem/`
    - `ruleEngine.py`: loads rule sets from JSON and evaluates condition expressions
    - `jsonEditor.py`: PyQt5 JSON visual editor (optional tooling)
  - `utils/`
    - `databaseProcess.py`: `SQLiteManager` and `DBReader` helpers (WAL mode, generic ops)
    - `getTimeframe.py`: resampling seconds OHLCV to higher TFs
    - `getusdtPairs.py`, `getMin.py`, `getleverage.py`, `getlastPrice.py` etc.
    - `functions.py`: `Processor` utilities (trade ops, list ops, profit math, time, TF generation)
- `dataGetter/`
  - `get_ohlcv.py`: 1s kline aggregation via Binance WS → `binance_data/ohlcv.db` (one table per symbol)
  - `getPos.py`: fetch open positions → `binance_data/open.db`
  - `getBal.py`: fetch account balances → `binance_data/balance.db`
- `breakoutController/`
  - `controller.py`: evaluate rules on OHLCV, write breakouts; includes concurrent fanout helpers
  - `opener.py`: open hedging legs after a recent breakout
  - `closer.py`: close opposite hedging leg when breakout direction confirms
- `leverage_controller/`
  - `controller.py`: adjusts leverage per symbol based on min amounts and notional tiers
- `psManager/`
  - `psController/`, `psCloser/`, `stoploss/`: profit/stop modules using processors and rule engine
- `tMessager/`
  - `main.py`: minimal Telegram HTTP sender
  - `sender.py`: scans DB tables and posts last rows (may require aligning imports)
- `binance_data/`: sqlite databases produced/used by the system
- `hedge_bot_docs/`: diagrams and DB screenshots
- `additional/`: experiments and analysis scripts (cycle analysis, volume spikes)


## High-level architecture and data flow
1) **Ingestion**
   - `dataGetter/get_ohlcv.py` connects to Binance futures WS for `@kline_1m`, aggregates to 1-second bars in memory, and flushes once per second to `binance_data/ohlcv.db` with one table per symbol: `timestamp INTEGER PRIMARY KEY, open, high, low, close, volume`.
   - `dataGetter/getPos.py` periodically fetches open positions via CCXT and writes to `binance_data/open.db`:
     - `open_symbol`: list of active symbols
     - `positions`: list of per-position table names
     - `SYMBOL_POSITION_SIDE` tables with columns like `entryPrice`, `amount`, `unRealizedProfit`, etc.
   - `dataGetter/getBal.py` periodically fetches futures balance and writes to `binance_data/balance.db` (table `balance`).

2) **Rule evaluation**
   - `core/ruleSystem/ruleEngine.py` loads rules from `core/config.json` using dot-notation paths; each rule has a `condition` expression, e.g. `rsi_1m>50 and rsi_5m>89`.
   - `core/getIndicators.py` computes enriched indicators on resampled OHLCV and derives Fibonacci levels across last RSI wave.
   - `core/utils/functions.py::Processor.TradeProcessor` and `ruleExtractor` prepare `variables` expected by rules (e.g., `fib_618_5m`, `rsi_1m`, `atr_15m`, `volume_5m`, etc.), evaluate `RuleReader.evaluate_all_rules`, and return pass/fail.

3) **Controllers**
   - `breakoutController/controller.py` (`Breakout.main(symbol, key)`): reads latest OHLCV, evaluates the rule group identified by `key`, and writes a breakout record when all rules pass (recent breakout state read/written via DB helpers).
   - `breakoutController/opener.py`: if a recent breakout occurred and the timestamp is fresh (within N minutes), open the opposite leg if the counterpart side is already present, extending a hedge.
   - `breakoutController/closer.py`: when both LONG and SHORT are open for a symbol and breakout confirms direction, close the opposite side to unhedge.
   - `leverage_controller/controller.py`: every 10s loads `open_symbol`, reads per-symbol `min_amounts` and available notional tiers, computes closest max notional and selects a matching leverage tier, then updates via CCXT `set_leverage`.
   - `psManager/psCloser/controller.py`: evaluates profit-taking per position using expected ATR-based projections across multiple TFs, closes when profit threshold is met, then optionally reopens with min amount. Also includes per-position profit/stop closers respecting rule keys.
   - `psManager/stoploss/controller.py`: emergency stop if a single symbol’s unrealized PnL crosses a balance-based threshold; closes both legs and records to `general_stoploss` DB.

4) **Orchestration**
   - `main/task_manager/worker_manager.py` provides `AdvancedAsyncWorker` (queue-based workers with retries, timeouts, and cancellation). Global worker helpers are exposed.
   - `main/task_manager/task_manager.py` wraps the global worker; `interactive_controller.py` presents a CLI to start/stop/list tasks from `task_library`.
   - `main/task_manager/main.py` is the interactive entrypoint; `main/asenkron_manager.py` shows how to enqueue real collectors (balance/positions) via the worker.

5) **Messaging and control**
   - `main/telegram_listener.py` uses `python-telegram-bot` to expose `/start` and `/stop` for operational toggling; persists events into DB via DB helper layer.
   - `tMessager/main.py` provides a simple `TelegramBot` over HTTP; `tMessager/sender.py` demonstrates iterating DB tables to post last rows periodically.


## Key modules and classes
- Trading/exchange
  - `core/trading.py::BinanceFuturesTrader`: loads API keys from `core/config.json`, wraps CCXT (async) for `fetch_balance`, `fetch_positions`, `create_order`, `set_leverage`.

- Indicators and rules
  - `core/getIndicators.py::AdvancedTechnicalIndicatorsFibLevels`: computes RSI/EMA/ATR/volume features and derives recent Fibonacci levels by locating last RSI overbought/oversold wave.
  - `core/ruleSystem/ruleEngine.py::RuleReader`: loads a rule group by JSON path and evaluates expressions with the provided variable map.
  - `core/utils/functions.py::Processor.TradeProcessor`: builds variables and calls `RuleReader`; contains helpers to open/close via `BinanceFuturesTrader`.

- Data ingestion
  - `dataGetter/get_ohlcv.py::getData`: per-symbol WS listener and 1-second aggregation → SQLite writer; `run_all()` also schedules USDT pairs refresher.
  - `dataGetter/getPos.py::GetPositions`: fetches positions, writes `open_symbol`, `positions`, and per-position tables.
  - `dataGetter/getBal.py::BalanceCollector`: fetches and writes `balance` table.

- Controllers
  - `breakoutController/(controller|opener|closer).py`: breakout detection, and open/close hedging legs according to recent breakout and current position state.
  - `leverage_controller/controller.py::LeverageController`: computes best leverage tier based on min amount and available notional tiers.
  - `psManager/psCloser/controller.py::PsCloser`: profit-close and reopen; `psManager/stoploss/controller.py::Stoploss` for emergency closes.

- Orchestration & CLI
  - `main/task_manager/worker_manager.py::AdvancedAsyncWorker`: cancellable, retrying async task workers.
  - `main/task_manager/task_manager.py::TaskManager`: starts/stops tasks; `interactive_controller.py` CLI.


## Databases
SQLite files live under `binance_data/` (WAL mode enabled for concurrent reads/writes).

Common DBs used in code:
- `ohlcv.db`: One table per symbol (uppercased), columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- `open.db`:
  - `open_symbol(symbol TEXT)` – list of active symbols
  - `positions(pos TEXT)` – list of position table names
  - `SYMBOL_LONG` / `SYMBOL_SHORT` tables: `symbol, pos_side, amount, entryPrice, liquidationPrice, initialMargin, unRealizedProfit, updateTime`
- `balance.db`: `balance(timestamp, wallet_balance, total, available, unreal_profit)`
- `leverage_data.db`: per-symbol leverage tiers (e.g., `maxNotionalValue`)
- `min_amounts.db`: per-symbol minimal trade amount
- `breakout.db`, `added.db`, `opened.db`, `closed.db`, `stoploss.db`, `general_stoploss.db`, `hedge.db`, `daily_profit.db`, `total_lost.db` – used by various controllers; schemas are created on demand via `SQLiteManager.create_table` before insert.

Notes:
- `SQLiteManager` auto-creates tables with TEXT columns by default for dynamic `insert`; explicit schemas are used in ingestion modules.
- WAL mode is enabled to reduce writer/reader contention.


## Configuration
User-provided `core/config.json` is required (gitignored). It serves two purposes:
- Exchange and Telegram credentials
- Rule sets for the rule engine

A minimal example (do not commit real secrets):
```json
{
  "config": [
    {
      "API_KEY": "YOUR_BINANCE_API_KEY",
      "API_SECRET": "YOUR_BINANCE_API_SECRET",
      "TOKEN": "YOUR_TELEGRAM_BOT_TOKEN",
      "wallet_cid": "YOUR_TELEGRAM_CHAT_OR_USER_ID"
    }
  ],
  "bigTimeframes": {
    "breakout1": {
      "1": { "condition": "lastPrice > fib_618_5m" },
      "2": { "condition": "rsi_1m > 50 and rsi_5m > 89" },
      "3": { "condition": "(atr_1m > 78 and atr_5m < 8) or (atr_5m > 30 and atr_15m < 10)" },
      "4": { "condition": "ema3_1m < ema7_1m and ema3_5m > ema7_5m" },
      "5": { "condition": "volume_1m > 3_avg and volume_5m > 5_avg" },
      "6": { "condition": "close_1m_3 < fib_382_5m and close_5m_2 > fib_382_5m" }
    }
  }
}
```
Rule IDs (`"1"..`) are arbitrary keys under a group (e.g., `bigTimeframes.breakout1`). Each `condition` is evaluated with a variable map prepared by `ruleExtractor` using indicators computed from resampled OHLCV.


## How to run
Prereqs:
- Python 3.11+ recommended (repo caches indicate 3.13 works)
- `pip install -r requirements.txt` plus extras mentioned above
- Create `core/config.json` as shown (testnet recommended first)

Data ingestion (recommended to run first):
```bash
# 1s aggregation from WS → ohlcv.db and periodic USDT pairs refresh
python -m dataGetter.get_ohlcv
```

Operational modes:
```bash
# Interactive task controller (start/stop demo tasks via CLI)
python -m main.task_manager.main

# Example async manager that starts balance & positions collectors
python -m main.asenkron_manager

# Telegram listener with /start and /stop (requires python-telegram-bot, nest-asyncio)
python -m main.telegram_listener

# Leverage controller loop
python -m leverage_controller.controller

# Breakout analysis examples (concurrent processing helpers)
python -m breakoutController.controller
```

Optional messaging:
- `tMessager/main.py` provides minimal Telegram sender class
- `tMessager/sender.py` iterates DBs and posts last rows (align imports as needed)


## Operational notes and gotchas
- Prefer running the system with testnet first (`BinanceFuturesTrader(testnet=True)`). Some controllers construct traders internally; adjust code or config to use testnet during validation.
- `core/config.json` is required; never commit secrets. Tokens and chat IDs are referenced by code as `config["config"][0]`.
- The codebase includes both demo/simulated tasks (under `task_library`) and real tasks (collectors/controllers). Use the interactive task manager for orchestration patterns; use dedicated module `__main__` runners for specific controllers.
- Some helper modules under `core/utils/getDatabase.py` appear to be stubs/in-progress and may need alignment with `databaseProcess.DBReader/SQLiteManager` APIs. Refer to ingestion modules for canonical table creation and access patterns.
- SQLite runs in WAL mode; databases are placed under `binance_data/`. Make sure the process has write permissions.
- Websocket connections can be many (per symbol). `get_ohlcv.py` uses a partitioned port mapping strategy for optional proxying.


## Extending the system
- Add a rule group: extend `core/config.json` with a new nested path (e.g., `smallTimeframes.breakoutA`). Use the same `condition` expression style.
- Add a controller: create a module under `breakoutController/` or `psManager/` and reuse `Processor` helpers for trading and DB access.
- Add tasks to the CLI: extend `main/task_manager/task_library.py` with your async class exposing `async def main(self, ...)` and register it in `TASK_LIBRARY`.


## Diagrams
See `hedge_bot_docs/` for architecture sketches and DB snapshots you can reference in reviews and operations:
- `hedge_listener.png`, `hedge_listener.drawio.png`
- `breakout_main_func.drawio`
- DB schemas: `balance.db.png`, `open.db.png`, `leverage_data.db.png`, etc.


## Security
- Treat all credentials as sensitive (never commit). Scope API keys to least-privilege and prefer IP restrictions where possible.
- Favor testnet and small sizing defaults. Always confirm behavior with dry runs or guard rails before using real funds.


## FAQ
- Why SQLite? Lightweight local persistence with WAL allows concurrent reads by controllers and monitoring.
- Why CCXT async? Integrates cleanly with asyncio for concurrent orchestration.
- How are conditions evaluated? String expressions evaluated against a prepared variable map; errors mark a rule as failed. Validate carefully.
