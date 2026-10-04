"use client";
import { useState } from "react";
import AnomalyLogTable from "../components/AnomalyLogTable";
import ControlBar from "../components/ControlBar";
import FinancialChart from "../components/FinancialChart";
import ForecastOverlay from "../components/ForecastOverlay";
import NarrativeInsights from "../components/NarrativeInsights";
import TickerHeader from "../components/TickerHeader";
import { useMarketData } from "../hooks/useMarketData";

export default function Dashboard() {
  const [ticker, setTicker] = useState("NVDA");
  const [period, setPeriod] = useState("1Y");
  const [model, setModel] = useState("prophet");
  const [horizon, setHorizon] = useState(30);
  const [contamination, setContamination] = useState(0.03);
  const [chartType, setChartType] = useState<"candles" | "line">("candles");
  const [showForecast, setShowForecast] = useState(true);
  const [showAnomalies, setShowAnomalies] = useState(true);

  const d = useMarketData(ticker, period, model, horizon, contamination);

  return (
    <main className="mx-auto flex min-h-screen max-w-[1500px] flex-col gap-3 p-3">
      <TickerHeader ticker={ticker} setTicker={setTicker} stats={d.stats}
        forecast={d.forecast} risk={d.anomalies?.risk_score} synthetic={d.synthetic} />
      <ControlBar period={period} setPeriod={setPeriod} model={model} setModel={setModel}
        contamination={contamination} setContamination={setContamination}
        horizon={horizon} setHorizon={setHorizon} chartType={chartType} setChartType={setChartType}
        showForecast={showForecast} setShowForecast={setShowForecast}
        showAnomalies={showAnomalies} setShowAnomalies={setShowAnomalies}
        loading={d.loading} onRefresh={d.refresh} />
      {d.error && <div className="rounded border border-red-500 bg-red-500/10 p-2 text-sm text-red-300">Backend unreachable: {d.error} — is FastAPI running on :8000?</div>}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-3">
          <FinancialChart candles={d.candles} forecast={d.forecast} anomalies={d.anomalies}
            chartType={chartType} showForecast={showForecast} showAnomalies={showAnomalies} />
          <ForecastOverlay forecast={d.forecast} />
          <AnomalyLogTable anomalies={d.anomalies} />
          <a href="/backtesting" className="text-xs text-slate-400 underline">Open model backtesting view →</a>
        </div>
        <NarrativeInsights narrative={d.narrative} stats={d.stats} anomalies={d.anomalies} forecast={d.forecast} />
      </div>
    </main>
  );
}
