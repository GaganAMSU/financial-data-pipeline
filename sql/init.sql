-- Runs once, automatically, the first time the postgres container starts
-- (mounted into /docker-entrypoint-initdb.d/). Creates a second database so
-- Airflow's own metadata is never mixed with our pipeline's data.

CREATE DATABASE findata;

\c findata

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.stock_prices (
    ticker      TEXT NOT NULL,
    price_date  DATE NOT NULL,
    open        NUMERIC(14, 4),
    high        NUMERIC(14, 4),
    low         NUMERIC(14, 4),
    close       NUMERIC(14, 4),
    adj_close   NUMERIC(14, 4),
    volume      BIGINT,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, price_date)
);
