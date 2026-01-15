import pandas as pd
import yfinance as yf
import random
import os

# --- CONFIGURATION ---
INPUT_FILE = "tickers.csv"
OUTPUT_FILE = "final_portfolio.csv" # Saved in current folder for safety
GRAND_TOTAL = 500000.00
FEE_PER_TRANSACTION = 10.00  # Flat fee per stock ticker


def solve_weighted_csv():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Reading {INPUT_FILE}...")

    # 1. Read CSV
    try:
        input_df = pd.read_csv(INPUT_FILE, header=None, names=['SYMBOL', 'WEIGHT'])
        input_df['WEIGHT'] = input_df['WEIGHT'].fillna(1.0)
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return

    tickers = input_df['SYMBOL'].tolist()
    num_stocks = len(tickers)
    
    # 2. CALCULATE BUDGET
    total_fees = num_stocks * FEE_PER_TRANSACTION
    target_stock_value = GRAND_TOTAL - total_fees
    
    print(f"--- BUDGET BREAKDOWN ---")
    print(f"Grand Total:   ${GRAND_TOTAL:,.2f}")
    print(f"Transaction Fees: -${total_fees:,.2f} ({num_stocks} stocks @ ${FEE_PER_TRANSACTION}/trade)")
    print(f"Net Stock Budget:  ${target_stock_value:,.2f}")
    print(f"------------------------")

    print(f"Fetching live prices for {num_stocks} stocks...")

    # 3. Fetch Live Data
    try:
        yf_tickers = yf.Tickers(' '.join(tickers))
        data_list = []

        for index, row in input_df.iterrows():
            sym = row['SYMBOL']
            weight = row['WEIGHT']
            try:
                # Get Market Price
                price = yf_tickers.tickers[sym].fast_info['last_price']
                
                # Try to get dividend yield
                try:
                    info = yf_tickers.tickers[sym].info
                    div = info.get('dividendYield', 0)
                except:
                    div = 0

                data_list.append({
                    'SYMBOL': sym,
                    'Market_Price': round(price, 2),
                    'Weight_Factor': weight,
                    'DIVIDEND': div
                })
            except Exception as e:
                print(f"Warning: Could not fetch price for {sym}. Skipping.")

    except Exception as e:
        print(f"Critical API Error: {e}")
        return

    df = pd.DataFrame(data_list)

    # 4. INITIAL ALLOCATION
    total_weight_score = df['Weight_Factor'].sum()
    df['Allocated_Cash'] = (df['Weight_Factor'] / total_weight_score) * target_stock_value
    df['AMOUNT'] = (df['Allocated_Cash'] // df['Market_Price']).astype(int)

    # Prepare Solver Dictionary
    portfolio = {}
    for _, row in df.iterrows():
        portfolio[row['SYMBOL']] = {
            'price': row['Market_Price'],
            'count': int(row['AMOUNT']),
            'weight': row['Weight_Factor'],
            'dividend': row['DIVIDEND']
        }

    print(f"Solving for exact Net Stock Value: ${target_stock_value:,.2f}...")

    # 5. THE SOLVER
    steps = 0
    max_steps = 5000000

    while steps < max_steps:
        # Calculate Current Stock Value
        current_stock_val = sum(p['price'] * p['count'] for p in portfolio.values())
        remainder = round(target_stock_value - current_stock_val, 2)

        if remainder == 0.00:
            print(f"\nSUCCESS! Exact match found.")
            break

        ticker_a = random.choice(list(portfolio.keys()))
        price_a = portfolio[ticker_a]['price']

        if remainder > 0:
            if price_a <= remainder:
                portfolio[ticker_a]['count'] += 1
            else:
                # Swap logic
                ticker_b = random.choice(list(portfolio.keys()))
                if ticker_b != ticker_a and portfolio[ticker_b]['count'] > 1:
                    portfolio[ticker_b]['count'] -= 1
                    portfolio[ticker_a]['count'] += 1

        elif remainder < 0:
            if portfolio[ticker_a]['count'] > 1:
                portfolio[ticker_a]['count'] -= 1

        steps += 1
        if steps % 500000 == 0:
            print(f"Optimizing... (${current_stock_val:,.2f})")

    # 6. EXPORT
    results = []
    
    for ticker, data in portfolio.items():
        market_val = data['price'] * data['count']
        results.append({
            'SYMBOL': ticker,
            'PRICEPER': data['price'],
            'AMOUNT': data['count'],
            'TOTAL': round(market_val, 2),
            'DIVIDEND': data['dividend']
        })

    final_df = pd.DataFrame(results).sort_values('TOTAL', ascending=False)
    final_stock_sum = final_df['TOTAL'].sum()
    grand_total_check = final_stock_sum + total_fees

    print("-" * 50)
    print(final_df[['SYMBOL', 'PRICEPER', 'AMOUNT', 'TOTAL']].head(10))
    print("-" * 50)
    print(f"NET STOCK VALUE: ${final_stock_sum:,.2f}")
    print(f"FEES PAID      : ${total_fees:,.2f}")
    print(f"GRAND TOTAL    : ${grand_total_check:,.2f}")

    if round(grand_total_check, 2) == GRAND_TOTAL:
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved to: {OUTPUT_FILE}")
    else:
        print("\nError: Could not solve. Try again.")

if __name__ == "__main__":
    solve_weighted_csv()
