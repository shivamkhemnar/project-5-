"use client";
import { useEffect, useRef } from "react";

export default function FinancialChart({ candles, forecast, anomalies, chartType, showForecast, showAnomalies }: any) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    let disposed = false;
    (async () => {
      const { createChart, ColorType, CrosshairMode } = await import("lightweight-charts");
      if (!ref.current || disposed) return;
      ref.current.innerHTML = "";
      const chart = createChart(ref.current, {
        layout: { background: { type: ColorType.Solid, color: "#0B0E14" }, textColor: "#9aa4b2" },
        grid: { vertLines: { color: "#141a26" }, horzLines: { color: "#141a26" } },
        crosshair: { mode: CrosshairMode.Normal },
        width: ref.current.clientWidth, height: 460,
        timeScale: { timeVisible: true },
      });
      chartRef.current = chart;
      const data = (candles ?? []).map((c: any) => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
      if (chartType === "candles") {
        const s = chart.addCandlestickSeries({ upColor: "#10B981", downColor: "#EF4444", wickUpColor: "#10B981", wickDownColor: "#EF4444", borderVisible: false });
        s.setData(data);
      } else {
        const s = chart.addLineSeries({ color: "#10B981", lineWidth: 2 });
        s.setData(data.map((d: any) => ({ time: d.time, value: d.close })));
      }
      // volume
      const vol = chart.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" } });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
      vol.setData((candles ?? []).map((c: any) => ({
        time: c.time, value: c.volume ?? 0,
        color: c.close >= c.open ? "rgba(16,185,129,.4)" : "rgba(239,68,68,.4)",
      })));
      // forecast fan
      if (showForecast && forecast?.forecast?.length) {
        const f = forecast.forecast;
        const t0 = (candles?.length ? candles[candles.length - 1].time : Math.floor(Date.now() / 1000));
        const toT = (d: string, i: number) => t0 + (i + 1) * 86400;
        const line = (k: string, color: string, width = 2, dash?: number[]) => {
          const s = chart.addLineSeries({ color, lineWidth: width as any, lineStyle: dash ? 2 : 0, priceLineVisible: false, lastValueVisible: true });
          s.setData(f.map((r: any, i: number) => ({ time: toT(r.date, i), value: r[k] })));
        };
        // 95 band as two lines + 80 band
        line("lower_95", "rgba(16,185,129,.35)", 1);
        line("upper_95", "rgba(16,185,129,.35)", 1);
        line("lower_80", "rgba(245,158,11,.55)", 1);
        line("upper_80", "rgba(245,158,11,.55)", 1);
        line("yhat", "#F59E0B", 2);
      }
      // anomalies
      if (showAnomalies && anomalies?.anomalies?.length) {
        const priceByTime = new Map((candles ?? []).map((c: any) => [c.time, c.close]));
        const dateToTime = new Map((candles ?? []).map((c: any) => [c.date, c.time]));
        const markers = anomalies.anomalies.map((a: any) => {
          const t = dateToTime.get(a.date) ?? [...priceByTime.keys()].find(() => false);
          return { t, a };
        }).filter((x: any) => x.t).map(({ t, a }: any) => ({
          time: t,
          position: a.return < 0 ? "aboveBar" : "belowBar",
          color: a.severity === "Critical" ? "#EF4444" : "#F59E0B",
          shape: a.severity === "Critical" ? "arrowDown" : "circle",
          text: `${a.severity[0]}:${a.type}`,
        }));
        try {
          const serieses = chart as any;
          // attach to first series via setMarkers if available
          const allSeries: any[] = [];
          // lightweight-charts v4: markers on series; re-add line series handle is lost, so use timeScale markers via first series trick:
          // simplest: create invisible line series at close to host markers
          const host = chart.addLineSeries({ color: "rgba(0,0,0,0)", lineVisible: false, priceLineVisible: false, lastValueVisible: false });
          host.setData((candles ?? []).map((c: any) => ({ time: c.time, value: c.close })));
          (host as any).setMarkers(markers.slice(0, 100));
        } catch {}
      }
      chart.timeScale().scrollToRealTime?.();
      const onResize = () => chart.applyOptions({ width: ref.current!.clientWidth });
      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    })();
    return () => { disposed = true; try { chartRef.current?.remove(); } catch {} };
  }, [candles, forecast, anomalies, chartType, showForecast, showAnomalies]);

  return <div ref={ref} className="w-full overflow-hidden rounded-lg border border-[#1E2532]" />;
}
