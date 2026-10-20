-- One row per (ticker, date) with the day-over-day simple return.
-- LAG() looks at the previous row within the same ticker's own date order —
-- a window function, not a join, so there's no risk of ticker rows crossing.

with prices as (
    select * from {{ ref('stg_prices') }}
),

with_prev_close as (
    select
        *,
        lag(close_price) over (
            partition by ticker order by price_date
        ) as prev_close_price
    from prices
)

select
    ticker,
    price_date,
    close_price,
    prev_close_price,
    round(
        (close_price - prev_close_price) / nullif(prev_close_price, 0),
        6
    ) as daily_return
from with_prev_close
