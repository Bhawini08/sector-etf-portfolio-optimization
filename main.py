"""
Sector ETF Portfolio Optimization
==================================
Compares five allocation strategies across seven SPDR sector ETFs:
  1. Global Minimum-Variance
  2. Maximum-Return
  3. Maximum-Sharpe (Tangency)
  4. Risk-Parity
  5. Black-Litterman

Sample period: March 2010 – March 2026 (~4,000 daily observations)

Author: Bhawini Singh
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
from scipy import stats
from scipy.optimize import minimize

warnings.filterwarnings("ignore")
pd.set_option("display.float_format", "{:.6f}".format)
plt.style.use("seaborn-v0_8-whitegrid")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

TICKERS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU"]
DATA_DIR = "data/"
OUTPUT_DIR = "output/"
RF_ANNUAL = 0.0425          # 1-year US Treasury bill yield (late 2025)
ANN_FACTOR = 252
RANDOM_STARTS = 20          # multi-start optimizer restarts

# Black-Litterman views
BL_VIEWS = {
    "P": np.array([
        [1, 0, 0, 0, 0, 0, 0],    # View 1: absolute on XLK
        [0, 0, 1, 0, 0, 0, -1],   # View 2: XLE vs XLU relative
    ]),
    "Q": np.array([0.20, 0.03]),   # 20% XLK, 3% XLE-XLU spread
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# DATA PREPARATION
# ─────────────────────────────────────────────

def load_prices(tickers, data_dir):
    """Load and align daily prices from CSV files."""
    price_dict = {}
    for t in tickers:
        # try common naming patterns
        candidates = [
            f"{t} ETF Stock Price History.csv",
            f"{t}.csv",
            f"{t}_daily.csv",
        ]
        filepath = None
        for c in candidates:
            fp = os.path.join(data_dir, c)
            if os.path.exists(fp):
                filepath = fp
                break
        if filepath is None:
            raise FileNotFoundError(
                f"No CSV found for {t} in {data_dir}. "
                f"Tried: {candidates}"
            )

        df = pd.read_csv(filepath)
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], format="mixed", dayfirst=False)
        df = df.set_index(date_col).sort_index()

        price_col = next(
            (c for c in ["Adj Close", "Close", "Price"] if c in df.columns), None
        )
        if price_col is None:
            raise ValueError(f"No price column found in {filepath}. Columns: {df.columns.tolist()}")

        series = pd.to_numeric(
            df[price_col].astype(str).str.replace(",", ""), errors="coerce"
        )
        price_dict[t] = series
        print(f"  {t}: {series.index[0].date()} -> {series.index[-1].date()}, {len(series)} obs")

    prices = pd.DataFrame(price_dict).sort_index().dropna()
    prices = prices[prices.index.dayofweek < 5]

    # remove data artifacts (>50% daily moves)
    test_ret = prices.pct_change()
    bad = (test_ret.abs() > 0.50).any(axis=1)
    print(f"  Removed {bad.sum()} rows with suspicious >50% daily moves")
    prices = prices[~bad]

    return prices


def compute_returns(prices):
    """Compute daily log returns."""
    return np.log(prices / prices.shift(1)).dropna()


# ─────────────────────────────────────────────
# DESCRIPTIVE STATISTICS
# ─────────────────────────────────────────────

def print_descriptive_stats(returns, tickers):
    """Print and plot descriptive statistics, covariance, and correlation."""
    desc = returns.describe().T
    desc["variance"] = returns.var()
    desc["skewness"] = returns.skew()
    desc["kurtosis"] = returns.kurtosis()
    desc = desc[["mean", "50%", "variance", "std", "skewness", "kurtosis", "min", "max", "count"]]
    desc.columns = ["Mean", "Median", "Variance", "Std Dev", "Skewness", "Kurtosis", "Min", "Max", "Count"]
    print("\n── Daily Return Descriptive Statistics ──\n")
    print(desc)

    # annualized summary
    ann_ret = returns.mean() * ANN_FACTOR
    ann_vol = returns.std() * np.sqrt(ANN_FACTOR)
    ann_df = pd.DataFrame({
        "Ann. Return (%)": ann_ret * 100,
        "Ann. Volatility (%)": ann_vol * 100,
        "Return/Risk": ann_ret / ann_vol,
    })
    print("\n── Annualized Return and Volatility ──\n")
    print(ann_df)

    # covariance heatmap
    cov = returns.cov()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.heatmap(cov, annot=True, fmt=".6f", cmap="inferno", square=True, ax=axes[0])
    axes[0].set_title("Covariance Matrix (Daily)")
    corr = returns.corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, square=True, ax=axes[1])
    axes[1].set_title("Correlation Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "covariance_correlation.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # return vs volatility bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(tickers))
    w = 0.35
    ax.bar(x - w / 2, ann_ret * 100, w, label="Ann. Return (%)", color="steelblue")
    ax.bar(x + w / 2, ann_vol * 100, w, label="Ann. Volatility (%)", color="salmon")
    ax.set_xticks(x)
    ax.set_xticklabels(tickers)
    ax.set_ylabel("%")
    ax.set_title("Annualized Return vs. Volatility by Sector")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "return_vs_volatility.png"), dpi=150, bbox_inches="tight")
    plt.show()

    return cov, corr


# ─────────────────────────────────────────────
# PORTFOLIO HELPERS
# ─────────────────────────────────────────────

def port_stats(w, mu, cov, ann=ANN_FACTOR):
    """Annualized return, volatility, and Sharpe ratio."""
    r = w @ mu * ann
    v = np.sqrt(w @ cov @ w) * np.sqrt(ann)
    s = (r - RF_ANNUAL) / v
    return r, v, s


def print_portfolio(name, w, tickers, mu, cov):
    """Print portfolio summary."""
    r, v, s = port_stats(w, mu, cov)
    print(f"\n  {name}")
    print(f"  Ann. Return:    {r*100:>7.2f}%")
    print(f"  Ann. Volatility:{v*100:>7.2f}%")
    print(f"  Sharpe Ratio:   {s:>7.4f}")
    print(f"  Weights:")
    for t, wi in zip(tickers, w):
        bar = "█" * int(wi * 40)
        print(f"    {t}: {wi:>7.4f}  {bar}")


# ─────────────────────────────────────────────
# OPTIMIZATION
# ─────────────────────────────────────────────

def optimize_min_variance(mu, cov, N):
    """Global Minimum-Variance portfolio (long-only, fully invested)."""
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bnds = [(0, 1)] * N
    best_w, best_val = None, np.inf
    for _ in range(RANDOM_STARTS):
        w0 = np.random.dirichlet(np.ones(N))
        res = minimize(lambda w: w @ cov @ w, w0,
                       method="SLSQP", bounds=bnds, constraints=cons,
                       options={"ftol": 1e-15, "maxiter": 1000})
        if res.fun < best_val:
            best_val, best_w = res.fun, res.x
    return best_w


def optimize_max_return(mu, N):
    """Maximum-Return portfolio (long-only) — allocates 100% to highest-mean asset."""
    w = np.zeros(N)
    w[np.argmax(mu)] = 1.0
    return w


def optimize_max_sharpe(mu, cov, rf_daily, N):
    """Maximum-Sharpe (Tangency) portfolio."""
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bnds = [(0, 1)] * N
    w0 = np.ones(N) / N

    def neg_sharpe(w):
        excess = w @ mu - rf_daily
        vol = np.sqrt(w @ cov @ w)
        return -(excess / vol)

    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bnds, constraints=cons)
    return res.x


def optimize_risk_parity(cov, N):
    """Risk-Parity portfolio — equalize each asset's risk contribution."""
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bnds = [(1e-6, 1)] * N
    best_w, best_val = None, np.inf

    def rp_obj(w):
        rc = w * (cov @ w)
        target = np.sum(rc) / N
        return np.sum((rc - target) ** 2)

    for _ in range(RANDOM_STARTS):
        w0 = np.random.dirichlet(np.ones(N))
        res = minimize(rp_obj, w0, method="SLSQP", bounds=bnds, constraints=cons,
                       options={"ftol": 1e-15, "maxiter": 1000})
        if res.fun < best_val:
            best_val, best_w = res.fun, res.x
    return best_w


