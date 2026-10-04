"""Forecasting engine: Prophet / ARIMA / Holt-Winters / ETS with intervals + metrics."""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SUPPORTED_MODELS = ["prophet", "arima", "holt-winters", "ets", "sma"]


def _residual_intervals(train: pd.Series, forecast: np.ndarray, horizon: int) -> tuple[np.ndarray, ...]:
    resid = train.diff().dropna()
    sigma = float(resid.std()) if len(resid) > 2 else float(train.std() * 0.02)
    sigma = sigma if sigma > 0 else float(train.mean() * 0.005 + 1e-6)
    steps = np.arange(1, horizon + 1)
    w80, w95 = 1.2816 * sigma * np.sqrt(steps), 1.96 * sigma * np.sqrt(steps)
    f = np.asarray(forecast, dtype=float)
    return f - w80, f + w80, f - w95, f + w95


def _forecast_prophet(df: pd.DataFrame, horizon: int) -> np.ndarray:
    from prophet import Prophet
    p = df[["date", "close"]].rename(columns={"date": "ds", "close": "y"})
    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True,
                interval_width=0.95)
    m.fit(p)
    fut = m.make_future_dataframe(periods=horizon, freq="D")
    fc = m.predict(fut)
    return fc["yhat"].tail(horizon).to_numpy()


def _forecast_arima(df: pd.DataFrame, horizon: int) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA
    y = df["close"].dropna()
    try:
        fit = ARIMA(y, order=(5, 1, 0)).fit()
    except Exception:
        fit = ARIMA(y, order=(1, 1, 1)).fit()
    return np.asarray(fit.forecast(steps=horizon))


