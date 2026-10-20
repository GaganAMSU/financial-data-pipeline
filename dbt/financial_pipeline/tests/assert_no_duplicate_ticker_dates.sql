-- A "singular" dbt test: any SQL file in tests/ that returns zero rows
-- passes, any row returned is treated as a failure. This one guards the
-- (ticker, price_date) grain that every mart in this project assumes.

select ticker, price_date, count(*) as n
from {{ ref('stg_prices') }}
group by ticker, price_date
having count(*) > 1