def optimize_black_litterman(mu, cov, rf_daily, N, P, Q, T):
    """Black-Litterman portfolio optimization."""
    # Step 1: equilibrium returns via reverse optimization
    w_eq = np.ones(N) / N
    cov_ann = cov * ANN_FACTOR
    mkt_ret = w_eq @ mu * ANN_FACTOR
    mkt_var = w_eq @ cov_ann @ w_eq
    delta = (mkt_ret - RF_ANNUAL) / mkt_var
    pi = delta * cov_ann @ w_eq
    print(f"\n  Risk aversion (δ): {delta:.4f}")
    print(f"  Equilibrium returns: {dict(zip(TICKERS, (pi*100).round(2)))}")

    # Step 2: view confidence (Omega)
    tau = 1 / T
    view_var = P @ (tau * cov_ann) @ P.T
    Omega = np.diag(np.diag(view_var))

    # Step 3: posterior returns
    tau_Sig_inv = np.linalg.inv(tau * cov_ann)
    Omega_inv = np.linalg.inv(Omega)
    post_cov = np.linalg.inv(tau_Sig_inv + P.T @ Omega_inv @ P)
    mu_BL = post_cov @ (tau_Sig_inv @ pi + P.T @ Omega_inv @ Q)

    bl_df = pd.DataFrame({
        "Prior (%)": pi * 100,
        "Posterior (%)": mu_BL * 100,
        "Shift (%)": (mu_BL - pi) * 100,
    }, index=TICKERS)
    print(f"\n  Prior vs Posterior Returns:\n{bl_df}\n")

    # Step 4: optimize on BL returns
    mu_bl_daily = mu_BL / ANN_FACTOR
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bnds = [(0, 1)] * N

    def neg_sharpe_bl(w):
        excess = w @ mu_bl_daily - rf_daily
        vol = np.sqrt(w @ cov @ w)
        return -(excess / vol)

    res = minimize(neg_sharpe_bl, np.ones(N) / N, method="SLSQP", bounds=bnds, constraints=cons)
    return res.x, mu_BL, pi


