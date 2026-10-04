"""Data ingestion: yfinance live fetch + GBM synthetic fallback + CSV upload."""
from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PERIOD_DAYS = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "5Y": 1825, "MAX": 3650}

BASE_PRICES = {
    "AAPL": 175.0, "NVDA": 480.0, "TSLA": 240.0, "MSFT": 330.0,
    "AMZN": 145.0, "GOOGL": 135.0, "META": 320.0, "BTC-USD": 43000.0,
    "ETH-USD": 2300.0, "^GSPC": 4750.0, "SPY": 475.0, "QQQ": 410.0,
}


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # flatten MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    rename = {"adj_close": "adj_close", "adjclose": "adj_close"}
    df = df.rename(columns=rename)
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]
    # ensure datetime index -> date column
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
    first = str(df.columns[0]).lower()
    if first in ("date", "datetime", "index"):
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").dropna(subset=["close"]).reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df[["date"] + [c for c in ("open", "high", "low", "close", "adj_close", "volume") if c in df.columns]]


def generate_gbm(
    ticker: str = "AAPL",
    days: int = 365,
    mu: float = 0.0008,
    sigma: float = 0.018,
    inject_anomalies: bool = True,
    seed: int | None = None,
    end_date: datetime | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """Geometric Brownian Motion synthetic OHLCV generator with injected anomalies."""
    rng = np.random.default_rng(seed if seed is not None else abs(hash(ticker)) % (2**31))
    s0 = BASE_PRICES.get(ticker.upper(), 150.0)
    dt = 1.0
    n = max(days, 30)
    shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), n)
    # add mild regime / trend breaks for realism
    regime = np.linspace(0, rng.normal(0, 0.0004) * n, n)
    log_returns = shocks + np.sin(np.arange(n) / 45.0) * 0.002 + regime / n
    close = s0 * np.exp(np.cumsum(log_returns))
    open_ = np.empty(n)
    open_[0] = s0
    open_[1:] = close[:-1] * (1 + rng.normal(0, 0.002, n - 1))
    spread = np.abs(rng.normal(0.004, 0.003, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    base_vol = 5_000_000 if "USD" not in ticker and "^" not in ticker else 20_000
    volume = (base_vol * (1 + np.abs(rng.normal(0, 0.4, n)) + np.abs(log_returns) * 40)).astype(int)

    end = end_date or datetime.utcnow()
    dates = pd.date_range(end=end, periods=n, freq="D")

    df = pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low,
                       "close": close, "adj_close": close, "volume": volume})
    if inject_anomalies:
        n_anom = max(3, n // 90)
        idx = rng.choice(np.arange(10, n - 1), size=n_anom, replace=False)
        for i in idx:
            kind = rng.random()
            if kind < 0.4:  # flash crash
                shock = -rng.uniform(0.05, 0.12)
                df.loc[i, "close"] *= (1 + shock)
                df.loc[i, "low"] *= (1 + shock * 1.3)
                df.loc[i, "volume"] = int(df.loc[i, "volume"] * rng.uniform(2.5, 5.0))
            elif kind < 0.7:  # spike
                shock = rng.uniform(0.05, 0.10)
                df.loc[i, "close"] *= (1 + shock)
                df.loc[i, "high"] *= (1 + shock * 1.3)
                df.loc[i, "volume"] = int(df.loc[i, "volume"] * rng.uniform(2.0, 4.0))
            else:  # volume-only anomaly
                df.loc[i, "volume"] = int(df.loc[i, "volume"] * rng.uniform(3.0, 6.0))
        df = df.sort_values("date").reset_index(drop=True)
    df.attrs["synthetic"] = True
    df.attrs["ticker"] = ticker
    return df


def fetch_market_data(ticker: str, period: str = "1Y", interval: str = "1d") -> tuple[pd.DataFrame, bool]:
    """Fetch OHLCV via yfinance; fallback to GBM on any failure. Returns (df, is_synthetic)."""
    days = PERIOD_DAYS.get(period.upper(), 365)
    try:
        import yfinance as yf
        yf_period = period.lower() if period.upper() in ("1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX") else "1y"
        df = yf.download(ticker, period=yf_period, interval=interval, progress=False,
                         auto_adjust=False, timeout=15)
        if df is None or df.empty or len(df) < 30:
            raise ValueError(f"yfinance returned {0 if df is None else len(df)} rows for {ticker}")
        df = _normalize_ohlc(df)
        if len(df) < 30:
            raise ValueError("insufficient rows after normalization")
        df.attrs["synthetic"] = False
        return df, False
    except Exception as exc:  # offline / rate-limited / unknown ticker
        logger.warning("yfinance fetch failed for %s (%s); using GBM fallback", ticker, exc)
        return generate_gbm(ticker=ticker, days=days), True


def parse_csv_upload(content: bytes) -> pd.DataFrame:
    """Parse user-uploaded CSV into normalized OHLCV."""
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    # accept common aliases
    aliases = {"timestamp": "date", "time": "date", "datetime": "date",
               "adjusted_close": "adj_close", "adjclose": "adj_close", "vol": "volume"}
    df = df.rename(columns=aliases)
    if "date" not in df.columns:
        raise ValueError("CSV must contain a date/datetime column")
    if "close" not in df.columns:
        raise ValueError("CSV must contain a close column")
    return _normalize_ohlc(df)


def to_candles(df: pd.DataFrame) -> list[dict]:
    out = []
    for _, r in df.iterrows():
        d = r["date"]
        ts = int(pd.Timestamp(d).timestamp())
        out.append({"time": ts, "date": pd.Timestamp(d).strftime("%Y-%m-%d"),
                    "open": round(float(r["open"]), 2) if "open" in r else round(float(r["close"]), 2),
                    "high": round(float(r["high"]), 2) if "high" in r else round(float(r["close"]), 2),
                    "low": round(float(r["low"]), 2) if "low" in r else round(float(r["close"]), 2),
                    "close": round(float(r["close"]), 2),
                    "volume": int(r["volume"]) if "volume" in r and pd.notna(r["volume"]) else 0})
    return out
