"""
Generate dense, realistic sales data for products 1-50 with DIVERSE demand patterns.

Goal: Each product should hit a DIFFERENT demand segment in the segmenter:
- STABLE_FLAT: Low CV, no seasonality, no trend  -> Decomposition / Holt-Winters
- STABLE_TRENDING: Low CV, clear upward/downward trend -> Holt-Winters
- SEASONAL_STABLE: Strong seasonal pattern, low noise -> SARIMA
- SEASONAL_VOLATILE: Strong seasonal + high noise -> Decomposition
- VOLATILE: High CV, random spikes -> XGBoost / Decomposition
- INTERMITTENT: Many zero-sales days -> Seasonal Naive

Includes:
- Day-of-week patterns (weekday vs weekend)
- Monthly/quarterly seasonality curves
- Event spikes (Black Friday, Christmas, Back-to-School, Prime Day, etc.)
- Trend lines (growing, declining, flat)
- Random noise calibrated per segment
"""
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

# Format: (base_daily, trend_pct_per_month, season_amplitude, noise_cv, segment_target)
PROFILES = {
    # ============ SEASONAL_STABLE (strong season, low noise) ============
    1:  (15, 0.0, 0.65, 0.15, 'SEASONAL_STABLE'),
    2:  (20, 0.0, 0.55, 0.18, 'SEASONAL_STABLE'),
    3:  (18, 0.1, 0.60, 0.15, 'SEASONAL_STABLE'),
    4:  (12, 0.0, 0.70, 0.12, 'SEASONAL_STABLE'),
    5:  (25, 0.0, 0.55, 0.16, 'SEASONAL_STABLE'),

    # ============ SEASONAL_VOLATILE (strong season, higher noise) ============
    6:  (14, 0.2, 0.60, 0.45, 'SEASONAL_VOLATILE'),
    7:  (10, -0.1, 0.55, 0.50, 'SEASONAL_VOLATILE'),
    8:  (16, 0.0, 0.65, 0.40, 'SEASONAL_VOLATILE'),
    9:  (20, 0.1, 0.50, 0.48, 'SEASONAL_VOLATILE'),
    10: (12, 0.0, 0.60, 0.42, 'SEASONAL_VOLATILE'),

    # ============ STABLE_FLAT (low CV, no seasonal, no trend) ============
    11: (22, 0.0, 0.05, 0.12, 'STABLE_FLAT'),
    12: (18, 0.0, 0.08, 0.10, 'STABLE_FLAT'),
    13: (30, 0.0, 0.05, 0.08, 'STABLE_FLAT'),
    14: (15, 0.0, 0.06, 0.14, 'STABLE_FLAT'),
    15: (10, 0.0, 0.07, 0.11, 'STABLE_FLAT'),

    # ============ STABLE_TRENDING (low CV, clear trend) ============
    16: (8,  1.5, 0.10, 0.15, 'STABLE_TRENDING'),
    17: (25, -0.8, 0.08, 0.14, 'STABLE_TRENDING'),
    18: (12, 1.0, 0.12, 0.16, 'STABLE_TRENDING'),
    19: (30, -0.5, 0.10, 0.13, 'STABLE_TRENDING'),
    20: (15, 2.0, 0.08, 0.12, 'STABLE_TRENDING'),

    # ============ VOLATILE (high CV, random spikes) ============
    21: (12, 0.0, 0.15, 0.70, 'VOLATILE'),
    22: (8,  0.2, 0.20, 0.80, 'VOLATILE'),
    23: (15, 0.0, 0.10, 0.65, 'VOLATILE'),
    24: (10, -0.1, 0.15, 0.75, 'VOLATILE'),
    25: (20, 0.0, 0.20, 0.70, 'VOLATILE'),

    # ============ INTERMITTENT (many zero-sales days) ============
    26: (5,  0.0, 0.20, 0.30, 'INTERMITTENT'),
    27: (3,  0.0, 0.15, 0.35, 'INTERMITTENT'),
    28: (8,  0.1, 0.25, 0.25, 'INTERMITTENT'),
    29: (4,  0.0, 0.10, 0.30, 'INTERMITTENT'),
    30: (6,  0.0, 0.20, 0.28, 'INTERMITTENT'),

    # ============ MIX for 31-50 ============
    31: (20, 0.3, 0.50, 0.18, 'SEASONAL_STABLE'),
    32: (14, 0.0, 0.05, 0.10, 'STABLE_FLAT'),
    33: (10, 1.2, 0.10, 0.14, 'STABLE_TRENDING'),
    34: (15, 0.0, 0.55, 0.45, 'SEASONAL_VOLATILE'),
    35: (8,  0.0, 0.12, 0.72, 'VOLATILE'),
    36: (4,  0.0, 0.15, 0.30, 'INTERMITTENT'),
    37: (22, 0.0, 0.60, 0.16, 'SEASONAL_STABLE'),
    38: (18, -0.6, 0.08, 0.13, 'STABLE_TRENDING'),
    39: (12, 0.0, 0.60, 0.48, 'SEASONAL_VOLATILE'),
    40: (28, 0.0, 0.04, 0.09, 'STABLE_FLAT'),
    41: (16, 0.5, 0.55, 0.17, 'SEASONAL_STABLE'),
    42: (10, 0.0, 0.10, 0.68, 'VOLATILE'),
    43: (6,  0.0, 0.20, 0.32, 'INTERMITTENT'),
    44: (20, 1.5, 0.12, 0.15, 'STABLE_TRENDING'),
    45: (14, 0.0, 0.55, 0.42, 'SEASONAL_VOLATILE'),
    46: (25, 0.0, 0.06, 0.11, 'STABLE_FLAT'),
    47: (18, 0.0, 0.65, 0.14, 'SEASONAL_STABLE'),
    48: (8,  0.0, 0.15, 0.75, 'VOLATILE'),
    49: (5,  0.0, 0.10, 0.28, 'INTERMITTENT'),
    50: (12, -1.0, 0.08, 0.12, 'STABLE_TRENDING'),
}