# ─────────────────────────────────────────────
# POST-OPTIMIZATION ANALYSIS
# ─────────────────────────────────────────────

def run_distribution_analysis(port_returns, port_weights, mu, cov):
    """Generate distribution plots and final comparison."""
    colors = {
        "Min-Variance": "steelblue", "Max-Return": "salmon",
        "Max-Sharpe": "coral", "Risk-Parity": "teal", "Black-Litterman": "darkorange",
    }

    # ── Histograms ──
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    for i, name in enumerate(port_returns.columns):
        axes[i].hist(port_returns[name], bins=80, density=True, alpha=0.7,
                     color=colors[name], edgecolor="white", linewidth=0.3)
        axes[i].set_title(name)
        axes[i].set_xlabel("Daily Return")
    axes[5].set_visible(False)
    fig.suptitle("Return Distributions: Histograms", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "histograms.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── KDE vs Normal ──
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    for i, name in enumerate(port_returns.columns):
        ax = axes[i]
        port_returns[name].plot.kde(ax=ax, color=colors[name], linewidth=2)
        x = np.linspace(port_returns[name].min(), port_returns[name].max(), 200)
        ax.plot(x, stats.norm.pdf(x, port_returns[name].mean(), port_returns[name].std()),
                "k--", linewidth=1, label="Normal")
        ax.set_title(name)
        ax.legend()
    axes[5].set_visible(False)
    fig.suptitle("KDE vs. Normal Distribution", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "kde_vs_normal.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── Q-Q Plots ──
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    for i, name in enumerate(port_returns.columns):
        stats.probplot(port_returns[name], dist="norm", plot=axes[i])
        axes[i].set_title(f"Q-Q: {name}")
        axes[i].get_lines()[0].set_color(colors[name])
        axes[i].get_lines()[0].set_markersize(2)
    axes[5].set_visible(False)
    fig.suptitle("Normal Q-Q Plots", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "qq_plots.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── Comparative KDE ──
    fig, ax = plt.subplots(figsize=(12, 6))
    for name in port_returns.columns:
        port_returns[name].plot.kde(ax=ax, label=name, color=colors[name], linewidth=2)
    ax.set_title("Comparative KDE: All Portfolios")
    ax.set_xlim(-0.08, 0.08)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "kde_overlay.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── Cumulative Returns ──
    fig, ax = plt.subplots(figsize=(12, 6))
    cum = (1 + port_returns).cumprod()
    for name in port_returns.columns:
        ax.plot(cum.index, cum[name], label=name, color=colors[name], linewidth=1.5)
    ax.set_title("Cumulative Returns (Growth of $1)")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "cumulative_returns.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── Final Comparison Table ──
    print("\n" + "=" * 70)
    print("  FINAL PORTFOLIO COMPARISON")
    print("=" * 70)
    rows = []
    for name, w in port_weights.items():
        r, v, s = port_stats(w, mu, cov)
        rows.append({
            "Portfolio": name,
            "Ann. Return (%)": round(r * 100, 2),
            "Ann. Vol (%)": round(v * 100, 2),
            "Sharpe": round(s, 4),
            "Skewness": round(port_returns[name].skew(), 4),
            "Kurtosis": round(port_returns[name].kurtosis(), 4),
            "Active Assets": int(np.sum(w > 0.01)),
            "HHI": round(np.sum(w ** 2), 4),
        })
    final = pd.DataFrame(rows).set_index("Portfolio")
    print(f"\n{final}\n")

    # ── Sharpe / Vol / HHI bar chart ──
    names = list(port_weights.keys())
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    c = [colors[n] for n in names]
    axes[0].bar(names, [port_stats(port_weights[n], mu, cov)[2] for n in names], color=c)
    axes[0].set_title("Sharpe Ratio")
    axes[0].tick_params(axis="x", rotation=45)
    axes[1].bar(names, [port_stats(port_weights[n], mu, cov)[1] * 100 for n in names], color=c)
    axes[1].set_title("Annualized Volatility (%)")
    axes[1].tick_params(axis="x", rotation=45)
    axes[2].bar(names, [np.sum(port_weights[n] ** 2) for n in names], color=c)
    axes[2].set_title("HHI (Concentration)")
    axes[2].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "final_comparison.png"), dpi=150, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  SECTOR ETF PORTFOLIO OPTIMIZATION")
    print("=" * 50)

    # ── Load data ──
    print("\n[1/5] Loading price data...")
    prices = load_prices(TICKERS, DATA_DIR)
    returns = compute_returns(prices)
    print(f"  Sample: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"  Observations: {len(returns)}")

    # ── Descriptive stats ──
    print("\n[2/5] Computing descriptive statistics...")
    mu = returns.mean().values
    cov = returns.cov().values
    N = len(TICKERS)
    rf_daily = RF_ANNUAL / ANN_FACTOR
    print_descriptive_stats(returns, TICKERS)

    # ── Optimize ──
    print("\n[3/5] Running portfolio optimizations...")

    w_mv = optimize_min_variance(mu, cov, N)
    print_portfolio("Global Minimum-Variance", w_mv, TICKERS, mu, cov)

    w_mr = optimize_max_return(mu, N)
    print_portfolio("Maximum-Return", w_mr, TICKERS, mu, cov)

    w_ms = optimize_max_sharpe(mu, cov, rf_daily, N)
    print_portfolio("Maximum-Sharpe (Tangency)", w_ms, TICKERS, mu, cov)

    w_rp = optimize_risk_parity(cov, N)
    print_portfolio("Risk-Parity", w_rp, TICKERS, mu, cov)

    # risk contribution table for risk-parity
    rc = w_rp * (cov @ w_rp)
    rc_pct = rc / rc.sum() * 100
    rc_df = pd.DataFrame({
        "Weight": w_rp, "Risk Contrib (%)": rc_pct
    }, index=TICKERS)
    print(f"\n  Risk-Parity Risk Contributions:\n{rc_df}\n")

    w_bl, mu_BL, pi = optimize_black_litterman(
        mu, cov, rf_daily, N, BL_VIEWS["P"], BL_VIEWS["Q"], T=len(returns)
    )
    print_portfolio("Black-Litterman", w_bl, TICKERS, mu, cov)

    # ── Weight comparison chart ──
    port_weights = {
        "Min-Variance": w_mv, "Max-Return": w_mr,
        "Max-Sharpe": w_ms, "Risk-Parity": w_rp, "Black-Litterman": w_bl,
    }

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(N)
    width = 0.15
    for i, (name, w) in enumerate(port_weights.items()):
        ax.bar(x + i * width, w, width, label=name)
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(TICKERS)
    ax.set_ylabel("Weight")
    ax.set_title("Portfolio Weight Comparison")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "weight_comparison.png"), dpi=150, bbox_inches="tight")
    plt.show()

    # ── Post-optimization analysis ──
    print("\n[4/5] Analyzing portfolio return distributions...")
    port_returns = pd.DataFrame(
        {name: returns.values @ w for name, w in port_weights.items()},
        index=returns.index,
    )
    run_distribution_analysis(port_returns, port_weights, mu, cov)

    print("\n[5/5] Done. Charts saved to output/")
    print("=" * 50)


if __name__ == "__main__":
    main()
