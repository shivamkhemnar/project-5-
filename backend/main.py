"""AlphaQuant AI — FastAPI entrypoint & analytics endpoints."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AnomalyLog, ForecastRecord, TickerQuery, get_db, init_db
from .services.anomaly_detection import detect_anomalies
from .services.data_ingestion import fetch_market_data, parse_csv_upload, to_candles
from .services.forecasting import SUPPORTED_MODELS, backtest_metrics, generate_forecast
from .services.statistics import adf_test, headline_stats, rolling_metrics, seasonal_decompose_series

logging.basicConfig(level=logging.INFO)
settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.version,
              description="Quantitative analytics: market data, forecasting, anomaly detection.")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
init_db()


class ForecastRequest(BaseModel):
    ticker: str = "AAPL"
    period: str = "1Y"
    horizon: int = Field(30, ge=7, le=180)
    model: str = "prophet"
    contamination: float = Field(0.03, ge=0.005, le=0.15)


class AnomalyRequest(BaseModel):
    ticker: str = "AAPL"
    period: str = "1Y"
    contamination: float = Field(0.03, ge=0.005, le=0.15)


def _load(ticker: str, period: str):
    df, synthetic = fetch_market_data(ticker.upper(), period.upper())
    return df, synthetic


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version,
            "time": datetime.utcnow().isoformat()}


@app.get("/api/market-data/{ticker}")
def market_data(ticker: str, period: str = Query("1Y"), db: Session = Depends(get_db)):
    df, synthetic = _load(ticker, period)
    enriched = rolling_metrics(df)
    stats = headline_stats(df)
    adf = adf_test(df["close"])
    decomp = seasonal_decompose_series(df.set_index("date")["close"] if "date" in df else df["close"])
    db.add(TickerQuery(ticker=ticker.upper(), period=period, rows=len(df),
                       synthetic=int(synthetic)))
    db.commit()
    tail = enriched.tail(400)
    history = [{"date": pd_date(tail, i), **row} for i, row in enumerate(_history_rows(tail))]
    return {"ticker": ticker.upper(), "period": period, "synthetic": synthetic,
            "stats": stats, "stationarity": adf, "decomposition": decomp,
            "candles": to_candles(df.tail(400)), "history": history,
            "count": len(df)}


def pd_date(tail, i):
    try:
        return tail.iloc[i]["date"].strftime("%Y-%m-%d")
    except Exception:
        return str(tail.iloc[i]["date"])


def _history_rows(tail):
    rows = []
    for _, r in tail.iterrows():
        rows.append({k: (None if str(v) == "nan" and not isinstance(v, str) else
                         (round(float(v), 3) if isinstance(v, float) else
                          (int(v) if k == "volume" and v == v else v)))
                     for k, v in r.items() if k != "date"})
    return rows


@app.post("/api/forecast")
def forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    if req.model.lower() not in SUPPORTED_MODELS:
        raise HTTPException(400, f"Unknown model. Choose from {SUPPORTED_MODELS}")
    df, synthetic = _load(req.ticker, req.period)
    try:
        result = generate_forecast(df, horizon=req.horizon, model=req.model)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    m = result["metrics"]
    db.add(ForecastRecord(ticker=req.ticker.upper(), model=result["model"],
                          horizon=req.horizon, direction=result["direction"],
                          rmse=m["rmse"], mae=m["mae"], payload=json.dumps(result["forecast"])))
    db.commit()
    return {"ticker": req.ticker.upper(), "synthetic": synthetic,
            "history_tail": to_candles(df.tail(120)), **result}


@app.post("/api/anomalies")
def anomalies(req: AnomalyRequest, db: Session = Depends(get_db)):
    df, synthetic = _load(req.ticker, req.period)
    result = detect_anomalies(df, contamination=req.contamination)
    for a in result["anomalies"]:
        db.add(AnomalyLog(ticker=req.ticker.upper(), date=a["date"], price=a["price"],
                          severity=a["severity"], type=a["type"], z_score=a["z_score"]))
    db.commit()
    # attach price context for chart overlay
    price_by_date = {pd.Timestamp(r["date"]).strftime("%Y-%m-%d"): round(float(r["close"]), 2)
                     for _, r in df.iterrows()}
    for a in result["anomalies"]:
        a["price"] = price_by_date.get(a["date"], a["price"])
    return {"ticker": req.ticker.upper(), "synthetic": synthetic, **result}


@app.get("/api/summary/{ticker}")
def summary(ticker: str, period: str = Query("1Y"), horizon: int = Query(30, ge=7, le=180),
            model: str = Query("prophet"), contamination: float = Query(0.03)):
    df, synthetic = _load(ticker, period)
    stats = headline_stats(df)
    anom = detect_anomalies(df, contamination=contamination)
    try:
        fc = generate_forecast(df, horizon=horizon, model=model)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    narrative = build_narrative(ticker.upper(), stats, anom, fc, period)
    return {"ticker": ticker.upper(), "period": period, "synthetic": synthetic,
            "stats": stats, "anomalies": anom, "forecast": fc, "narrative": narrative}


@app.get("/api/backtest")
def backtest(ticker: str = Query("AAPL"), period: str = Query("1Y"),
             horizon: int = Query(30, ge=7, le=90)):
    df, synthetic = _load(ticker, period)
    results = {}
    for model in SUPPORTED_MODELS:
        try:
            results[model] = backtest_metrics(df, horizon=horizon, model=model)
        except Exception as exc:
            results[model] = {"error": str(exc)}
    best = min(((m, v) for m, v in results.items() if "rmse" in v),
               key=lambda kv: kv[1]["rmse"], default=(None, {}))
    return {"ticker": ticker.upper(), "horizon": horizon, "synthetic": synthetic,
            "results": results, "best_model": best[0]}


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = parse_csv_upload(content)
    except Exception as exc:
        raise HTTPException(400, f"CSV parse error: {exc}")
    stats = headline_stats(df)
    return {"filename": file.filename, "rows": len(df), "stats": stats,
            "candles": to_candles(df.tail(400))}


def build_narrative(ticker: str, stats: dict, anom: dict, fc: dict, period: str) -> str:
    n_crit = anom["by_severity"].get("Critical", 0)
    n_med = anom["by_severity"].get("Medium", 0)
    n = anom["count"]
    direction = fc["direction"]
    proba = fc.get("continuation_probability", 0.5)
    m = fc["metrics"]
    risk = anom["risk_score"]
    risk_label = "elevated" if risk > 60 else "moderate" if risk > 30 else "contained"
    stat_line = (f"{ticker} closed at ${stats['price']} ({stats['change_pct']:+.2f}% d/d, "
                 f"{stats['period_change_pct']:+.1f}% over {period}) with ATR {stats['atr']} "
                 f"and RSI {stats['rsi']}.")
    if n == 0:
        anom_line = f"No significant structural anomalies detected; anomaly risk is {risk_label} ({risk}/100)."
    else:
        anom_line = (f"Detected {n} ensemble anomaly event(s) — {n_crit} critical, {n_med} medium — "
                     f"with an active anomaly risk score of {risk}/100 ({risk_label}).")
    fc_line = (f"The {fc['model']} model forecasts a {direction} trajectory over the next "
               f"{fc['horizon']} trading days with a {proba*100:.0f}% continuation probability "
               f"(backtest RMSE {m['rmse']}, MAPE {m['mape']}%, directional accuracy {m['directional_accuracy']}%).")
    action = ("Risk controls advised: tighten stops and reduce size into forecast dispersion."
              if risk > 60 or direction == "bearish" else
              "Momentum constructive but respect the 95% confidence band for position sizing.")
    return f"{stat_line} {anom_line} {fc_line} {action}"


@app.get("/api/anomaly-log")
def anomaly_log(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(AnomalyLog).order_by(AnomalyLog.id.desc()).limit(limit).all()
    return [{"ticker": r.ticker, "date": r.date, "price": r.price, "severity": r.severity,
             "type": r.type, "z_score": r.z_score} for r in rows]