def generate_events_calendar(start_date, end_date):
    events = {}
    for year in range(start_date.year, end_date.year + 1):
        nov1 = datetime(year, 11, 1)
        first_fri = nov1 + timedelta(days=(4 - nov1.weekday()) % 7)
        black_friday = first_fri + timedelta(weeks=3)
        event_list = [
            (datetime(year, 1, 1), 3, 1.4),
            (datetime(year, 2, 10), 5, 1.3),
            (datetime(year, 3, 15), 3, 1.2),
            (datetime(year, 5, 1), 5, 1.25),
            (datetime(year, 6, 15), 3, 1.15),
            (datetime(year, 7, 15), 5, 1.40),
            (datetime(year, 8, 15), 7, 1.35),
            (datetime(year, 9, 1), 3, 1.2),
            (datetime(year, 10, 25), 3, 1.25),
            (black_friday - timedelta(days=1), 4, 2.0),
            (datetime(year, 12, 1), 10, 1.5),
            (datetime(year, 12, 15), 10, 1.8),
            (datetime(year, 12, 26), 5, 1.3),
        ]
        for evt_start, duration, multiplier in event_list:
            for d in range(duration):
                evt_date = evt_start + timedelta(days=d)
                if start_date <= evt_date <= end_date:
                    key = evt_date.strftime('%Y-%m-%d')
                    events[key] = max(events.get(key, 1.0), multiplier)
    return events


def monthly_seasonality(month_frac, amplitude):
    theta = 2 * np.pi * (month_frac - 0.5) / 12.0
    raw = np.cos(theta - 2 * np.pi * 11.0 / 12.0)
    return 1.0 + amplitude * raw


def dow_pattern(dow):
    return [1.10, 1.08, 1.05, 1.08, 1.15, 0.85, 0.60][dow]


def generate_product_sales(pid, profile, start_date, end_date, events, rng):
    base_demand, trend_pct, season_amp, noise_cv, target_segment = profile
    total_days = (end_date - start_date).days + 1
    records = []

    for day_offset in range(total_days):
        current = start_date + timedelta(days=day_offset)
        date_key = current.strftime('%Y-%m-%d')
        months_elapsed = day_offset / 30.44
        trend_mult = max(1.0 + (trend_pct / 100.0) * months_elapsed, 0.2)
        base = base_demand * trend_mult
        season_mult = monthly_seasonality(current.month + current.day / 30.0, season_amp)
        dow_mult = dow_pattern(current.weekday())
        event_mult = events.get(date_key, 1.0)

        # Noise per segment type
        if target_segment == 'VOLATILE':
            noise = rng.lognormal(0, noise_cv)
            if rng.random() < 0.05:
                noise *= rng.uniform(2.5, 5.0)
        elif target_segment in ('SEASONAL_VOLATILE',):
            noise = rng.lognormal(0, noise_cv)
        elif target_segment == 'INTERMITTENT':
            noise = rng.lognormal(0, noise_cv)
        else:
            noise = max(rng.normal(1.0, noise_cv), 0.3)

        # Intermittent zeros
        if target_segment == 'INTERMITTENT':
            zero_prob = 0.35 + 0.15 * max(0, 1 - season_mult)
            if rng.random() < zero_prob:
                records.append({'product_id': pid, 'date': date_key, 'quantity_sold': 0})
                continue
        else:
            if rng.random() < 0.02:
                records.append({'product_id': pid, 'date': date_key, 'quantity_sold': 0})
                continue

        daily = base * season_mult * dow_mult * event_mult * noise
        quantity = max(int(round(daily)), 1)
        records.append({'product_id': pid, 'date': date_key, 'quantity_sold': quantity})

    return records


