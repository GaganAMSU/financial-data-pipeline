import pandas as pd

from ingestion.fetch_prices import get_tickers, to_records


def test_get_tickers_parses_and_normalizes(monkeypatch):
    monkeypatch.setenv("TICKERS", " aapl, msft ,, tsla")
    assert get_tickers() == ["AAPL", "MSFT", "TSLA"]


def test_get_tickers_default(monkeypatch):
    monkeypatch.delenv("TICKERS", raising=False)
    assert "AAPL" in get_tickers()


def test_to_records_empty_frame_returns_empty_list():
    assert to_records(pd.DataFrame(), "AAPL") == []


def test_to_records_shapes_rows_correctly():
    df = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Adj Close": [104.0],
            "Volume": [1_000_000],
        },
        index=pd.to_datetime(["2026-01-02"]),
    )

    records = to_records(df, "AAPL")

    assert len(records) == 1
    row = records[0]
    assert row["ticker"] == "AAPL"
    assert row["price_date"].isoformat() == "2026-01-02"
    assert row["close"] == 104.0
    assert row["volume"] == 1_000_000
