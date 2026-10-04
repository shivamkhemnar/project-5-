"use client";

const color: Record<string, string> = { Critical: "#EF4444", Medium: "#F59E0B", Low: "#10B981" };

export default function AnomalyLogTable({ anomalies }: any) {
  const rows = anomalies?.anomalies ?? [];
  return (
    <div className="rounded-lg border border-[#1E2532] bg-[#11151F]">
      <div className="flex items-center justify-between border-b border-[#1E2532] px-3 py-2 text-xs font-bold">
        <span>ANOMALY LOG ({anomalies?.count ?? 0}) · RISK {anomalies?.risk_score ?? 0}/100</span>
        <span className="text-[10px] font-normal text-slate-400">{anomalies?.method}</span>
      </div>
      <div className="scroll-thin max-h-64 overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-[#0B0E14] text-slate-400">
            <tr><th className="p-2 text-left">Date</th><th className="p-2 text-right">Price</th>
              <th className="p-2 text-right">Ret</th><th className="p-2 text-right">Z</th>
              <th className="p-2 text-left">Severity</th><th className="p-2 text-left">Type</th></tr>
          </thead>
          <tbody>
            {rows.map((a: any, i: number) => (
              <tr key={i} className="border-t border-[#1a2130]">
                <td className="p-2">{a.date}</td>
                <td className="p-2 text-right">${a.price}</td>
                <td className="p-2 text-right" style={{ color: a.return < 0 ? "#EF4444" : "#10B981" }}>{(a.return * 100).toFixed(2)}%</td>
                <td className="p-2 text-right">{a.z_score}</td>
                <td className="p-2"><span className={a.severity === "Critical" ? "pulse-dot rounded px-1 font-bold" : "rounded px-1 font-bold"}
                  style={{ background: `${color[a.severity]}22`, color: color[a.severity] }}>{a.severity}</span></td>
                <td className="p-2 text-slate-300">{a.type}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} className="p-4 text-center text-slate-500">No anomalies at current sensitivity.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
