# Analysis: Sector ETF Portfolio Optimization

A detailed walkthrough of the methodology, results, and investment interpretation behind each stage of the optimization pipeline.

---

## 1. Asset Selection and Data Preparation

### Why Sector ETFs?

The portfolio consists of seven SPDR sector ETFs — XLK (Technology), XLF (Financials), XLE (Energy), XLV (Healthcare), XLI (Industrials), XLP (Consumer Staples), and XLU (Utilities). I chose ETFs over individual stocks because each ETF already provides diversified exposure within its sector, which means the optimization results reflect genuine cross-sector allocation decisions rather than getting distorted by idiosyncratic single-stock risk.

From a practical standpoint, this is closer to how an institutional allocator would actually frame the problem — deciding how much to tilt toward tech versus energy versus defensives, not picking individual names.

### Sample Period

The dataset spans March 2010 through March 2026, giving roughly 4,000 daily observations per asset. Starting in 2010 captures several different market environments: the post-financial-crisis recovery, the COVID drawdown and rebound, the 2022 rate hiking cycle, and everything in between. That variety of regimes matters because any optimization framework is only as good as the data feeding it. If a model is calibrated on a bull market alone, risk estimates tend to get understated and the "optimal" portfolio can look great on paper but break down quickly once volatility spikes.

### Data Cleaning

The raw price series were first aligned by date across all assets. Weekend and holiday entries were removed, and any observation where a single asset moved more than 50% in a day was flagged and removed — four rows in total. Moves that large in a sector ETF are almost always data issues (unadjusted splits, bad prints, etc.), and leaving them in would distort both the return distribution and the covariance matrix.

### Log Returns

Log returns were used throughout the analysis. The main reason is their additivity over time — with log returns, a multi-day return is simply the sum of the daily values, which keeps the math cleaner for cumulative performance, rolling analysis, and risk decomposition. For daily data the numerical difference between log and simple returns is negligible, so the standard mean-variance approximation still holds without meaningful loss of accuracy.

---

## 2. Descriptive Statistics and Risk Structure

### Return and Volatility Profiles

A sanity check on daily standard deviations shows everything falls into a reasonable 0.8%–1.7% range, with Energy (XLE) being the most volatile and Consumer Staples (XLP) the least.

Looking at annualized performance, Technology (XLK) clearly dominates with about 15.7% annualized return and the strongest return per unit of risk (roughly 0.72). Industrials (XLI) and Health Care (XLV) fall into a middle tier at about 10.9% and 9.9% respectively.

Energy (XLE) posts the weakest performance at roughly 4.4% annualized while carrying the highest volatility at around 27.5%. The return-to-risk ratio of about 0.16 suggests investors were not well compensated for the additional volatility in that sector over this period.

The defensive sectors behave as expected. Consumer Staples (XLP) and Utilities (XLU) both produce returns around 7.1%, but XLP shows about 13.9% annualized volatility while XLU comes in at 17.6%, making XLP the more efficient defensive allocation.

### Distributional Properties

Every sector shows negative skewness and elevated excess kurtosis, meaning large downside moves occur more often than a normal distribution would suggest. Energy stands out with kurtosis around 15.2 and the most negative skew (-0.85). Even the defensive sectors show kurtosis well above zero — none of these return series are "well behaved."

From a portfolio construction perspective, this matters because a mean-variance optimizer only sees average return and variance, not tail risk. If the return distribution has fat tails, the optimizer will tend to underestimate the probability of large drawdowns. A portfolio that looks efficient on paper may still be vulnerable in stressed market conditions.

### Correlation Structure

All correlations are positive, and none fall below 0.41. The strongest relationship appears between Financials (XLF) and Industrials (XLI) at 0.87, which makes intuitive sense since both sectors are closely tied to the business cycle. Technology and Industrials also pair strongly at 0.76.

Utilities (XLU) consistently shows the weakest correlations with the rest of the universe, dropping to 0.41 with Energy and 0.45 with Technology. For a portfolio optimizer, this creates genuine diversification opportunities even though everything still belongs to the broader US equity market.

The covariance matrix reinforces the same idea. Energy's variance dominates the diagonal (0.000301 compared with roughly 0.000076 for Consumer Staples), and the off-diagonal terms between defensive sectors and cyclical sectors remain relatively small — suggesting the diversification benefit is real rather than simply a result of lower standalone volatility.

### Summary

The asset universe shows a fairly clear trade-off between return-seeking sectors and defensive stabilizers. Technology and Industrials drive most of the return potential, while Consumer Staples, Utilities, and Health Care provide the main diversification benefits. The relatively high correlations among cyclical sectors limit how much diversification you get from combining them with each other — the more meaningful risk reduction comes from blending those exposures with the defensive sectors.

---

## 3. Risk-Free Rate and Estimation Risk

### Rate Assumption

The risk-free rate is set at 4.25% annualized, reflecting the approximate yield on 1-year US Treasury bills as of late 2025, converted to a daily rate by dividing by 252 trading days.

