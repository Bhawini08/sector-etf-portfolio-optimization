# Sector ETF Portfolio Optimization

A comprehensive Python-based portfolio optimization framework applied to seven SPDR Select Sector ETFs, comparing five allocation strategies: Minimum-Variance, Maximum-Return, Maximum-Sharpe (Tangency), Risk-Parity, and Black-Litterman.

## Overview

This project constructs and evaluates optimal portfolios across US equity sectors using 16 years of daily data (March 2010 – March 2026, ~4,000 observations). The analysis covers the full optimization pipeline — from data preparation and covariance estimation through to post-optimization distributional analysis and tail-risk assessment.

### Asset Universe

| ETF | Sector |
|-----|--------|
| XLK | Technology |
| XLF | Financials |
| XLE | Energy |
| XLV | Health Care |
| XLI | Industrials |
| XLP | Consumer Staples |
| XLU | Utilities |

## Optimization Strategies

### 1. Global Minimum-Variance
Minimizes portfolio variance subject to long-only, fully invested constraints. Ignores expected returns entirely — relies only on the covariance matrix.

**Result:** 13.53% annualized volatility | 7.71% return | Sharpe 0.26
Allocates to XLP (67.7%), XLV (21.2%), XLU (11.2%) — purely defensive.

### 2. Maximum-Return
Maximizes expected return under long-only constraints, which collapses to a 100% allocation in the highest-mean asset (XLK).

**Result:** 21.82% volatility | 15.69% return | Sharpe 0.52

### 3. Maximum-Sharpe (Tangency)
Maximizes the Sharpe ratio to identify the tangency portfolio on the efficient frontier. In this dataset, also converges to 100% XLK due to Technology's dominant risk-adjusted performance over the sample period.

**Result:** 21.82% volatility | 15.69% return | Sharpe 0.52

### 4. Risk-Parity
Equalizes each asset's contribution to total portfolio risk. Uses no return estimates — allocates based purely on risk structure.

**Result:** 15.18% volatility | 8.77% return | Sharpe 0.30
All seven sectors receive non-zero weights. HHI = 0.218 (most diversified).

### 5. Black-Litterman
Starts from market-implied equilibrium returns (via reverse optimization) and blends in two investor views:
- **Absolute view:** XLK returns 20% annually (AI/cloud structural thesis)
- **Relative view:** XLE outperforms XLU by 3% annually

**Result:** 20.94% volatility | 14.49% return | Sharpe 0.49
Allocates XLK (85.6%), XLF (7.3%), XLE (5.5%), XLI (1.6%) — concentrated but not fully single-sector.

## Key Findings

- **Estimation risk dominates:** Max-Sharpe and Max-Return both collapse to single-asset portfolios, highlighting mean-variance optimization's sensitivity to noisy return estimates.
- **Fat tails across all portfolios:** Excess kurtosis ranges from 10 to 18. Q-Q plots confirm significant deviation from normality in both tails. Parametric VaR systematically understates downside risk.
- **Diversification ≠ tail-risk immunity:** Risk-Parity has the lowest HHI (0.218) but the highest kurtosis (18.0), because correlations spike during stress events.
- **Black-Litterman as practical middle ground:** Captures most of the upside from a strong sector view while maintaining partial diversification. Sharpe ratio of 0.49 vs. 0.52 for the fully concentrated portfolio — a small tradeoff for meaningfully better risk properties.

## Project Structure

```
sector-etf-portfolio-optimization/
├── README.md
├── requirements.txt
├── data/
│   └── (place CSV files here)
├── src/
│   ├── data_preparation.py
│   ├── optimization.py
│   ├── black_litterman.py
│   ├── analysis.py
│   └── utils.py
├── notebooks/
│   └── full_analysis.ipynb
├── output/
│   └── (generated charts saved here)
└── main.py
```

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/sector-etf-portfolio-optimization.git
cd sector-etf-portfolio-optimization
pip install -r requirements.txt
```

### Data
Download daily price history CSVs for XLK, XLF, XLE, XLV, XLI, XLP, and XLU from any provider (e.g., Yahoo Finance, Nasdaq) and place them in the `data/` directory. Update file paths in `main.py` if needed.

### Run

```bash
python main.py
```

Or open `notebooks/full_analysis.ipynb` for the interactive walkthrough.

## Requirements

```
pandas>=1.5
numpy>=1.23
matplotlib>=3.6
seaborn>=0.12
scipy>=1.9
```

## Methodology Notes

- **Returns:** Log returns used throughout for time-additivity.
- **Risk-free rate:** 4.25% annualized (approximate 1-year US Treasury bill yield, late 2025).
- **Annualization:** 252 trading days. Returns scaled linearly, volatility by √252.
- **Data cleaning:** Weekend/holiday removal, >50% daily move filter (4 rows removed).
- **Optimizer:** `scipy.optimize.minimize` with SLSQP method, multiple random starting points to avoid local minima.
- **Black-Litterman:** τ = 1/T, Ω derived from view portfolio variance, posterior computed via precision-weighted blending.

## Visualizations

The analysis generates:
- Covariance and correlation heatmaps
- Annualized return vs. volatility comparison
- Portfolio weight comparisons across all five strategies
- Risk contribution breakdown (Risk-Parity)
- Prior vs. posterior expected returns (Black-Litterman)
- Return distribution histograms, KDE overlays, and Q-Q plots
- Cumulative return chart (2010–2026)
- Sharpe ratio, volatility, and HHI concentration comparison

## Author

**Bhawini Singh**
MS Quantitative Finance, Northeastern University (2026)

## License

MIT
