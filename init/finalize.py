import pandas as pd
import math

# 1. The List of 20 Winners
TARGET_TICKERS = [
    'MSFT', 'AAPL', 'NVDA', 'GOOGL', 'AMZN',  # The Giants
    'JNJ', 'KO', 'PG', 'JPM', 'CVX',  # The Dividend Kings
    'STRL', 'AMBA', 'CROX', 'HALO',  # The Mid-Cap Growth
    'BLBD', 'PL', 'TGTX', 'SITM',  # The Small-Cap Volatility
    'BITF', 'DTST'  # The Penny/Crypto Proxies
]


def generate_final_csv(input_csv, output_csv):
    # Load your fresh data
    df = pd.read_csv(input_csv)
    df.columns = df.columns.str.strip()

    # Filter for only our target 20 stocks
    df = df[df['SYMBOL'].isin(TARGET_TICKERS)].copy()

    # Configuration
    TOTAL_CAPITAL = 500000.00
    TARGET_PER_STOCK = TOTAL_CAPITAL / len(TARGET_TICKERS)  # $25,000

    print(f"Allocating ${TARGET_PER_STOCK:,.2f} to each of the {len(df)} stocks...")

    # Calculate Shares and Totals
    # We use floor() to buy whole shares only
    df['AMOUNT'] = (TARGET_PER_STOCK / df['Current_Price']).apply(math.floor).astype(int)
    df['TOTAL'] = df['AMOUNT'] * df['Current_Price']

    # Rename columns to match your desired format
    # MAPPING: SYMBOL, PRICEPER, AMOUNT, TOTAL, DIVIDEND
    final_df = df[['SYMBOL', 'Current_Price', 'AMOUNT', 'TOTAL', 'Dividend_Yield']].copy()
    final_df.columns = ['SYMBOL', 'PRICEPER', 'AMOUNT', 'TOTAL', 'DIVIDEND']

    # Formatting fixes
    # 1. Round prices/totals to 2 decimals
    final_df['PRICEPER'] = final_df['PRICEPER'].round(2)
    final_df['TOTAL'] = final_df['TOTAL'].round(2)

    # 2. Save
    final_df.to_csv(output_csv, index=False)

    # Summary
    total_invested = final_df['TOTAL'].sum()
    cash_leftover = TOTAL_CAPITAL - total_invested

    print("-" * 40)
    print(final_df)
    print("-" * 40)
    print(f"Total Invested: ${total_invested:,.2f}")
    print(f"Cash Leftover:  ${cash_leftover:,.2f}")
    print(f"Saved to: {output_csv}")


if __name__ == "__main__":
    generate_final_csv("stock_metrics.csv", "final_portfolio.csv")