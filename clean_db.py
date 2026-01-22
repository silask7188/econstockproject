from app import app, db, PortfolioHistory, StockHistory
import pandas_market_calendars as mcal
from datetime import datetime
import pytz

# 1. Load the Calendar ONCE (Global Scope)
print("📅 Loading NYSE Calendar (this takes 2 seconds)...")
nyse = mcal.get_calendar('NYSE')

# 2. Create a Cache for dates we have already looked up
# This prevents calculating the schedule 1000 times for the same day
schedule_cache = {}

def is_market_open(timestamp):
    """
    Returns True if the timestamp is during valid NYSE market hours.
    Uses caching for speed.
    """
    # Convert timestamp to US/Eastern
    if timestamp.tzinfo is None:
        tz = pytz.timezone('US/Eastern')
        timestamp = tz.localize(timestamp)
    
    # Check Cache first
    date_key = timestamp.date()
    
    if date_key not in schedule_cache:
        # If not in cache, calculate it and save it
        schedule = nyse.schedule(start_date=date_key, end_date=date_key)
        
        if schedule.empty:
            schedule_cache[date_key] = None # Mark as closed
        else:
            # Store the open and close times
            schedule_cache[date_key] = (
                schedule.iloc[0]['market_open'],
                schedule.iloc[0]['market_close']
            )

    # Retrieve from cache
    cached_times = schedule_cache[date_key]
    
    # If None, market was closed that day (Holiday/Weekend)
    if cached_times is None:
        return False
        
    market_open, market_close = cached_times
    return market_open <= timestamp <= market_close

def clean_database():
    with app.app_context():
        print("🚀 Starting Smart Cleanup (Holiday Aware)...")
        
        # --- CLEAN PORTFOLIO HISTORY ---
        print("   Scanning Portfolio History...")
        p_history = PortfolioHistory.query.all()
        p_deleted = 0
        
        for i, record in enumerate(p_history):
            if not is_market_open(record.date):
                db.session.delete(record)
                p_deleted += 1
            
            # Progress bar every 500 items
            if i > 0 and i % 500 == 0:
                print(f"   ...checked {i} portfolio records...")
        
        # --- CLEAN STOCK HISTORY ---
        print(f"   Scanning Stock History...")
        s_history = StockHistory.query.all()
        s_deleted = 0
        
        for i, record in enumerate(s_history):
            if not is_market_open(record.timestamp):
                db.session.delete(record)
                s_deleted += 1

            if i > 0 and i % 500 == 0:
                print(f"   ...checked {i} stock records...")

        # Commit changes
        if p_deleted > 0 or s_deleted > 0:
            print("   💾 Saving changes to database...")
            db.session.commit()
            print(f"✅ CLEANUP COMPLETE!")
            print(f"   - Removed {p_deleted} flatline portfolio records")
            print(f"   - Removed {s_deleted} flatline stock records")
        else:
            print("✅ Database was already clean.")

if __name__ == "__main__":
    clean_database()
