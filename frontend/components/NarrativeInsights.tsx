"use client";
import { motion } from "framer-motion";
import { BrainCircuit } from "lucide-react";

export default function NarrativeInsights({ narrative, stats, anomalies, forecast }: any) {
  return (
    <motion.aside initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
      className="flex flex-col gap-2 rounded-lg border border-[#1E2532] bg-[#11151F] p-3">
      <div className="flex items-center gap-2 text-xs font-bold tracking-wide">
        <BrainCircuit size={14} className="text-[#10B981]" /> AUTOMATED NARRATIVE INSIGHTS
      </div>
      <p className="text-[13px] leading-relaxed text-slate-200">{narrative || "Loading insights…"}</p>
      <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
        {[["Critical", anomalies?.by_severity?.Critical ?? 0, "#EF4444"],
          ["Medium", anomalies?.by_severity?.Medium ?? 0, "#F59E0B"],
          ["Low", anomalies?.by_severity?.Low ?? 0, "#10B981"]].map(([k, v, c]) => (
          <div key={k as string} className="rounded border border-[#1E2532] p-2">
            <div className="text-lg font-black" style={{ color: c as string }}>{v}</div>
            <div className="text-slate-400">{k}</div>
          </div>
        ))}
      </div>
      {stats && (
        <div className="text-[11px] text-slate-400">
          52W range ${stats.low_52w} – ${stats.high_52w} · Vol {stats.volume?.toLocaleString()} · Stationary signal from ADF test drives {forecast?.model ?? "—"} selection.
        </div>
      )}
    </motion.aside>
  );
}
