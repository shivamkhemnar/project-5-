export const fmtUSD = (v: number | null | undefined) =>
  v == null || Number.isNaN(v)
    ? "—"
    : v >= 1000
    ? "$" + v.toLocaleString("en-US", { maximumFractionDigits: 2 })
    : "$" + Number(v).toFixed(2);

export const fmtPct = (v: number | null | undefined) =>
  v == null ? "—" : `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%`;

export const cls = (...xs: (string | false | null | undefined)[]) =>
  xs.filter(Boolean).join(" ");

export function riskLabel(score: number) {
  if (score > 60) return { label: "ELEVATED", color: "#EF4444" };
  if (score > 30) return { label: "MODERATE", color: "#F59E0B" };
  return { label: "CONTAINED", color: "#10B981" };
}
