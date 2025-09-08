import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import os

def load_data(path="../data/base_analyze/xsmb-2-digits.csv"):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    number_columns = [c for c in df.columns if c != "date"]
    return df, number_columns

def build_gap_data(df, number_columns):
    gap_data = defaultdict(list)
    last_seen = {}

    for _, row in df.iterrows():
        date = row["date"]
        numbers_today = row[number_columns].astype(str).tolist()

        for num in numbers_today:
            if len(num) == 1:
                num = "0" + num

            if num in last_seen:
                gap = (date - last_seen[num]).days
                gap_data[num].append(gap)

            last_seen[num] = date

    return gap_data, last_seen

def compute_hazard(gap_data):
    hazard_data = {}

    for num, gaps in gap_data.items():
        values, counts = np.unique(gaps, return_counts=True)
        pmf = dict(zip(values, counts / counts.sum()))

        survival = {}
        for t in sorted(values):
            survival[t] = sum([pmf[k] for k in pmf if k >= t])

        hazard = {t: pmf[t] / survival[t] for t in survival}
        hazard_data[num] = hazard

    return hazard_data

if __name__ == "__main__":
    # === Step 1: Load Data ===
    df, number_columns = load_data()

    # === Step 2: Build gap dataset ===
    gap_data, last_seen = build_gap_data(df, number_columns)

    # === Step 3: Compute hazard ===
    hazard_data = compute_hazard(gap_data)

    # === Step 4: Current gaps ===
    today = df["date"].max()
    current_gap = {num: (today - last_seen[num]).days for num in last_seen}

    # === Step 5: Hazard score for prediction ===
    hazard_score = {}
    for num, gap in current_gap.items():
        h = hazard_data.get(num, {})
        if gap in h:
            hazard_score[num] = h[gap]
        else:
            hazard_score[num] = min(h.values()) if h else 0

    top10 = sorted(hazard_score.items(), key=lambda x: x[1], reverse=True)[:10]
    print("Top 10 numbers by hazard score:", top10)

    # === Step 6: Create output folder ===
    os.makedirs("data", exist_ok=True)

    # === Step 7: Example chart ===
    def plot_hazard(num):
        h = hazard_data.get(num, {})
        if not h:
            print(f"No data for {num}")
            return
        xs = sorted(h.keys())
        ys = [h[t] for t in xs]

        plt.figure(figsize=(8,5))
        plt.plot(xs, ys, marker="o")
        plt.title(f"Hazard function for number {num}")
        plt.xlabel("Gap length (days)")
        plt.ylabel("Hazard probability")
        plt.grid(True)
        plt.savefig(f"data/hazard_{num}.png")
        plt.close()


    def plot_multiple_hazards(hazard_data, numbers):
        plt.figure(figsize=(10, 6))

        for num in numbers:
            h = hazard_data.get(num, {})
            if not h:
                print(f"No data for number {num}")
                continue

            xs = sorted(h.keys())
            ys = [h[t] for t in xs]

            plt.plot(xs, ys, marker="o", label=f"{num}")

            # Highlight last point (current max gap)
            plt.scatter(xs[-1], ys[-1], s=100, edgecolors="black", zorder=5)

            # Add description text near the last point
            plt.text(xs[-1] + 0.5, ys[-1], f"{num}: {ys[-1]:.2f}", fontsize=9)

        plt.title("Hazard Function Comparison for Selected Numbers")
        plt.xlabel("Gap length (days since last seen)")
        plt.ylabel("Hazard probability")
        plt.legend(title="Numbers")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig("../data/gap_hazard_analyze/images/hazard_compare.png")
        plt.show()


    # # Save hazard plots for top 5
    # for num, _ in top10[:10]:
    #     plot_hazard(num)
    numbers = [num for num, _ in top10[:5]]
    plot_multiple_hazards(hazard_data, numbers)
