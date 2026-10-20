"""Pulls daily OHLCV data from Yahoo Finance and upserts it into raw.stock_prices.

Kept IO-free in the middle: get_tickers/download_prices/upsert_records touch
the outside world, to_records is a pure function so it can be unit tested
without a network call or a database.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import psycopg2
import psycopg2.extras
import yfinance as yf

DEFAULT_LOOKBACK_DAYS = 10


def get_tickers() -> list[str]:
    raw = os.environ.get("TICKERS", "AAPL,MSFT,GOOGL,AMZN,TSLA")
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def download_prices(ticker: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> pd.DataFrame:
    start = date.today() - timedelta(days=lookback_days)
    return yf.download(ticker, start=start, progress=False, auto_adjust=False)


def to_records(df: pd.DataFrame, ticker: str) -> list[dict]:
    """Reshape a yfinance OHLCV frame into flat dicts ready for upsert."""
    if df.empty:
        return []

    # yfinance returns a MultiIndex column frame when columns include the
    # ticker level; flatten it so column names are plain strings either way.
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    records = []
    for idx, row in df.iterrows():
        records.append(
            {
                "ticker": ticker,
                "price_date": idx.date() if hasattr(idx, "date") else idx,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "adj_close": float(row["Adj Close"]),
                "volume": int(row["Volume"]),
            }
        )
    return records


def upsert_records(conn_str: str, records: list[dict]) -> int:
    if not records:
        return 0

    columns = ["ticker", "price_date", "open", "high", "low", "close", "adj_close", "volume"]
    values = [[r[c] for c in columns] for r in records]

    query = f"""
        INSERT INTO raw.stock_prices ({", ".join(columns)})
        VALUES %s
        ON CONFLICT (ticker, price_date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            adj_close = EXCLUDED.adj_close,
            volume = EXCLUDED.volume,
            loaded_at = now()
    """

    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)
        conn.commit()

    return len(records)


def main() -> None:
    conn_str = os.environ["FINDATA_DB_CONN"]
    total = 0
    for ticker in get_tickers():
        df = download_prices(ticker)
        records = to_records(df, ticker)
        total += upsert_records(conn_str, records)
        print(f"{ticker}: upserted {len(records)} rows")
    print(f"Done. {total} rows upserted total.")


if __name__ == "__main__":
    main()
