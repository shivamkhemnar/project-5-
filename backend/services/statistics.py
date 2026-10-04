"""Descriptive statistics: ADF test, decomposition, rolling metrics, ATR."""
from __future__ import annotations

import numpy as np
import pandas as pd


def adf_test(series: pd.Series) -> dict:
    try:
        from statsmodels.tsa.stattools import adfuller
        res = adfuller(series.dropna(), autolag="AIC")
        return {"statistic": float(res[0]), "p_value": float(res[1]),
                "stationary": bool(res[1] < 0.05),
                "critical_values": {k: float(v) for k, v in res[4].items()}}
    except Exception as exc:
        return {"statistic": None, "p_value": None, "stationary": None, "error": str(exc)}


def seasonal_decompose_series(series: pd.Series, period: int = 63, model: str = "additive") -> dict:
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        s = series.dropna()
        period = min(period, max(7, len(s) // 3))
        res = seasonal_decompose(s, model=model, period=period, extrapolate_trend="freq")
        def _clean(x):
            return [None if pd.isna(v) else round(float(v), 4) for v in np.asarray(x)]
        return {"trend": _clean(res.trend), "seasonal": _clean(res.seasonal),
                "resid": _clean(res.resid), "period": period, "model": model}
    except Exception as exc:
        return {"trend": [], "seasonal": [], "resid": [], "error": str(exc)}


def rolling_metrics(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    d = df.copy()
    c = d["close"]
    d["sma_20"] = c.rolling(window).mean()
    d["sma_50"] = c.rolling(50).mean()
    d["std_20"] = c.rolling(window).std()
    d["upper_bb"] = d["sma_20"] + 2 * d["std_20"]
    d["lower_bb"] = d["sma_20"] - 2 * d["std_20"]
    d["daily_ret"] = c.pct_change()
    d["volatility_20"] = d["daily_ret"].rolling(window).std() * np.sqrt(252)
    # ATR(14)
    if {"high", "low"}.issubset(d.columns):
        tr = pd.concat([(d["high"] - d["low"]),
                        (d["high"] - c.shift()).abs(),
                        (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
        d["atr_14"] = tr.rolling(14).mean()
    else:
        d["atr_14"] = (c.diff().abs()).rolling(14).mean()
    # RSI(14)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-12)
    d["rsi_14"] = 100 - 100 / (1 + rs)
    return d


def headline_stats(df: pd.DataFrame) -> dict:
    d = rolling_metrics(df)
    last = d.iloc[-1]
    prev = d.iloc[-2] if len(d) > 1 else last
    price = float(last["close"])
    prev_close = float(prev["close"])
    chg = (price - prev_close) / (prev_close + 1e-12) * 100
    # 24h change uses last two closes; period change uses first->last
    period_chg = (price - float(d.iloc[0]["close"])) / float(d.iloc[0]["close"]) * 100
    atr = float(last["atr_14"]) if pd.notna(last["atr_14"]) else float(d["close"].std())
    vol = float(last["volatility_20"]) if pd.notna(last["volatility_20"]) else 0.0
    return {
        "price": round(price, 2),
        "prev_close": round(prev_close, 2),
        "change_pct": round(chg, 2),
        "period_change_pct": round(float(period_chg), 2),
        "high_52w": round(float(d["high"].max()), 2) if "high" in d else round(float(d["close"].max()), 2),
        "low_52w": round(float(d["low"].min()), 2) if "low" in d else round(float(d["close"].min()), 2),
        "atr": round(atr, 3),
        "volatility": round(vol, 4),
        "rsi": round(float(last["rsi_14"]), 1) if pd.notna(last["rsi_14"]) else 50.0,
        "volume": int(last["volume"]) if "volume" in d and pd.notna(last["volume"]) else 0,
        "count": len(d),
    }
