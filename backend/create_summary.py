import sqlite3
import time

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

print('Creating daily summary table for instant dashboard...')
start = time.time()

cursor.execute('DROP TABLE IF EXISTS daily_sales_summary')

cursor.execute('''
    CREATE TABLE daily_sales_summary AS
    SELECT 
        date(date) as sale_date,
        SUM(quantity_sold) as total_quantity,
        SUM(COALESCE(revenue, quantity_sold * 10)) as total_revenue,
        SUM(quantity_sold * COALESCE(unit_cost_at_sale, 5)) as total_cost,
        SUM(CASE WHEN profit_loss_amount < 0 THEN ABS(profit_loss_amount) ELSE 0 END) as total_loss,
        COUNT(*) as transaction_count
    FROM sales_history
    GROUP BY date(date)
''')
conn.commit()

cursor.execute('CREATE INDEX idx_daily_summary_date ON daily_sales_summary(sale_date)')
conn.commit()

count = cursor.execute('SELECT COUNT(*) FROM daily_sales_summary').fetchone()[0]
print(f'Created summary table with {count} days')
print(f'Time: {time.time()-start:.1f}s')

start = time.time()
result = cursor.execute("SELECT sale_date, total_quantity, total_revenue FROM daily_sales_summary ORDER BY sale_date DESC LIMIT 30").fetchall()
print(f'Summary query took {time.time()-start:.3f}s')
print(f'Rows: {len(result)}')

conn.close()
