# Vietnam Lottery (XSMB) Analysis

## 📋 Table of Contents

- [📖 Description](#-description)
- [📦 Boilerplate](#-boilerplate)
- [🕵️ Features](#-features)
- [⚙️ How it works?](#-how-it-works)
- [🚀 Installation & Usage](#-installation--usage)
- [📖 References](#-references)
- [📖 Summary](#-summary)
- [📄 License](#-license)

## 📖 Description

This project focuses on analyzing the Northern Vietnam Lottery (Xổ Số Miền Bắc – XSMB) results.
It collects historical draw data, processes it, and generates statistics, frequency distributions, and visual insights to help understand lottery patterns.

## 📦 Boilerplate

Fork from original
repo [clean architecture python boilerplate](https://github.com/AnhTuPhi/clean-architecture-python-boilerplate)

## 🕵️ Features

### 🔎 Key Features

- 📊 Data Collection – Fetches official XSMB results daily. (Free version - Public Repo)

- 📈 Statistical Analysis – Computes number frequency, hot/cold numbers, and distribution trends. (Only available in charge fee version - Private Repo)

- 📉 Visualization – Charts and graphs showing historical trends and probability insights. (Only available in charge fee version - Private Repo)

- ⚡ Automation – GitHub Actions automatically update results and refresh insights. (Free version - Public Repo)

- 🔮 Exploratory Prediction – Initial attempts at forecasting possible outcomes based on historical data. (Only available in charge fee version - Private Repo)

### 🎯 Purpose

The goal of this project is not gambling but rather:

- Learning data analysis and visualization with real-world datasets.
- Exploring patterns and randomness in lottery systems.
- Experimenting with prediction models for educational purposes.

## ⚙️ How it works?

### 🤖 Automated Data Collection

This project runs completely automatically using **Github Actions** - no server required - aiming to be serverless!

- ⏰ Schedule: Runs daily via **GitHub Actions workflow**
- 🔄 Process: Fetches latest results → Processes data → Commits to repository
- 📊 Analysis: Generates statistics and updates /data and README.md automatically

### 🕵️ Data Crawling Method

The data collection works by:

- 🔍 Network Analysis: Inspecting browser-server communication
- 🐍 Python Replication: Recreating the data fetch logic in Python
- 📋 Structured Storage: Saving results in JSONL format for easy analysis
- 🔄 Continuous Updates: Daily automated runs ensure fresh data

> **Note:** This is purely for educational and research purposes. No gambling advice is provided.

## 🚀 Installation & Usage

Install requirement dependencies

```sh
pip install -r requirement.txt
```

Run service

```sh
python ./xxx.py
```

## 📖 References

Document references in [this](https://github.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/blob/master/REFERENCES.md)

## 📖 Summary

| Lottery (Xổ số) | Loto (Lô tô) |
| :------------: | :----------: |
| <table><tr><td>Date (Ngày)</td><td>08-09-2025</td></tr><tr><td>Special (Giải đặc biệt)</td><td>04493</td></tr><tr><td>First (Giải nhất)</td><td>66113</td></tr><tr><td>Second (Giải nhì)</td><td>57584, 90587</td></tr><tr><td rowspan="2">Third (Giải ba)</td><td>36917, 29542, 20268</td></tr><tr><td>75320, 01384, 30265</td></tr><tr><td>Fourth (Giải tư)</td><td>8326, 6739, 9383, 8311</td></tr><tr><td rowspan="2">Fifth (Giải năm)</td><td>4763, 7769, 3868</td></tr><tr><td>3932, 0137, 5071</td></tr><tr><td>Sixth (Giải sáu)</td><td>814, 134, 074</td></tr><tr><td>Seventh (Giải bảy)</td><td>32, 24, 12, 52</td></tr></table> | <table><tr><td>First (Đầu)</td><td>Last (Đuôi)</td></tr><tr><td>0</td><td>-</td></tr><tr><td>1</td><td>1, 2, 3, 4, 7</td></tr><tr><td>2</td><td>0, 4, 6</td></tr><tr><td>3</td><td>2, 2, 4, 7, 9</td></tr><tr><td>4</td><td>2</td></tr><tr><td>5</td><td>2</td></tr><tr><td>6</td><td>3, 5, 8, 8, 9</td></tr><tr><td>7</td><td>1, 4</td></tr><tr><td>8</td><td>3, 4, 4, 7</td></tr><tr><td>9</td><td>3</td></tr></table> |

## Data (Dữ liệu)

|          | CSV | JSON | Parquet |
|----------|-----|------|---------|
| Raw      | [xsmb.csv](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb.csv) | [xsmb.json](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb.json) | [xsmb.parquet](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb.parquet) |
| 2-digits | [xsmb-2-digits.csv](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-2-digits.csv) | [xsmb-2-digits.json](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-2-digits.json) | [xsmb-2-digits.parquet](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-2-digits.parquet) |
| Sparse   | [xsmb-sparse.csv](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-sparse.csv) | [xsmb-sparse.json](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-sparse.json) | [xsmb-sparse.parquet](https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-sparse.parquet) |

## Using

You can use `curl` or `wget` to download data files. Or you can load them directly into DataFrame:

Bạn có thể sử dụng curl hoặc wget để tải các tệp dữ liệu. Hoặc bạn có thể tải chúng trực tiếp vào DataFrame:

```sh
wget https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb.csv
```

```sh
curl -O https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-2-digits.csv
```

```python
import pandas as pd

df = pd.read_csv('https://raw.githubusercontent.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/refs/heads/master/data/xsmb-sparse.csv')
df.info()
```

<details>
  <summary><h2>Analysis of special prices (Phân tích kết quả xổ số)</h2></summary>
  <h3>Amount of day from last appearing (Số ngày từ lần xuất hiện cuối cùng)</h3>

  ![Delta](images/special_delta.jpg)

  <h3>Top 10 amount of day from last appearing (Top 10 số lâu chưa xuất hiện)</h3>

  ![Delta top 10](images/special_delta_top_10.jpg)
</details>

<details>
  <summary><h2>Analysis of one-year Loto results (Phân tích kết quả lô tô trong 1 năm)</h2></summary>

  Max: 125. Min: 77.

  Mean: 97.47. Standard deviation: 9.18.

  <h3>Detail (Chi tiết)</h3>

  ![Detail](images/heatmap.jpg)

  <h3>Top 10</h3>

  ![Top 10](images/top-10.jpg)

  <h3>Distribution (Phân bổ)</h3>

  ![Distribution](images/distribution.jpg)
</details>

<details>
  <summary><h3>Amount of day from last appearing (Số ngày từ lần xuất hiện cuối cùng)</h2></summary>

  ![Delta](images/delta.jpg)

  <h3>Top 10 amount of day from last appearing (Top 10 số lâu chưa xuất hiện)</h3>

  ![Delta top 10](images/delta_top_10.jpg)
</details>

## 📄 License

This project is licensed under the MIT License - see
the [LICENSE](https://github.com/AnhTuPhi/xsmb-vietnam-lottery-analysis/blob/master/LICENSE) file for details.

---

<div align="center">
  <strong>⭐ If you find this project useful, please consider giving it a star!</strong>
</div>
