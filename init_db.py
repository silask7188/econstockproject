import pandas as pd
from app import app, db, Portfolio, Holding, Transaction, PortfolioHistory
import os
from datetime import datetime

# CONFIGURATION
CSV_FILE = "final_portfolio.csv"
DB_FILE = "stock_data.db"
FEE_PER_TRANSACTION = 10.00  # <--- FLAT FEE PER STOCK BOUGHT


def init_database():
    print("🚀 Starting Database Initialization...")

    if os.path.exists(DB_FILE):
        print(f"⚠️  Found existing {DB_FILE}. Deleting it...")
        os.remove(DB_FILE)

    with app.app_context():
        db.create_all()
        
        if not os.path.exists(CSV_FILE):
            print(f"❌ CRITICAL ERROR: {CSV_FILE} not found!")
            return

        try:
            df = pd.read_csv(CSV_FILE)
            df.columns = df.columns.str.strip()
            print(f"📂 Loaded {len(df)} rows from {CSV_FILE}.")
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return

        # --- CALCULATE TOTALS ---
        total_assets_value = df['TOTAL'].sum()
        
        # New Fee Logic: $10 per Ticker (per row in CSV)
        total_fees_paid = len(df) * FEE_PER_TRANSACTION
        
        target_investment = 500000.00
        cost_basis = total_assets_value + total_fees_paid
        cash_balance = target_investment - cost_basis
        
        # Net Worth = Assets + Cash (Fees are gone/spent)
        starting_net_worth = total_assets_value + cash_balance

        # --- CREATE PORTFOLIO ---
        p = Portfolio(
            cash_balance=cash_balance,
            total_net_worth=starting_net_worth,
            last_updated=datetime.now()
        )
        db.session.add(p)
        print(f"💰 Portfolio initialized.")
        print(f"   - Assets:   ${total_assets_value:,.2f}")
        print(f"   - Fees Pd:  ${total_fees_paid:,.2f} ({len(df)} trades)")
        print(f"   - Cash:     ${cash_balance:.2f}")

        # --- PROCESS HOLDINGS ---
        for _, row in df.iterrows():
            ticker = row['SYMBOL']
            qty = int(row['AMOUNT'])
            price = float(row['PRICEPER'])
            total_val = float(row['TOTAL'])
            div_yield = float(row['DIVIDEND'])

            h = Holding(
                ticker=ticker,
                quantity=qty,
                average_buy_price=price,
                current_price=price,
                dividend_yield=div_yield
            )
            db.session.add(h)

            t = Transaction(
                ticker=ticker,
                transaction_type="BUY (INIT)",
                amount_shares=qty,
                price_per_share=price,
                total_value=total_val,
                timestamp=datetime.now()
            )
            db.session.add(t)

        # --- INITIAL HISTORY ---
        hist = PortfolioHistory(
            date=datetime.now(),
            cash_balance=cash_balance,
            assets_value=total_assets_value,
            total_value=starting_net_worth
        )
        db.session.add(hist)

        db.session.commit()
        print(f"✨ SUCCESS! Database built.")

if __name__ == "__main__":
    init_database()
