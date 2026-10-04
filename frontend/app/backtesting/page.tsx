"use client";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useForecast } from "../../hooks/useForecast";

export default function BacktestingPage() {
  const [ticker, setTicker] = useState("NVDA");
  const [horizon, setHorizon] = useState(30);
  const { data, loading } = useForecast(ticker, "1Y", horizon);
  const rows = data?.results ? Object.entries(data.results).filter(([, v]: any) => v.rmse).map(([m, v]: any) => ({ model: m, RMSE: v.rmse, MAE: v.mae, DirAcc: v.directional_accuracy })) : [];
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-4 p-6">
      <a href="/" className="text-xs text-slate-400 underline">← Back to terminal</a>
      <h1 className="text-2xl font-black">Model Backtesting</h1>
      <p className="text-sm text-slate-400">Hold-out evaluation over the last {horizon} trading days. Best model: <b className="text-[#10B981]">{data?.best_model ?? "…"}</b></p>
      <div className="flex gap-2 text-sm">
        <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} className="rounded border border-[#1E2532] bg-[#11151F] px-2 py-1" />
        <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="rounded border border-[#1E2532] bg-[#11151F] px-2 py-1">
          {[14, 30, 60].map((h) => <option key={h} value={h}>{h} days</option>)}
        </select>
      </div>
      {loading ? <div className="text-slate-400">Scoring models…</div> : (
        <div className="h-80 rounded border border-[#1E2532] bg-[#11151F] p-3">
          <ResponsiveContainer>
            <BarChart data={rows}>
              <CartesianGrid stroke="#1E2532" /><XAxis dataKey="model" stroke="#9aa4b2" />
              <YAxis stroke="#9aa4b2" /><Tooltip contentStyle={{ background: "#11151F" }} /><Legend />
              <Bar dataKey="RMSE" fill="#EF4444" /><Bar dataKey="MAE" fill="#F59E0B" /><Bar dataKey="DirAcc" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <pre className="overflow-auto rounded bg-black/40 p-3 text-xs">{JSON.stringify(data, null, 2)}</pre>
    </main>
  );
}
