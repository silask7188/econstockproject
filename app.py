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
    history = PortfolioHistory.query.order_by(PortfolioHistory.date.asc()).all()
    data = [{'x': h.date.isoformat(), 'y': h.total_value} for h in history]
    return jsonify(data)


@app.route('/api/stock_history_json')
def get_stock_history_json():
    """Dump all stock history as standard JSON"""
    history = StockHistory.query.order_by(StockHistory.timestamp.asc()).all()
    data = [{'date': h.timestamp.isoformat(), 'ticker': h.ticker, 'price': h.price} for h in history]
    return jsonify(data)


@app.route('/api/timestamps_csv')
def get_timestamps_csv():
    """
    Complex Endpoint: JSON keys are timestamps, values are CSV strings.
    Usage: /api/timestamps_csv?days=7 (defaults to all time if not specified)
    """
    days = request.args.get('days', type=int)
    query = StockHistory.query

    if days:
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(StockHistory.timestamp >= start_date)

    history = query.order_by(StockHistory.timestamp.asc()).all()

    # Group by timestamp
    grouped = {}
    for h in history:
        ts = h.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        if ts not in grouped:
            grouped[ts] = []
        grouped[ts].append([h.ticker, h.price])

    # Convert lists to CSV strings
    result = {}
    for ts, rows in grouped.items():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['SYMBOL', 'PRICE'])  # Header
        writer.writerows(rows)
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
                        # Save old price to 'previous' before overwriting, so we can show change
                        if h.current_price:
                            h.previous_price = h.current_price
                        else:
                            h.previous_price = h.average_buy_price  # Fallback for first run

                        h.current_price = new_price

                        # Add to StockHistory (For the JSON/CSV endpoint)
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