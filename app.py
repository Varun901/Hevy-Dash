import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, jsonify
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

HEVY_API_KEY = os.getenv("HEVY_API_KEY")

# ---------------------------
# API Helper
# ---------------------------
def get_hevy_data(endpoint):
    url = f"https://api.hevyapp.com/v1/{endpoint}"
    headers = {
        "accept": "application/json",
        "api-key": HEVY_API_KEY
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

# ---------------------------
# Data Fetch
# ---------------------------
def fetch_workouts():
    page = 1
    all_workouts = []
    while True:
        data = get_hevy_data(f"workouts?page={page}&pageSize=10")
        if not data or len(data) == 0:
            break
        all_workouts.extend(data)
        page += 1
    return all_workouts

# ---------------------------
# Process Data
# ---------------------------
def process_data(workouts):
    records = []
    volume_by_week = defaultdict(float)
    frequency = defaultdict(int)
    pr_data = defaultdict(list)
    muscle_volume = defaultdict(float)

    total_sets = 0
    total_reps = 0
    total_exercises = 0

    for w in workouts:
        date = datetime.strptime(w["start_time"], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        week = date.strftime("%Y-W%U")

        for ex in w["exercises"]:
            ex_name = ex["name"]
            muscle_group = ex.get("primary_muscle_group", "Other")
            frequency[ex_name] += 1
            total_exercises += 1

            for set_ in ex.get("sets", []):
                reps = set_.get("reps", 0)
                weight = set_.get("weight", 0)
                total_sets += 1
                total_reps += reps

                # Calculate volume
                volume = reps * weight
                volume_by_week[week] += volume
                muscle_volume[muscle_group] += volume

                # Track PRs
                if weight > 0:
                    pr_data[ex_name].append({"date": date, "weight": weight})

            records.append({
                "date": date,
                "exercise": ex_name,
                "muscle_group": muscle_group,
                "sets": ex.get("sets", [])
            })

    df = pd.DataFrame(records)

    # Calculate summary metrics
    avg_reps = total_reps / total_sets if total_sets else 0
    avg_sets_per_ex = total_sets / total_exercises if total_exercises else 0

    # Workouts per month
    workouts_per_month = defaultdict(int)
    for w in workouts:
        month = datetime.strptime(w["start_time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m")
        workouts_per_month[month] += 1

    return df, frequency, volume_by_week, pr_data, muscle_volume, avg_reps, avg_sets_per_ex, workouts_per_month

# ---------------------------
# Plots
# ---------------------------
def create_heatmap(df):
    df_dates = df.groupby("date").size()
    plt.figure(figsize=(10, 3))
    plt.scatter(df_dates.index, [1]*len(df_dates), s=50, c="green")
    plt.axis("off")
    plt.savefig("static/images/heatmap.png", bbox_inches="tight")
    plt.close()

def create_exercise_distribution(frequency):
    labels, values = zip(*sorted(frequency.items(), key=lambda x: x[1], reverse=True)[:10])
    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct="%1.0f%%")
    plt.savefig("static/images/exercise_distribution.png", bbox_inches="tight")
    plt.close()

def create_volume_trend(volume_by_week):
    weeks, volumes = zip(*sorted(volume_by_week.items()))
    plt.figure(figsize=(8, 4))
    plt.plot(weeks, volumes, marker="o")
    plt.xticks(rotation=45)
    plt.title("Weekly Training Volume")
    plt.savefig("static/images/weekly_volume.png", bbox_inches="tight")
    plt.close()

def create_muscle_group_chart(muscle_volume):
    labels, values = zip(*muscle_volume.items()) if muscle_volume else ([], [])
    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct="%1.0f%%")
    plt.title("Volume by Muscle Group")
    plt.savefig("static/images/muscle_volume.png", bbox_inches="tight")
    plt.close()

def create_monthly_workout_bar(workouts_per_month):
    months, counts = zip(*sorted(workouts_per_month.items()))
    plt.figure(figsize=(8, 4))
    plt.bar(months, counts, color="orange")
    plt.xticks(rotation=45)
    plt.title("Workouts Per Month")
    plt.savefig("static/images/workouts_per_month.png", bbox_inches="tight")
    plt.close()

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def dashboard():
    workouts = fetch_workouts()
    df, frequency, volume_by_week, pr_data, muscle_volume, avg_reps, avg_sets_per_ex, workouts_per_month = process_data(workouts)

    create_heatmap(df)
    create_exercise_distribution(frequency)
    create_volume_trend(volume_by_week)
    create_muscle_group_chart(muscle_volume)
    create_monthly_workout_bar(workouts_per_month)

    return render_template(
        "dashboard.html",
        pr_data=pr_data,
        avg_reps=round(avg_reps, 1),
        avg_sets=round(avg_sets_per_ex, 1),
        total_workouts=len(workouts)
    )

@app.route("/pr_data")
def get_pr_data():
    workouts = fetch_workouts()
    _, _, _, pr_data, _, _, _, _ = process_data(workouts)
    return jsonify(pr_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
