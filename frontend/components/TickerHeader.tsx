"use client";
import { Activity, ArrowDownRight, ArrowUpRight, TriangleAlert } from "lucide-react";
import { TICKERS } from "../lib/api";
import { fmtPct, fmtUSD, riskLabel } from "../lib/utils";

export default function TickerHeader({ ticker, setTicker, stats, forecast, risk, synthetic }: any) {
  const chg = stats?.change_pct ?? 0;
  const up = chg >= 0;
  const dir = forecast?.direction ?? "—";
  const rl = riskLabel(risk ?? 0);
  const cards = [
    { label: "Current Price", value: fmtUSD(stats?.price), sub: `${fmtPct(chg)} d/d`,
      icon: up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />,
      color: up ? "#10B981" : "#EF4444" },
    { label: "Volatility (20d ann.)", value: stats ? `${(stats.volatility * 100).toFixed(1)}%` : "—",
      sub: `ATR ${stats?.atr ?? "—"} · RSI ${stats?.rsi ?? "—"}`, icon: <Activity size={14} />, color: "#E5E9F0" },
    { label: "30-Day Forecast", value: dir.toUpperCase(), sub: `${((forecast?.continuation_probability ?? 0) * 100).toFixed(0)}% continuation · ${forecast?.model ?? ""}`,
      icon: <Activity size={14} />, color: dir === "bullish" ? "#10B981" : "#EF4444" },
    { label: "Anomaly Risk", value: `${risk ?? 0}/100 ${rl.label}`, sub: "IsolationForest + Z + Bollinger",
      icon: <TriangleAlert size={14} />, color: rl.color },
  ];
  return (
    <header className="flex flex-col gap-3 border-b border-[#1E2532] bg-[#0B0E14] px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-[#10B981] font-black text-black">α</div>
          <div>
            <div className="text-sm font-bold tracking-wide">AlphaQuant AI</div>
            <div className="text-[10px] text-slate-400">QUANT TERMINAL · {synthetic ? "SYNTHETIC FEED (GBM)" : "LIVE FEED"}</div>
          </div>
        </div>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)}
          className="rounded border border-[#1E2532] bg-[#11151F] px-3 py-2 text-sm font-semibold outline-none">
          {TICKERS.map((t) => <option key={t}>{t}</option>)}
        </select>
        {synthetic && <span className="rounded bg-[#F59E0B]/15 px-2 py-1 text-[11px] font-bold text-[#F59E0B]">FALLBACK MODE</span>}
        <div className="ml-auto hidden text-[11px] text-slate-400 md:block">DARK TERMINAL · ARIMA / PROPHET / ETS · ISOLATION FOREST</div>
      </div>
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-lg border border-[#1E2532] bg-[#11151F] px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-slate-400">{c.label}</div>
            <div className="flex items-center gap-1 text-lg font-bold" style={{ color: c.color }}>
              {c.icon}{c.value}
            </div>
            <div className="truncate text-[11px] text-slate-400">{c.sub}</div>
          </div>
        ))}
      </div>
    </header>
  );
}