A constant rate is a simplification — in reality, the risk-free rate moved substantially over this 16-year sample, sitting close to zero for much of 2010 to 2021 before rising sharply between 2023 and 2025. For a single-period optimization framework, however, using the current market rate is the more practical choice. The objective is to construct a portfolio today, so the relevant opportunity cost is what an investor can earn in a risk-free instrument right now.

### Estimation Risk

The sample mean is a notoriously noisy estimator of expected returns. Even with more than 4,000 observations, the standard error of a daily mean return is large relative to the mean itself.

To make this concrete: XLK's daily mean of 0.062% versus XLP's 0.028% appears to imply a gap of roughly 8.5 percentage points annualized. In reality, that difference is completely buried under day-to-day volatility that is an order of magnitude larger. If one particularly bad year is added or removed from the sample, the ranking of sector returns could easily change.

The covariance matrix can usually be estimated with more precision — variances and correlations are second-moment statistics and tend to stabilize more quickly as sample size increases. Even so, the assumption that correlations remain stable over time breaks down during market stress. A correlation like the 0.87 between XLF and XLI during normal conditions can behave very differently during a financial crisis.

This asymmetry — where the covariance matrix is relatively reliable but expected returns are highly uncertain — is exactly why the five optimization approaches can produce very different portfolios from the same dataset.

---

## 4. Portfolio Optimization Results

### 4.1 Global Minimum-Variance

**Result:** 7.71% return | 13.53% volatility | Sharpe 0.26
**Weights:** XLP 67.7%, XLV 21.2%, XLU 11.2% — zero allocation to all other sectors.

The optimizer settles on these three because they have the lowest individual volatility and their correlations with each other are moderate compared to the cyclical sectors. XLP acts as the anchor with about 13.9% volatility and correlations of 0.72 with XLV and 0.70 with XLU.

Financials, Energy, and Industrials receive zero weight because they increase portfolio risk without offering enough diversification benefit. Energy has about 27.5% volatility, Financials around 22.0%, and Industrials about 19.5% — and they're also strongly correlated with each other. When the optimizer tries to reduce total variance, including these assets simply pushes risk higher.

The result is a heavily defensive portfolio with no exposure to Technology or Financials and very little sensitivity to the broader economic cycle.

### 4.2 Maximum-Return

**Result:** 15.69% return | 21.82% volatility | Sharpe 0.52
**Weights:** XLK 100%

With long-only constraints, maximizing expected return just means putting the entire portfolio into the highest sample mean return asset. The Sharpe ratio of 0.52 is actually higher than the minimum-variance portfolio, but a fully concentrated position in a single sector would be difficult to justify in a real portfolio.

### 4.3 Maximum-Sharpe (Tangency)

**Result:** 15.69% return | 21.82% volatility | Sharpe 0.52
**Weights:** XLK 100% — identical to Maximum-Return.

This illustrates a well-known behavior of mean-variance optimization: when one asset has a clearly higher Sharpe ratio and correlations are moderate, the optimizer will concentrate entirely in that asset. XLK's annualized excess return of roughly 11.4% on 21.8% volatility yields a Sharpe of 0.52. No combination of the other six ETFs can beat that risk-adjusted performance in this sample.

While mathematically correct, a single-sector portfolio is impractical for any real-world allocator, which is why constraints on positions and diversification are typically added in professional implementations.

### 4.4 Risk-Parity

**Result:** 8.77% return | 15.18% volatility | Sharpe 0.30
**Weights:** XLP 37.9%, XLK 14.8%, XLU 13.8%, XLF 13.0%, XLE 9.1%, XLI 8.8%, XLV 2.6%

Every asset receives a non-zero allocation, reflecting a balanced risk budgeting approach. The weights are intuitive — Consumer Staples gets the largest weight because it has the lowest volatility, while Energy gets the smallest weight because it has the highest.

The risk contribution chart shows contributions ranging from roughly 2% (XLV) to 30% (XLP) against a 14.3% target. With only seven assets and this correlation structure, true equal risk contribution is impossible to achieve exactly. Still, the portfolio is far more balanced than any mean-variance allocation.

For an investor skeptical of return forecasts, risk parity is the more robust starting point, even if it sacrifices some expected return. It is robust to misestimation of returns and avoids concentration risk by construction.

### 4.5 Black-Litterman

**Result:** 14.49% return | 20.94% volatility | Sharpe 0.49
**Weights:** XLK 85.6%, XLF 7.3%, XLE 5.5%, XLI 1.6%

#### Equilibrium Returns

The equilibrium returns were obtained through reverse optimization using an equal-weight portfolio as a proxy for market weights. The implied risk aversion parameter is δ = 1.8352. The equilibrium returns are fairly compressed, ranging from 3.3% for XLP to 6.5% for XLE — this acts as a stabilizing anchor that prevents the model from chasing historical return differences.

