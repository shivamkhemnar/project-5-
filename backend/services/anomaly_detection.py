"""Ensemble anomaly detection: Isolation Forest + rolling z-score + Bollinger violations."""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.03, window: int = 20) -> dict:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    contamination = float(min(max(contamination, 0.005), 0.15))
    d = df.sort_values("date").reset_index(drop=True).copy()
    close = d["close"].astype(float)
    ret = close.pct_change().fillna(0)
    vol = d["volume"].astype(float) if "volume" in d else pd.Series(np.ones(len(d)))
    vol_chg = vol.pct_change().fillna(0).replace([np.inf, -np.inf], 0)

    roll_mean = close.rolling(window).mean()
    roll_std = close.rolling(window).std().replace(0, np.nan).bfill()
    z = ((close - roll_mean) / (roll_std + 1e-12)).fillna(0)
    upper_bb = roll_mean + 2 * roll_std
    lower_bb = roll_mean - 2 * roll_std
    bb_break = ((close > upper_bb) | (close < lower_bb)).astype(int)

    feats = np.column_stack([ret.fillna(0).to_numpy(),
                             z.to_numpy(),
                             np.log1p(vol.abs()).to_numpy() * 0 + vol_chg.to_numpy(),
                             bb_break.to_numpy()])
    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
    scaled = StandardScaler().fit_transform(feats)
    iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    iso_flag = (iso.fit_predict(scaled) == -1).astype(int)
    iso_score = -iso.score_samples(scaled)  # higher = more anomalous

    z_flag = (z.abs() > 3.0).astype(int).to_numpy()
    votes = iso_flag + z_flag + bb_break.to_numpy()
    is_anomaly = votes >= 2

    anomalies: list[dict] = []
    for i in np.where(is_anomaly)[0]:
        r = d.iloc[i]
        abs_z = abs(float(z.iloc[i]))
        ret_i = abs(float(ret.iloc[i]))
        # severity rules
        if ret_i > 0.07 or abs_z > 4.5:
            severity = "Critical"
        elif ret_i > 0.03 or abs_z > 3.0 or float(vol_chg.iloc[i]) > 2.0:
            severity = "Medium"
        else:
            severity = "Low"
        kind = ("flash_crash" if float(ret.iloc[i]) < -0.04 else
                "spike" if float(ret.iloc[i]) > 0.04 else
                "volatility_break" if bb_break.iloc[i] else "volume_spike")
        anomalies.append({
            "date": pd.Timestamp(r["date"]).strftime("%Y-%m-%d"),
            "index": int(i),
            "price": round(float(r["close"]), 2),
            "return": round(float(ret.iloc[i]), 4),
            "z_score": round(float(z.iloc[i]), 2),
            "severity": severity,
            "type": kind,
            "votes": int(votes[i]),
            "iso_score": round(float(iso_score[i]), 3),
            "volume": int(r["volume"]) if "volume" in d and pd.notna(r["volume"]) else 0,
        })

    # risk score 0-100: weighted recent anomalies + current z/volatility
    risk = 0.0
    if anomalies:
        w = {"Low": 1, "Medium": 2.5, "Critical": 5}
        total = sum(w[a["severity"]] for a in anomalies)
        recency = sum(w[a["severity"]] * (0.5 + 0.5 * (a["index"] / max(len(d) - 1, 1))) for a in anomalies)
        risk = min(100.0, (recency * 6 + min(abs(float(z.iloc[-1])) * 8, 30) +
                            min(abs(float(ret.iloc[-1])) * 400, 20)))
    else:
        risk = min(100.0, abs(float(z.iloc[-1])) * 6 + abs(float(ret.iloc[-1])) * 150)

    by_sev = {s: sum(1 for a in anomalies if a["severity"] == s) for s in ("Low", "Medium", "Critical")}
    return {"anomalies": anomalies, "count": len(anomalies), "by_severity": by_sev,
            "risk_score": round(float(risk), 1), "contamination": contamination,
            "method": "isolation_forest+zscore+bollinger(2/3 votes)"}
