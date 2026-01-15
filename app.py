from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import yfinance as yf
import io
import csv

# Initialize Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
from models import db, Portfolio, Holding, Transaction, PortfolioHistory, StockHistory

db.init_app(app)


# --- ROUTES ---

@app.route('/')
def dashboard():
    portfolio = Portfolio.query.first()
    holdings = Holding.query.all()
    # Sort by Total Value
    holdings.sort(key=lambda h: h.quantity * (h.current_price or h.average_buy_price), reverse=True)

    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(15).all()

    return render_template('dashboard.html',
                           portfolio=portfolio,
                           holdings=holdings,
                           transactions=transactions)


@app.route('/update_now')
def manual_update():
    """Trigger manual update from the button"""
    update_market_data()
    return redirect(url_for('dashboard'))


@app.route('/api/history')
def get_history_data():
    """
    Returns Portfolio History (Total Net Worth).
    FILTER: Returns only 1 data point per hour to keep graph clean.
    """
    history = PortfolioHistory.query.order_by(PortfolioHistory.date.asc()).all()

    hourly_data = {}
    for h in history:
        # Create a key for the specific hour (e.g., "2023-10-25 14")
        hour_key = h.date.strftime('%Y-%m-%d %H')

        # Only keep the first entry we see for this hour
        if hour_key not in hourly_data:
            hourly_data[hour_key] = {
                'x': h.date.strftime('%Y-%m-%d %H:00:00'),  # Force neat timestamp
                'y': h.total_value
            }

    # Convert dict back to list
    return jsonify(list(hourly_data.values()))


@app.route('/api/stock_history_json')
def get_stock_history_json():
    """
    Returns ALL stock history.
    FILTER: Returns only 1 data point per ticker per hour.
    """
    history = StockHistory.query.order_by(StockHistory.timestamp.asc()).all()

    hourly_data = {}

    for h in history:
        # Key = "2023-10-25 14" + "AAPL"
        hour_key = h.timestamp.strftime('%Y-%m-%d %H') + "_" + h.ticker

        if hour_key not in hourly_data:
            hourly_data[hour_key] = {
                'date': h.timestamp.strftime('%Y-%m-%d %H:00:00'),
                'ticker': h.ticker,
                'price': h.price
            }

    return jsonify(list(hourly_data.values()))


@app.route('/api/timestamps_csv')
def get_timestamps_csv():
    """
    Complex Endpoint: JSON keys are HOURLY timestamps.
    Values are CSV strings of that hour's snapshot.
    """
    days = request.args.get('days', type=int)
    query = StockHistory.query

    if days:
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(StockHistory.timestamp >= start_date)

    history = query.order_by(StockHistory.timestamp.asc()).all()

    # Group by Hourly Timestamp
    grouped = {}

    for h in history:
        # Round timestamp to the nearest hour string
        ts_hour = h.timestamp.strftime('%Y-%m-%d %H:00:00')

        # We need to ensure we don't have duplicates for the same ticker in the same hour
        # So we use a nested dictionary first: grouped[hour][ticker] = price
        if ts_hour not in grouped:
            grouped[ts_hour] = {}

        # Since we are looping ascending, this will keep the *first* price found for that hour
        # (Change to .desc() in query if you want the last price of the hour)
        if h.ticker not in grouped[ts_hour]:
            grouped[ts_hour][h.ticker] = h.price

    # Convert the nested dictionaries into CSV strings
    result = {}
    for ts, stocks_dict in grouped.items():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['SYMBOL', 'PRICE'])  # CSV Header

        # Write rows
        for ticker, price in stocks_dict.items():
            writer.writerow([ticker, price])

        result[ts] = output.getvalue()

    return jsonify(result)


# --- AUTOMATION ---

def update_market_data():
    with app.app_context():
        print(f"[{datetime.now()}] 🔄 Scanning Market...")
        portfolio = Portfolio.query.first()
        holdings = Holding.query.all()

        if not holdings: return

        # Fetch Live Data
        tickers_list = [h.ticker for h in holdings]
        try:
            ticker_str = " ".join(tickers_list)
            data = yf.Tickers(ticker_str)

            current_assets_value = 0.0
            timestamp = datetime.now()

            for h in holdings:
                try:
                    # Get new price
                    new_price = data.tickers[h.ticker].fast_info['last_price']

                    if new_price:
                        # Save old price to 'previous' before overwriting
                        if h.current_price:
                            h.previous_price = h.current_price
                        else:
                            h.previous_price = h.average_buy_price

                        h.current_price = new_price

                        # Add to StockHistory
                        sh = StockHistory(timestamp=timestamp, ticker=h.ticker, price=new_price)
                        db.session.add(sh)

                        current_assets_value += (new_price * h.quantity)
                except Exception as e:
                    print(f"   ⚠️ Error {h.ticker}: {e}")
                    current_assets_value += (h.current_price * h.quantity)

            # Update Portfolio
            portfolio.total_net_worth = portfolio.cash_balance + current_assets_value
            portfolio.last_updated = timestamp

            # Save Portfolio History
            ph = PortfolioHistory(
                date=timestamp,
                cash_balance=portfolio.cash_balance,
                assets_value=current_assets_value,
                total_value=portfolio.total_net_worth
            )
            db.session.add(ph)
            db.session.commit()
            print(f"✅ Update Complete. Net Worth: ${portfolio.total_net_worth:,.2f}")

        except Exception as e:
            print(f"❌ Critical Update Error: {e}")


# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_market_data, trigger="interval", minutes=60)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)