#### Investor Views

Two views were introduced:

**View 1 (Absolute):** XLK earns about 20% annually, motivated by the continued expansion of AI infrastructure and strong cloud-related earnings growth.

**View 2 (Relative):** XLE outperforms XLU by about 3% per year, based on relatively strong energy demand and utilities facing pressure from higher interest rates.

The first view has the largest effect on posterior returns — XLK's expected return increases from 5.32% to 12.56%. All sectors see their expected returns move upward, even those without direct views, because XLK is positively correlated with the other sectors and a strong positive view on Technology pulls up related assets through the blending process.

#### Why Black-Litterman Is More Stable

The 100% XLK allocation from the maximum-Sharpe solution shows the main weakness of traditional mean-variance optimization — it treats sample mean returns as perfectly reliable and pushes the portfolio toward whichever asset appears to have the highest Sharpe ratio.

Black-Litterman deals with this by starting from equilibrium returns and adjusting them only where the investor has clear views. The final expected returns are a weighted combination of the prior and the views. About 14% of the portfolio is allocated across sectors other than XLK — a meaningful improvement in diversification for a small tradeoff in expected Sharpe ratio (0.49 vs. 0.52).

---

## 5. Post-Optimization Distributional Analysis

### Fat Tails and Non-Normality

All five portfolios show fat tails and negative skewness, with excess kurtosis values between 10 and 18. The KDE plots confirm this visually: for every portfolio, the empirical density is higher than the normal curve near the center and the tails remain above the normal reference. The Q-Q plots show the characteristic S-shaped pattern in all cases — more extreme negative returns than the normal model predicts on the left, and more extreme positive returns on the right.

Risk-Parity shows the fattest tails (kurtosis 18.0), followed by Min-Variance (14.4), Black-Litterman (11.5), and Max-Sharpe (10.0). The high kurtosis in the diversified portfolios is intuitive: by spreading weight across multiple sectors, these portfolios are exposed to correlated extreme moves when correlations spike during stress.

### Tail Loss Exposure

The 5th percentile daily losses confirm the expected risk hierarchy:

| Portfolio | Q5% Daily Loss | Worst Daily Loss |
|-----------|---------------|-----------------|
| Min-Variance | -1.25% | -9.51% |
| Risk-Parity | -1.42% | -11.10% |
| Black-Litterman | -2.08% | -14.81% |
| Max-Sharpe | -2.18% | -14.88% |

### Cumulative Performance

The portfolios concentrated in Technology grow to roughly eight times the initial investment by 2026. The more diversified portfolios grow to around three to three and a half times. However, the concentrated portfolios also experience larger drawdowns during periods such as 2020 and 2022, while the diversified portfolios decline less.

---

## 6. Final Assessment and Recommendation

### Concentration vs. Diversification

| Portfolio | HHI | Active Assets | Sharpe |
|-----------|-----|--------------|--------|
| Min-Variance | 0.515 | 3 | 0.256 |
| Max-Return | 1.000 | 1 | 0.524 |
| Max-Sharpe | 1.000 | 1 | 0.524 |
| Risk-Parity | 0.218 | 7 | 0.298 |
| Black-Litterman | 0.742 | 4 | 0.489 |

### Recommendation

Among the five approaches, **Black-Litterman appears to be the most reasonable allocation**. It produces an annualized return of 14.49% with a Sharpe ratio of 0.489, capturing much of the upside seen in the concentrated Technology portfolios while still allocating about 14% of the capital to other sectors.

More importantly, the allocation does not rely entirely on historical sample means. Instead, it reflects an explicit view about the Technology sector while keeping equilibrium returns as a baseline for the rest of the portfolio. From an investment perspective, that reasoning is easier to justify than simply extending historical return rankings into the future.

### Key Lessons

1. **Gaussian-based risk measures understate extremes.** Parametric VaR systematically underestimates the probability and magnitude of losses. Practitioners should prefer empirical VaR, t-distribution VaR, or CVaR to capture tail risk directly.

2. **Diversification is not a cure-all.** Min-Variance and Risk-Parity compress day-to-day volatility but carry higher kurtosis, meaning extreme market events can still generate substantial drawdowns. Correlations spike during stress, weakening the diversification benefit exactly when it matters most.

3. **Estimation risk is the dominant practical challenge.** The fact that Max-Sharpe collapses to a single-asset portfolio highlights how sensitive mean-variance optimization is to noisy return estimates. Black-Litterman addresses this by anchoring to equilibrium returns and only adjusting where the investor has explicit conviction.

4. **No portfolio eliminates tail risk entirely.** In practice, investors would usually combine portfolio optimization with additional tools such as CVaR limits, drawdown controls, or stress testing. Among the five approaches considered here, Black-Litterman provides the most reasonable starting point for constructing a real portfolio.

---

*Author: Bhawini Singh | MS Quantitative Finance, Northeastern University (2026)*
