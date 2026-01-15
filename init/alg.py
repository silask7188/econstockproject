import pandas as pd
import yfinance as yf
import random
import os

# --- CONFIGURATION ---
INPUT_FILE = "tickers.csv"
OUTPUT_FILE = "../final_portfolio.csv"
TARGET_TOTAL = 500000.00


def solve_weighted_csv():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Reading {INPUT_FILE}...")

    # 1. Read CSV (No Header expected: Symbol, Weight)
    # If a weight is missing, it defaults to 1.0
    try:
        input_df = pd.read_csv(INPUT_FILE, header=None, names=['SYMBOL', 'WEIGHT'])
        input_df['WEIGHT'] = input_df['WEIGHT'].fillna(1.0)
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return

    tickers = input_df['SYMBOL'].tolist()
    print(f"Fetching live prices for {len(tickers)} stocks...")

    # 2. Fetch Live Data
    try:
        # Batch fetch is faster
        yf_tickers = yf.Tickers(' '.join(tickers))

        data_list = []
        for index, row in input_df.iterrows():
            sym = row['SYMBOL']
            weight = row['WEIGHT']

            try:
                # Fast info fetch
                price = yf_tickers.tickers[sym].fast_info['last_price']

                # Try to get dividend yield (optional, but good for DB)
                try:
                    info = yf_tickers.tickers[sym].info
                    div = info.get('dividendYield', 0)
                except:
                    div = 0

                data_list.append({
                    'SYMBOL': sym,
                    'Current_Price': round(price, 2),
                    'Weight_Factor': weight,
                    'DIVIDEND': div
                })
            except Exception as e:
                print(f"Warning: Could not fetch price for {sym}. Skipping.")

    except Exception as e:
        print(f"Critical API Error: {e}")
        return

    df = pd.DataFrame(data_list)

    # 3. CALCULATE WEIGHTED ALLOCATION
    # Math: (Individual_Weight / Total_Weights) * $500,000
    total_weight_score = df['Weight_Factor'].sum()

    df['Allocated_Cash'] = (df['Weight_Factor'] / total_weight_score) * TARGET_TOTAL

    # Initial share count (rounded down)
    df['AMOUNT'] = (df['Allocated_Cash'] // df['Current_Price']).astype(int)

    # Prepare Solver Dictionary
    portfolio = {}
    for _, row in df.iterrows():
        portfolio[row['SYMBOL']] = {
            'price': row['Current_Price'],
            'count': int(row['AMOUNT']),
            'weight': row['Weight_Factor'],
            'dividend': row['DIVIDEND']
        }

    print("Baseline calculated based on your weights. Solving for exact $500,000.00...")

    # 4. THE SOLVER (Exact Matcher)
    steps = 0
    max_steps = 3000000

    while steps < max_steps:
        current_total = sum(p['price'] * p['count'] for p in portfolio.values())
        remainder = round(TARGET_TOTAL - current_total, 2)

        if remainder == 0.00:
            print(f"\nSUCCESS! Exact match found.")
            break

        # Pick random stock to adjust
        ticker_a = random.choice(list(portfolio.keys()))
        price_a = portfolio[ticker_a]['price']

        if remainder > 0:
            if price_a <= remainder:
                portfolio[ticker_a]['count'] += 1
            else:
                # Swap (Sell B, Buy A)
                ticker_b = random.choice(list(portfolio.keys()))
                if ticker_b != ticker_a and portfolio[ticker_b]['count'] > 1:
                    portfolio[ticker_b]['count'] -= 1
                    portfolio[ticker_a]['count'] += 1

        elif remainder < 0:
            if portfolio[ticker_a]['count'] > 1:
                portfolio[ticker_a]['count'] -= 1

        steps += 1
        if steps % 500000 == 0:
            print(f"Optimizing... (${current_total:,.2f})")

    # 5. EXPORT
    results = []
    for ticker, data in portfolio.items():
        results.append({
            'SYMBOL': ticker,
            'PRICEPER': data['price'],
            'AMOUNT': data['count'],
            'TOTAL': round(data['price'] * data['count'], 2),
            'DIVIDEND': data['dividend']
        })

    final_df = pd.DataFrame(results).sort_values('TOTAL', ascending=False)

    print("-" * 50)
    print(final_df[['SYMBOL', 'PRICEPER', 'AMOUNT', 'TOTAL']])
    print("-" * 50)
    print(f"FINAL SUM: ${final_df['TOTAL'].sum():,.2f}")

    if round(final_df['TOTAL'].sum(), 3) == 500000.00:
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved to: {OUTPUT_FILE}")
    else:
        print("Error: Math did not align. Try running again.")


if __name__ == "__main__":
    solve_weighted_csv()