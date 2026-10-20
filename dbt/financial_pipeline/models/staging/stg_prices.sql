-- Thin cleaning layer: rename/cast raw columns, nothing analytical here.
-- Marts build on this instead of touching raw.stock_prices directly so that
-- any future column renames in the source only need to be fixed in one place.

select
    ticker,
    price_date,
    open::numeric       as open_price,
    high::numeric        as high_price,
    low::numeric         as low_price,
    close::numeric       as close_price,
    adj_close::numeric   as adj_close_price,
    volume::bigint       as volume
from {{ source('raw', 'stock_prices') }}
