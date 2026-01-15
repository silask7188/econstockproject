import pandas as pd
import yfinance as yf
import time


def fetch_metrics(input_csv, output_csv):
    # 1. Read the symbols from your current list
    try:
        df = pd.read_csv(input_csv)
        # Clean column names and symbols
        df.columns = df.columns.str.strip()
        symbols = df['SYMBOL'].astype(str).str.strip().tolist()
    except Exception as e:
        print(f"Error reading {input_csv}: {e}")
        return

    print(f"Gathering deep metrics for {len(symbols)} stocks... please wait.")
    print("This may take 30-60 seconds to avoid rate limits.\n")

    data_list = []

    # 2. Fetch data
    for sym in symbols:
        try:
            print(f"Fetching: {sym}...")
            ticker = yf.Ticker(sym)
            info = ticker.info

            # Extract key metrics safely (handle missing data with defaults)
            data_list.append({
                'SYMBOL': sym,
                'Current_Price': info.get('currentPrice', 0),
                'Market_Cap': info.get('marketCap', 0),
                'PE_Ratio': info.get('trailingPE', 0),
                'Dividend_Yield': info.get('dividendYield', 0),  # 0.05 = 5%
                'Beta': info.get('beta', 1.0),  # Volatility (1.0 is market avg)
                '52W_High': info.get('fiftyTwoWeekHigh', 0),
                '52W_Low': info.get('fiftyTwoWeekLow', 0),
                'Profit_Margin': info.get('profitMargins', 0)
            })

            # Sleep briefly to be nice to the API
            time.sleep(0.5)

        except Exception as e:
            print(f"Could not fetch {sym}: {e}")

    # 3. Save to new CSV
    metrics_df = pd.DataFrame(data_list)
    metrics_df.to_csv(output_csv, index=False)

    print(f"\nDone! Data saved to '{output_csv}'.")
    print("Please upload/paste the content of that file so I can analyze it.")


if __name__ == "__main__":
    fetch_metrics("data.csv", "stock_metrics.csv")