def main():
    print("=" * 65)
    print("  Generating DIVERSE sales data for products 1-50")
    print("=" * 65)

    end_date = datetime(2026, 2, 26)
    start_date = datetime(2024, 2, 26)
    total_days = (end_date - start_date).days + 1
    print(f"  Date range: {start_date:%Y-%m-%d} -> {end_date:%Y-%m-%d} ({total_days} days)")

    events = generate_events_calendar(start_date, end_date)
    print(f"  Events calendar: {len(events)} event days")

    conn = sqlite3.connect(DB_PATH)
    products = {}
    for row in conn.execute("SELECT id, unit_price, unit_cost, category FROM products WHERE id <= 50"):
        products[row[0]] = {'unit_price': row[1] or 50.0, 'unit_cost': row[2] or 25.0, 'category': row[3]}
    print(f"  Products found: {len(products)}\n")

    old = conn.execute("SELECT COUNT(*) FROM sales_history WHERE product_id <= 50").fetchone()[0]
    conn.execute("DELETE FROM sales_history WHERE product_id <= 50")
    print(f"  Deleted {old:,} old records\n")

    rng = np.random.default_rng(seed=2026)
    all_records = []
    segment_counts = {}

    print(f"  {'ID':>3} {'Category':25} {'Segment':22} {'Recs':>5} {'Total':>7} {'Avg':>6} {'Zeros':>6}")
    print("  " + "-" * 90)

    for pid in range(1, 51):
        profile = PROFILES[pid]
        target_seg = profile[4]
        segment_counts[target_seg] = segment_counts.get(target_seg, 0) + 1
        records = generate_product_sales(pid, profile, start_date, end_date, events, rng)

        prod_info = products.get(pid, {'unit_price': 50.0, 'unit_cost': 25.0})
        for r in records:
            qty = r['quantity_sold']
            price = prod_info['unit_price'] * rng.uniform(0.95, 1.05)
            cost = prod_info['unit_cost']
            r['revenue'] = round(price * qty, 2)
            r['unit_price_at_sale'] = round(price, 2)
            r['unit_cost_at_sale'] = round(cost, 2)
            r['profit_loss_amount'] = round((price - cost) * qty, 2)

        all_records.extend(records)
        qtys = [r['quantity_sold'] for r in records]
        total_qty = sum(qtys)
        avg = total_qty / max(len(records), 1)
        zero_pct = sum(1 for q in qtys if q == 0) / len(qtys) * 100
        cat = products.get(pid, {}).get('category', '?')[:25]
        print(f"  {pid:3d} {cat:25} {target_seg:22} {len(records):5} {total_qty:7,} {avg:6.1f} {zero_pct:5.1f}%")

    max_id = conn.execute("SELECT MAX(id) FROM sales_history").fetchone()[0] or 0
    print(f"\n  Inserting {len(all_records):,} records...")

    df = pd.DataFrame(all_records)
    df.insert(0, 'id', range(max_id + 1, max_id + 1 + len(df)))
    for col in ['profit_margin_pct', 'discount_applied', 'transaction_type',
                'promotion_id', 'sales_channel', 'customer_id', 'region']:
        if col not in df.columns:
            df[col] = None
    df.to_sql('sales_history', conn, if_exists='append', index=False, chunksize=5000)

    # Realistic stock levels
    for pid in range(1, 51):
        base = PROFILES[pid][0]
        stock = int(base * rng.uniform(10, 28))
        conn.execute("UPDATE products SET current_stock=? WHERE id=?", (stock, pid))

    conn.commit()
    new_count = conn.execute("SELECT COUNT(*) FROM sales_history WHERE product_id <= 50").fetchone()[0]
    total_count = conn.execute("SELECT COUNT(*) FROM sales_history").fetchone()[0]

    print(f"\n  {'=' * 65}")
    print(f"  DONE! Products 1-50: {new_count:,} records | Total DB: {total_count:,}")
    print(f"\n  Segment distribution:")
    for seg, cnt in sorted(segment_counts.items()):
        print(f"    {seg:22}: {cnt} products")
    print(f"  {'=' * 65}")
    conn.close()


if __name__ == '__main__':
    main()
