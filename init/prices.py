import pandas as pd
import yfinance as yf


def get_current_prices(csv_file):
    # 1. Read the CSV
    try:
        df = pd.read_csv(csv_file)
        # Ensure column names are stripped of whitespace
        df.columns = df.columns.str.strip()
    except FileNotFoundError:
        print(f"Error: Could not find {csv_file}")
        return

    # 2. Extract unique symbols
    symbols = df['SYMBOL'].unique().tolist()

    print(f"Fetching prices for: {', '.join(symbols)}\n")
    print(f"{'SYMBOL':<10} | {'CURRENT PRICE':<15}")
    print("-" * 30)

    # 3. Fetch prices efficiently
    # Using Tickers object allows yfinance to optimize connection sharing
    tickers = yf.Tickers(' '.join(symbols))

    for symbol in symbols:
        try:
            # fast_info is much faster than .info as it fetches less data
            price = tickers.tickers[symbol].fast_info['last_price']
            print(f"{symbol:<10} | ${price:,.2f}")
        except Exception as e:
            print(f"{symbol:<10} | ERROR (Not found)")


if __name__ == "__main__":
    get_current_prices("data.csv")