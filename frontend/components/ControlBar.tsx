"use client";
import { MODELS, PERIODS } from "../lib/api";

export default function ControlBar(p: any) {
  const { period, setPeriod, model, setModel, contamination, setContamination,
    horizon, setHorizon, chartType, setChartType, showForecast, setShowForecast,
    showAnomalies, setShowAnomalies, loading, onRefresh } = p;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#1E2532] bg-[#11151F] px-3 py-2 text-xs">
      <div className="flex gap-1">
        {PERIODS.map((x) => (
          <button key={x} onClick={() => setPeriod(x)}
            className={`rounded px-2 py-1 font-bold ${period === x ? "bg-[#10B981] text-black" : "bg-[#1a2130] text-slate-300"}`}>{x}</button>
        ))}
      </div>
      <label className="flex items-center gap-1">Model
        <select value={model} onChange={(e) => setModel(e.target.value)}
          className="rounded border border-[#1E2532] bg-[#0B0E14] px-2 py-1">{MODELS.map((m) => <option key={m}>{m}</option>)}</select>
      </label>
      <label className="flex items-center gap-1">Horizon
        <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}
          className="rounded border border-[#1E2532] bg-[#0B0E14] px-2 py-1">
          {[14, 30, 90].map((h) => <option key={h} value={h}>{h}d</option>)}
        </select>
      </label>
      <label className="flex items-center gap-2">Sensitivity {contamination.toFixed(2)}
        <input type="range" min={0.01} max={0.10} step={0.01} value={contamination}
          onChange={(e) => setContamination(Number(e.target.value))} className="w-28 accent-[#F59E0B]" />
      </label>
      <div className="flex gap-1">
        {(["candles", "line"] as const).map((t) => (
          <button key={t} onClick={() => setChartType(t)}
            className={`rounded px-2 py-1 font-bold ${chartType === t ? "bg-white text-black" : "bg-[#1a2130] text-slate-300"}`}>
            {t === "candles" ? "Candlestick" : "Line"}</button>
        ))}
      </div>
      <button onClick={() => setShowForecast(!showForecast)}
        className={`rounded px-2 py-1 font-bold ${showForecast ? "bg-[#10B981] text-black" : "bg-[#1a2130]"}`}>Forecast</button>
      <button onClick={() => setShowAnomalies(!showAnomalies)}
        className={`rounded px-2 py-1 font-bold ${showAnomalies ? "bg-[#EF4444] text-white" : "bg-[#1a2130]"}`}>Anomalies</button>
      <button onClick={onRefresh} disabled={loading}
        className="ml-auto rounded bg-white px-3 py-1 font-bold text-black disabled:opacity-50">
        {loading ? "LOADING…" : "REFRESH"}</button>
    </div>
  );
}
