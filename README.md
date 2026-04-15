<div align="center">

![MLB Banner](https://readme-typing-svg.demolab.com?font=Fira+Code&size=30&pause=1000&color=00BFFF&center=true&width=600&lines=⚾+MLB+Prediction+Engine;Powered+by+Data+%26+ML;Sportsbook+Edge+Analysis)

# ⚾ MLB Prediction Engine
### ML-powered Home Run & Hit Probability System with Sportsbook Edge Analysis

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-00C853?style=for-the-badge)

</div>

---

## 🧠 Overview

A modular, data-driven MLB prediction pipeline that generates daily player picks for **home runs and hits** using probabilistic modeling, park factor analysis, and sportsbook edge detection.

The system identifies **+EV (positive expected value)** betting opportunities by comparing model-generated probabilities against sportsbook implied odds — targeting edges of **+7% or greater**.

---

## ✨ Features

- 🔮 **HR Probability Modeling** — predicts home run likelihood per player per game
- 🎯 **Hit Probability Board** — daily ranked hit probability across all active players
- 📊 **Sportsbook Edge Analysis** — compares model odds vs market odds to find +EV spots
- 🏟️ **Park Factor Integration** — adjusts predictions based on ballpark dimensions & conditions
- 📝 **Post-Game Result Logging** — tracks pick accuracy and refines the model over time
- ⚙️ **Modular Pipeline** — each component runs independently or as a full pipeline

---

## 🏗️ System Architecture
---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.9+
pip install -r requirements.txt
```

### Installation
```bash
git clone https://github.com/YOUR_USERNAME/mlb-prediction-engine.git
cd mlb-prediction-engine
pip install -r requirements.txt
```

### Run Daily Picks
```bash
python pipeline/runner.py --date today
```

### Run Specific Date
```bash
python pipeline/runner.py --date 2025-06-12
```

---

## 📊 Sample Output
---

## 🔧 Configuration

Edit `config.py` to customize:

```python
EDGE_THRESHOLD = 0.07        # Minimum edge to flag a pick (7%)
HR_PROB_THRESHOLD = 0.20     # Minimum HR probability (20%)
LOOKBACK_DAYS = 30           # Days of historical data to use
PARK_FACTOR_WEIGHT = 0.15    # Weight of park factor in model
```

---

## 📅 Roadmap

- [ ] Add pitcher matchup scoring
- [ ] Integrate weather API for wind/temperature adjustments
- [ ] Build web dashboard for daily picks
- [ ] Add Statcast exit velocity & barrel rate features
- [ ] Deploy as automated daily cron job

---

## 🤝 Contributing

Pull requests are welcome! For major changes please open an issue first.

---

## 📄 License

MIT License — see [LICENSE](./LICENSE.txt) for details.

---

<div align="center">

Built with ❤️ by **Nitan** | MS Data Science & AI Engineering

⭐ Star this repo if you find it useful!

</div>
