import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///inventory.db')
with engine.connect() as conn:
    rows = conn.execute(text("SELECT date, quantity_sold FROM sales_history WHERE product_id = 9 ORDER BY date")).fetchall()
    df = pd.DataFrame(rows, columns=["date", "quantity_sold"])
    df["date"] = pd.to_datetime(df["date"])
    
    # Weekly aggregation
    df["week"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
    weekly = df.groupby("week")["quantity_sold"].sum().reset_index()
    weekly.columns = ["date", "qty"]
    
    # Fill missing weeks
    full_weeks = pd.date_range(start=weekly["date"].min(), end=weekly["date"].max(), freq="W-MON")
    weekly = weekly.set_index("date").reindex(full_weeks, fill_value=0).reset_index()
    weekly.columns = ["date", "qty"]
    
    non_zero = (weekly["qty"] > 0).sum()
    total_w = len(weekly)
    
    print(f"Product 9: {len(df)} sales days, {total_w} total weeks")
    print(f"Non-zero weeks: {non_zero} / {total_w} ({non_zero/total_w*100:.1f}%)")
    print(f"Weekly qty: mean={weekly['qty'].mean():.1f}, std={weekly['qty'].std():.1f}, min={weekly['qty'].min()}, max={weekly['qty'].max()}")
    print()
    print("Last 30 weeks:")
    for _, row in weekly.tail(30).iterrows():
        bar = "#" * min(int(row["qty"]), 40)
        print(f"  {row['date'].strftime('%Y-%m-%d')}  {row['qty']:5.0f}  {bar}")
