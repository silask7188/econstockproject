import pandas as pd
from app import app, db, Portfolio, Holding, Transaction, PortfolioHistory
import os
from datetime import datetime

# CONFIGURATION
CSV_FILE = "final_portfolio.csv"
DB_FILE = "stock_data.db"


def init_database():
    print("🚀 Starting Database Initialization...")

    # 1. Clean Slate: Remove old DB if it exists
    if os.path.exists(DB_FILE):
        print(f"⚠️  Found existing {DB_FILE}. Deleting it...")
        os.remove(DB_FILE)

    # 2. Initialize within Flask Context
    with app.app_context():
        # Create the tables based on models.py
        db.create_all()
        print("✅ Database tables created successfully.")

        # 3. Load the CSV Data
        if not os.path.exists(CSV_FILE):
            print(f"❌ CRITICAL ERROR: {CSV_FILE} not found!")
            print("   Please run your portfolio solver script first.")
            return

        try:
            df = pd.read_csv(CSV_FILE)
            # Ensure columns are stripped of whitespace
            df.columns = df.columns.str.strip()
            print(f"📂 Loaded {len(df)} rows from {CSV_FILE}.")
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return

        # 4. Calculate Totals
        # The CSV has 'TOTAL' for each stock. Sum them up.
        total_assets_value = df['TOTAL'].sum()
        target_portfolio_value = 500000.00

        # Calculate leftover cash (likely 0.00 or very small)
        cash_balance = target_portfolio_value - total_assets_value

        # 5. Create Portfolio Record
        p = Portfolio(
            cash_balance=cash_balance,
            total_net_worth=target_portfolio_value,
            last_updated=datetime.now()
        )
        db.session.add(p)
        print(f"💰 Portfolio initialized. Cash: ${cash_balance:.2f} | Assets: ${total_assets_value:,.2f}")

        # 6. Process Holdings & Transactions
        print("📥 Importing Holdings...")

        for _, row in df.iterrows():
            ticker = row['SYMBOL']
            qty = int(row['AMOUNT'])
            price = float(row['PRICEPER'])
            total_val = float(row['TOTAL'])
            div_yield = float(row['DIVIDEND'])

            # A. Create Holding Entry
            h = Holding(
                ticker=ticker,
                quantity=qty,
                average_buy_price=price,
                current_price=price,  # Set current price to buy price initially
                dividend_yield=div_yield
            )
            db.session.add(h)

            # B. Create Transaction Log (The "Initial Buy")
            t = Transaction(
                ticker=ticker,
                transaction_type="BUY (INIT)",
                amount_shares=qty,
                price_per_share=price,
                total_value=total_val,
                timestamp=datetime.now()
            )
            db.session.add(t)

        # 7. Create Initial History Data Point (For the Chart)
        hist = PortfolioHistory(
            date=datetime.now(),
            cash_balance=cash_balance,
            assets_value=total_assets_value,
            total_value=target_portfolio_value
        )
        db.session.add(hist)

        # 8. Commit All Changes
        db.session.commit()
        print(f"✨ SUCCESS! Database built with {len(df)} positions.")
        print(f"   You can now run 'python app.py' to see your dashboard.")


if __name__ == "__main__":
    init_database()