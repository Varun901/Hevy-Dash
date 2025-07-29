import os
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # For Render server compatibility
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
from datetime import datetime
import calendar
from collections import defaultdict

# Flask app
app = Flask(__name__)

# Hevy API settings
HEVY_API_KEY = os.environ.get("HEVY_API_KEY")
BASE_URL = "https://api.hevyapp.com/v1"

# ==============================
# HELPER: Fetch workout history
# ==============================
def fetch_workouts():
    workouts = []
    page = 1
    while True:
        url = f"{BASE_URL}/workouts?page={page}&pageSize=10"
        headers = {"accept": "application/json", "api-key": HEVY_API_KEY}
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print("API Error:", r.text)
            break
        data = r.json()
        if not data:
            break
        workouts.extend(data)
        page += 1
    return workouts

# ==============================
# HELPER: Process workout data
# ==============================
def process_workouts():
    workouts = fetch_workouts()
    if not workouts:
        return pd.DataFrame()

    rows = []
    for w in workouts:
        date = datetime.fromisoformat(w["start_time"].replace("Z", "+00:00")).date()
        for ex in w.get("exercises", []):
            name = ex["name"]
            for set_data in ex.get("sets", []):
                if set_data.get("weight_kg") is not None:
                    weight = set_data.get("weight_kg", 0)
                    reps = set_data.get("reps", 0)
                    volume = weight * reps
                    rows.append({
                        "date": date,
                        "exercise": name,
                        "weight": weight,
                        "reps": reps,
                        "volume": volume
                    })

    df = pd.DataFrame(rows)
    return df

# ==============================
# CHART: Workout Heatmap
# ==============================
def create_heatmap(df):
    if df.empty:
        return
    df_dates = df.groupby("date").size()
    days = [d.timetuple().tm_yday for d in df_dates.index]
    counts = df_dates.values

    plt.figure(figsize=(12, 2))
    plt.scatter(days, [1]*len(days), c=counts, cmap="Reds", s=100)
    plt.yticks([])
    plt.xticks(range(0, 366, 30), [calendar.month_abbr[m] for m in range(1, 13)])
    plt.title("Workout Heatmap (Days Trained)", fontsize=14)
    plt.colorbar(label="Workouts per day")
    plt.savefig("static/heatmap.png", bbox_inches="tight")
    plt.close()

# ==============================
# CHART: Volume Trend
# ==============================
def create_volume_chart(df):
    if df.empty:
        return
    df_vol = df.groupby("date")["volume"].sum().reset_index()

    plt.figure(figsize=(8, 4))
    plt.plot(df_vol["date"], df_vol["volume"], marker="o")
    plt.title("Total Training Volume Over Time")
    plt.xlabel("Date")
    plt.ylabel("Volume (kg)")
    plt.grid(True)
    plt.savefig("static/volume_trend.png", bbox_inches="tight")
    plt.close()

# ==============================
# CHART: PR Graph
# ==============================
def create_pr_chart(df, exercise_name):
    if df.empty:
        return
    ex_df = df[df["exercise"] == exercise_name]
    if ex_df.empty:
        return
    ex_df["max_weight"] = ex_df.groupby("date")["weight"].transform("max")
    pr_df = ex_df.groupby("date")["max_weight"].max().reset_index()

    plt.figure(figsize=(8, 4))
    plt.plot(pr_df["date"], pr_df["max_weight"], marker="o")
    plt.title(f"PR Progression: {exercise_name}")
    plt.xlabel("Date")
    plt.ylabel("Max Weight (kg)")
    plt.grid(True)
    plt.savefig("static/pr_chart.png", bbox_inches="tight")
    plt.close()

# ==============================
# CHART: Muscle Group Breakdown
# ==============================
def create_muscle_breakdown(df):
    if df.empty:
        return
    # Placeholder grouping by keyword
    muscle_map = defaultdict(float)
    for _, row in df.iterrows():
        ex = row["exercise"].lower()
        vol = row["volume"]
        if "bench" in ex or "press" in ex:
            muscle_map["Chest/Shoulders"] += vol
        elif "row" in ex or "pulldown" in ex or "pullup" in ex:
            muscle_map["Back"] += vol
        elif "curl" in ex:
            muscle_map["Biceps"] += vol
        elif "extension" in ex or "squat" in ex or "lunge" in ex:
            muscle_map["Quads"] += vol
        elif "rdl" in ex or "hip" in ex or "deadlift" in ex:
            muscle_map["Glutes/Hamstrings"] += vol
        elif "calf" in ex:
            muscle_map["Calves"] += vol
        else:
            muscle_map["Other"] += vol

    labels = list(muscle_map.keys())
    sizes = list(muscle_map.values())

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%")
    plt.title("Training Volume by Muscle Group")
    plt.savefig("static/muscle_breakdown.png", bbox_inches="tight")
    plt.close()

# ==============================
# ROUTES
# ==============================
@app.route("/", methods=["GET", "POST"])
def dashboard():
    df = process_workouts()
    if not df.empty:
        create_heatmap(df)
        create_volume_chart(df)
        create_muscle_breakdown(df)

        selected_exercise = request.form.get("exercise_dropdown") or df["exercise"].iloc[0]
        create_pr_chart(df, selected_exercise)

        exercises = sorted(df["exercise"].unique())
    else:
        exercises = []
        selected_exercise = None

    return render_template(
        "dashboard.html",
        exercises=exercises,
        selected_exercise=selected_exercise
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
