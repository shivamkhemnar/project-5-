"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function useForecast(ticker: string, period: string, horizon: number) {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setLoading(true);
    api.backtest(ticker, period, horizon)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [ticker, period, horizon]);
  return { data, loading };
}
