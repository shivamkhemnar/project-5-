const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  market: (ticker: string, period = "1Y") =>
    req(`/api/market-data/${ticker}?period=${period}`),
  forecast: (body: object) =>
    req(`/api/forecast`, { method: "POST", body: JSON.stringify(body) }),
  anomalies: (body: object) =>
    req(`/api/anomalies`, { method: "POST", body: JSON.stringify(body) }),
  summary: (ticker: string, p: Record<string, string | number>) => {
    const q = new URLSearchParams(
      Object.fromEntries(Object.entries(p).map(([k, v]) => [k, String(v)]))
    ).toString();
    return req(`/api/summary/${ticker}?${q}`);
  },
  backtest: (ticker: string, period = "1Y", horizon = 30) =>
    req(`/api/backtest?ticker=${ticker}&period=${period}&horizon=${horizon}`),
};

export const TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "BTC-USD", "ETH-USD", "SPY"];
export const PERIODS = ["1M", "3M", "6M", "1Y", "2Y", "5Y"];
export const MODELS = ["prophet", "arima", "holt-winters", "ets", "sma"];
