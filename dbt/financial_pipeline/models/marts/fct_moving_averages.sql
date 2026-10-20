-- 20/50-day simple moving averages of the close price per ticker.
-- Early rows (fewer than 20/50 days of history yet) get a partial-window
-- average rather than null — that's a deliberate choice, not a bug: call it
-- out if you'd rather these be null until the full window is available.

with prices as (
    select * from {{ ref('stg_prices') }}
)

select
    ticker,
    price_date,
    close_price,
    avg(close_price) over (
        partition by ticker order by price_date
        rows between 19 preceding and current row
    ) as ma_20,
    avg(close_price) over (
        partition by ticker order by price_date
        rows between 49 preceding and current row
    ) as ma_50
from prices
