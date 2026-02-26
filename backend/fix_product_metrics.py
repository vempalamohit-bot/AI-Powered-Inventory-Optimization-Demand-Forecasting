"""Scale product metrics to realistic levels after quantity_sold downscaling."""
import sqlite3, time

conn = sqlite3.connect('inventory.db', timeout=60)
conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA cache_size=-200000')
c = conn.cursor()

# Step 1: Compute avg daily demand per product into Python dict
print('Step 1: Computing avg daily demand per product...')
start = time.time()
c.execute("""
    SELECT product_id, SUM(quantity_sold) * 1.0 / 90 as avg_demand
    FROM sales_history
    WHERE date >= datetime('now', '-90 days')
    GROUP BY product_id
""")
demand_map = {row[0]: row[1] for row in c.fetchall()}
print(f"  Computed for {len(demand_map)} products in {time.time()-start:.1f}s")

# Step 2: Get all product IDs and their lead_time_days, current_stock
print('Step 2: Reading product data...')
c.execute("SELECT id, lead_time_days, current_stock FROM products")
products = c.fetchall()
print(f"  Read {len(products)} products")

# Step 3: Batch update using executemany
print('Step 3: Batch updating all product metrics...')
start = time.time()
updates = []
for pid, lead_time, stock in products:
    demand = demand_map.get(pid, 0.1)
    reorder_pt = round(demand * lead_time * 1.2)
    safety = round(demand * lead_time * 0.3)
    weeks_supply = round(stock / (demand * 7), 1) if demand > 0 else 0
    turnover = round(demand * 365 / stock, 2) if stock > 0 else 0
    
    if stock == 0:
        status = 'out_of_stock'
    elif stock <= reorder_pt:
        status = 'low_stock'
    elif stock > demand * 120:
        status = 'overstock'
    else:
        status = 'in_stock'
    
    updates.append((demand, reorder_pt, safety, weeks_supply, turnover, status, pid))

c.executemany("""
    UPDATE products SET
        average_daily_demand = ?,
        reorder_point = ?,
        safety_stock = ?,
        weeks_of_supply = ?,
        inventory_turnover = ?,
        stock_status = ?
    WHERE id = ?
""", updates)
print(f"  Updated {len(updates)} products in {time.time()-start:.1f}s")

conn.commit()
print("  Committed.")

# Verify
c.execute("""SELECT AVG(average_daily_demand), AVG(current_stock), AVG(reorder_point),
    AVG(weeks_of_supply), AVG(inventory_turnover) FROM products WHERE current_stock > 0""")
row = c.fetchone()
print(f"\nResults (in-stock products):")
print(f"  Avg daily demand: {row[0]:.2f} units")
print(f"  Avg stock: {row[1]:.0f} units")
print(f"  Avg reorder point: {row[2]:.0f} units")
print(f"  Avg weeks of supply: {row[3]:.1f}")
print(f"  Avg inventory turnover: {row[4]:.2f}")

c.execute("SELECT stock_status, COUNT(*) FROM products GROUP BY stock_status")
print("\nStock status distribution:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
print("\nDone!")
