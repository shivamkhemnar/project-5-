"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";

export interface DashboardState {
  candles: any[];
  stats: any | null;
  forecast: any | null;
  anomalies: any | null;
  narrative: string;
  synthetic: boolean;
  loading: boolean;
  error: string | null;
}

export function useMarketData(
  ticker: string,
  period: string,
  model: string,
  horizon: number,
  contamination: number
) {
  const [state, setState] = useState<DashboardState>({
    candles: [], stats: null, forecast: null, anomalies: null,
    narrative: "", synthetic: false, loading: true, error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [mkt, fc, anom, sum] = await Promise.all([
        api.market(ticker, period),
        api.forecast({ ticker, period, horizon, model, contamination }),
        api.anomalies({ ticker, period, contamination }),
        api.summary(ticker, { period, horizon, model, contamination }),
      ]);
      setState({
        candles: mkt.candles,
        stats: mkt.stats,
        forecast: fc,
        anomalies: anom,
        narrative: sum.narrative,
        synthetic: mkt.synthetic || fc.synthetic,
        loading: false,
        error: null,
      });
    } catch (e: any) {
      setState((s) => ({ ...s, loading: false, error: e.message }));
    }
  }, [ticker, period, model, horizon, contamination]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}
