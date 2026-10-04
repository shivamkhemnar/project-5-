"use client";

export default function ForecastOverlay({ forecast }: any) {
  if (!forecast) return null;
  const m = forecast.metrics ?? {};
  const items = [
    ["Model", `${forecast.model} (req: ${forecast.requested_model})`],
    ["Direction", forecast.direction],
    ["Continuation P", `${((forecast.continuation_probability ?? 0) * 100).toFixed(1)}%`],
    ["RMSE", m.rmse], ["MAE", m.mae], ["MAPE", m.mape != null ? `${m.mape}%` : "—"],
    ["Dir. accuracy", m.directional_accuracy != null ? `${m.directional_accuracy}%` : "—"],
  ];
  return (
    <div className="grid grid-cols-2 gap-2 rounded-lg border border-[#1E2532] bg-[#11151F] p-3 text-xs md:grid-cols-4">
      {items.map(([k, v]) => (
        <div key={k}>
          <div className="text-[10px] uppercase text-slate-400">{k}</div>
          <div className="font-bold">{String(v)}</div>
        </div>
      ))}
      <div className="col-span-2 flex items-center gap-2 text-[11px] text-slate-400 md:col-span-4">
        <span className="inline-block h-1 w-6 bg-[#F59E0B]" /> point forecast
        <span className="inline-block h-3 w-6 bg-[#F59E0B]/30" /> 80% band
        <span className="inline-block h-3 w-6 bg-[#10B981]/20" /> 95% band
      </div>
    </div>
  );
}