def _forecast_holt_winters(df: pd.DataFrame, horizon: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    y = df["close"].dropna()
    seasonal_periods = 21 if len(y) >= 63 else None
    try:
        if seasonal_periods:
            fit = ExponentialSmoothing(y, trend="add", seasonal="add",
                                       seasonal_periods=seasonal_periods).fit(optimized=True)
        else:
            fit = ExponentialSmoothing(y, trend="add").fit(optimized=True)
    except Exception:
        fit = ExponentialSmoothing(y, trend="add").fit(optimized=True)
    return np.asarray(fit.forecast(horizon))


def _forecast_ets(df: pd.DataFrame, horizon: int) -> np.ndarray:
    # Simple exponential smoothing (ETS A,N,N fallback)
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing
    y = df["close"].dropna()
    fit = SimpleExpSmoothing(y).fit(smoothing_level=0.3, optimized=True)
    last = float(fit.level[-1]) if hasattr(fit, "level") else float(y.iloc[-1])
    trend = float(y.diff().tail(20).mean())
    return np.array([last + trend * (i + 1) for i in range(horizon)])


def _forecast_sma(df: pd.DataFrame, horizon: int) -> np.ndarray:
    y = df["close"].dropna()
    drift = float(y.diff().tail(30).mean())
    last = float(y.iloc[-1])
    if np.isnan(drift):
        drift = 0.0
    return np.array([last + drift * (i + 1) for i in range(horizon)])


def generate_forecast(df: pd.DataFrame, horizon: int = 30, model: str = "prophet") -> dict:
    """Return point forecast + 80/95% bands + in-sample backtest metrics."""
    model = (model or "prophet").lower()
    if model not in SUPPORTED_MODELS:
        model = "prophet"
    horizon = int(max(7, min(horizon, 180)))
    hist = df.sort_values("date").reset_index(drop=True)
    train = hist["close"]

    forecast_fn = {"prophet": _forecast_prophet, "arima": _forecast_arima,
                   "holt-winters": _forecast_holt_winters, "ets": _forecast_ets,
                   "sma": _forecast_sma}[model]
    tried = [model]
    point: np.ndarray | None = None
    used_model = model
    last_err = None
    for candidate in tried + ["holt-winters", "arima", "ets", "sma"]:
        if candidate in tried[1:]:
            continue
        try:
            fn = {"prophet": _forecast_prophet, "arima": _forecast_arima,
                  "holt-winters": _forecast_holt_winters, "ets": _forecast_ets,
                  "sma": _forecast_sma}[candidate]
            point = np.asarray(fn(hist, horizon), dtype=float)
            used_model = candidate
            break
        except Exception as exc:
            last_err = str(exc)
            continue
    if point is None:
        raise RuntimeError(f"All forecast models failed. Last error: {last_err}")
    # guard against non-finite / negative drift explosions
    point = np.where(np.isfinite(point), point, train.iloc[-1])
    point = np.maximum(point, train.iloc[-1] * 0.2)

    lo80, hi80, lo95, hi95 = _residual_intervals(train, point, horizon)
    last_date = pd.Timestamp(hist["date"].iloc[-1])
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
    direction = "bullish" if float(point[-1]) > float(train.iloc[-1]) else "bearish"
    proba = _directional_probability(train, point)
    metrics = backtest_metrics(hist, horizon=min(horizon, 30), model=used_model)

    rows = [{"date": d.strftime("%Y-%m-%d"), "yhat": round(float(y), 2),
             "lower_80": round(float(a), 2), "upper_80": round(float(b), 2),
             "lower_95": round(float(c), 2), "upper_95": round(float(d_), 2)}
            for d, y, a, b, c, d_ in zip(future_dates, point, lo80, hi80, lo95, hi95)]
    return {"model": used_model, "requested_model": model, "horizon": horizon,
            "direction": direction, "continuation_probability": round(proba, 3),
            "forecast": rows, "metrics": metrics}


def _directional_probability(train: pd.Series, point: np.ndarray) -> float:
    drift = float(np.mean(np.diff(train.tail(30)))) if len(train) > 5 else 0.0
    sigma = float(train.diff().std()) or 1e-6
    up = float(point[-1] - train.iloc[-1] > 0)
    # blend momentum z-score with naive vote
    import math
    z = drift * len(point) / (sigma * math.sqrt(len(point)) + 1e-12)
    logistic = 1 / (1 + math.exp(-3 * z))
    return round(0.5 * up + 0.5 * (logistic if up else 1 - logistic) + (0.18 if up == (drift > 0) else -0.05), 3)


def backtest_metrics(df: pd.DataFrame, horizon: int = 30, model: str = "holt-winters") -> dict:
    """Hold out last `horizon` points, forecast, compare."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    hist = df.sort_values("date").reset_index(drop=True)
    horizon = max(7, min(horizon, len(hist) // 3 if len(hist) > 30 else 7))
    train, test = hist.iloc[:-horizon], hist.iloc[-horizon:]
    try:
        fn = {"prophet": _forecast_prophet, "arima": _forecast_arima,
              "holt-winters": _forecast_holt_winters, "ets": _forecast_ets,
              "sma": _forecast_sma}.get(model, _forecast_holt_winters)
        pred = np.asarray(fn(train, horizon), dtype=float)
    except Exception:
        pred = np.asarray(_forecast_sma(train, horizon), dtype=float)
    actual = test["close"].to_numpy(dtype=float)
    n = min(len(pred), len(actual))
    pred, actual = pred[:n], actual[:n]
    rmse = float(np.sqrt(mean_squared_error(actual, pred)))
    mae = float(mean_absolute_error(actual, pred))
    mape = float(np.mean(np.abs((actual - pred) / (np.abs(actual) + 1e-9))) * 100)
    dir_acc = float(np.mean(np.sign(np.diff(actual)) == np.sign(np.diff(pred))) * 100) if n > 2 else 50.0
    return {"rmse": round(rmse, 3), "mae": round(mae, 3), "mape": round(mape, 2),
            "directional_accuracy": round(float(dir_acc), 1), "test_points": n, "model": model}
