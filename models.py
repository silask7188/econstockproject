from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cash_balance = db.Column(db.Float, default=0.00)
    total_net_worth = db.Column(db.Float, default=500000.00)
    last_updated = db.Column(db.DateTime, default=datetime.now)

class Holding(db.Model):
    ticker = db.Column(db.String(10), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    previous_price = db.Column(db.Float, nullable=True) # NEW: For calculating "Change"
    dividend_yield = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    ticker = db.Column(db.String(10), nullable=True)
    transaction_type = db.Column(db.String(20), nullable=False)
    amount_shares = db.Column(db.Integer, nullable=True)
    price_per_share = db.Column(db.Float, nullable=True)
    total_value = db.Column(db.Float, nullable=False)

class PortfolioHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now)
    cash_balance = db.Column(db.Float)
    assets_value = db.Column(db.Float)
    total_value = db.Column(db.Float)

# NEW TABLE: Tracks every stock's price at every snapshot
class StockHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    ticker = db.Column(db.String(10))
    price = db.Column(db.Float)