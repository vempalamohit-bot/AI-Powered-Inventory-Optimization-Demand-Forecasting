import sqlite3
conn = sqlite3.connect('backend/inventory.db')
c = conn.cursor()

# Get existing columns
c.execute('PRAGMA table_info(products)')
existing_cols = {r[1] for r in c.fetchall()}
print(f'Existing product columns: {len(existing_cols)}')

# All columns that SQLAlchemy model expects but CSV doesn't have
missing_cols = {
    'created_at': 'DATETIME',
    'description': 'TEXT',
}

for col, typ in missing_cols.items():
    if col not in existing_cols:
        try:
            c.execute(f'ALTER TABLE products ADD COLUMN {col} {typ}')
            print(f'Added products.{col}')
        except Exception as e:
            print(f'products.{col}: {e}')

# Set default value for created_at
c.execute("UPDATE products SET created_at = '2024-01-01 00:00:00' WHERE created_at IS NULL")
conn.commit()
print(f'Updated created_at for {c.rowcount} rows')

# Check sales_history columns
c.execute('PRAGMA table_info(sales_history)')
sales_cols = {r[1] for r in c.fetchall()}
print(f'Existing sales columns: {len(sales_cols)}')

# Sales columns from SQLAlchemy model
sales_missing = {
    'unit_price_at_sale': 'REAL',
    'unit_cost_at_sale': 'REAL', 
    'profit_loss_amount': 'REAL',
    'profit_margin_pct': 'REAL',
    'discount_applied': 'REAL',
    'transaction_type': 'VARCHAR(20)',
    'promotion_id': 'VARCHAR(50)',
    'sales_channel': 'VARCHAR(20)',
    'customer_id': 'VARCHAR(50)',
    'region': 'VARCHAR(50)',
}

for col, typ in sales_missing.items():
    if col not in sales_cols:
        try:
            c.execute(f'ALTER TABLE sales_history ADD COLUMN {col} {typ}')
            print(f'Added sales_history.{col}')
        except Exception as e:
            print(f'sales_history.{col}: {e}')

conn.commit()

# Verify
c.execute('PRAGMA table_info(products)')
final_cols = [r[1] for r in c.fetchall()]
print(f'\nFinal product columns ({len(final_cols)}): {final_cols}')

c.execute('PRAGMA table_info(sales_history)')
final_sales_cols = [r[1] for r in c.fetchall()]
print(f'Final sales columns ({len(final_sales_cols)}): {final_sales_cols}')

c.execute('SELECT COUNT(*) FROM products')
print(f'Products: {c.fetchone()[0]:,}')
c.execute('SELECT COUNT(*) FROM sales_history')
print(f'Sales: {c.fetchone()[0]:,}')

conn.close()
print('Done!')
