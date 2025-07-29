import threading
import time
from flask import Flask, render_template
import os
import pandas as pd
import requests
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Render
import matplotlib.pyplot as plt

# Flask app
app = Flask(__name__)

# Environment variables (set in Render dashboard)
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
AUTO_REFRESH_INTERVAL = 1800  # 30 min

# Cache for workouts
cache_df = None

# ---------------------------
# Fetch data from Hevy API
# ---------------------------
def fetch_workouts():
    url = "https://api.hevyapp.com/v1/workouts?page=1&pageSize=10"
    headers = {
        "accept": "application/json",
        "api-key": HEVY_API_KEY
    }
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print(f"[ERROR] API returned {r.status_code}: {r.text}")
        return None

    data = r.json()
    rows = []

    # Loop through workout items
    for w in data.get("items", []):
        try:
            date = datetime.fromisoformat(w["start_time"].replace("Z", "+00:00")).date()
        except Exception:
            date = None

        name = w.get("name", "Unknown")
        volume = w.get("volume", 0)
        rows.append({"date": date, "name": name, "volume": volume})

    df = pd.DataFrame(rows)
    return df

# ---------------------------
# Generate PNG charts
# ---------------------------
def generate_charts(df):
    if df is None or df.empty:
        return

    # Sort by date
    df = df.sort_values("date")

    # Weekly volume trend
    weekly = df.groupby("date")["volume"].sum()
    plt.figure(figsize=(8, 4))
    weekly.plot(kind="line", marker="o", title="Weekly Training Volume")
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("static/weekly_trend.png")
    plt.close()

# ---------------------------
# Auto refresh function
# ---------------------------
def auto_refresh_workouts():
    global cache_df
    while True:
        print("[Auto-Refresh] Fetching latest workouts from Hevy API...")
        df = fetch_workouts()
        if df is not None and not df.empty:
            cache_df = df
            generate_charts(df)
            print(f"[Auto-Refresh] Updated {len(df)} workouts at {datetime.now()}")
        else:
            print("[Auto-Refresh] No data fetched.")
        time.sleep(AUTO_REFRESH_INTERVAL)

# ---------------------------
# Flask routes
# ---------------------------
@app.route("/")
def dashboard():
    global cache_df
    if cache_df is None:
        df = fetch_workouts()
        if df is not None:
            cache_df = df
            generate_charts(df)
    return render_template("dashboard.html")

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    threading.Thread(target=auto_refresh_workouts, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
