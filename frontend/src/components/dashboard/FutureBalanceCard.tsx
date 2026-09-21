import React, { useState } from "react";
import { TrendingUp, ArrowUpRight, ShieldCheck } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

interface ForecastScenarios {
  expected: number;
  high_spending: number;
  low_spending: number;
}

interface FutureBalanceProps {
  projectedMonthEndBalance?: number;
  scenarios?: ForecastScenarios;
  chartData?: Array<{
    day: string;
    expected: number;
    high_spend: number;
    low_spend: number;
  }>;
  dailyBurnRate?: number;
  currency?: string;
  onViewForecastPage?: () => void;
}

export const FutureBalanceCard: React.FC<FutureBalanceProps> = ({
  projectedMonthEndBalance,
  scenarios,
  chartData,
  dailyBurnRate,
  currency = "INR",
  onViewForecastPage,
}) => {
  const symbol = currency === "USD" ? "$" : currency === "EUR" ? "€" : "₹";
  const [activeScenario, setActiveScenario] = useState<"all" | "expected" | "high" | "low">("all");

  const hasChartData = Array.isArray(chartData) && chartData.length > 0;

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden flex flex-col justify-between">
      {/* Glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Future Projection</h3>
              <p className="text-xs text-slate-500">End-of-Month Solvency Simulation</p>
            </div>
          </div>

          {/* Scenario Filter Pills */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900/80 border border-white/5 text-[11px] font-semibold">
            <button
              onClick={() => setActiveScenario("all")}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeScenario === "all" ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40" : "text-slate-400 hover:text-white"
              }`}
            >
              All Scenarios
            </button>
            <button
              onClick={() => setActiveScenario("expected")}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeScenario === "expected" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "text-slate-400 hover:text-white"
              }`}
            >
              Expected
            </button>
            <button
              onClick={() => setActiveScenario("high")}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeScenario === "high" ? "bg-rose-500/20 text-rose-300 border border-rose-500/40" : "text-slate-400 hover:text-white"
              }`}
            >
              High Spend
            </button>
            <button
              onClick={() => setActiveScenario("low")}
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                activeScenario === "low" ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "text-slate-400 hover:text-white"
              }`}
            >
              Optimized
            </button>
          </div>
        </div>

        {/* Hero Value */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-4">
          <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-white/5 sm:col-span-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Projected Month-End Balance
            </span>
            <div className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
              {projectedMonthEndBalance !== undefined ? `${symbol}${projectedMonthEndBalance.toLocaleString("en-IN")}` : "—"}
            </div>
            <p className="text-[11px] text-emerald-400 font-medium mt-1 flex items-center gap-1">
              {projectedMonthEndBalance !== undefined ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {projectedMonthEndBalance >= 0 ? "Positive solvency margin" : "Deficit alert"}
                </>
              ) : (
                <span className="text-slate-500 font-normal">Simulation pending transaction history</span>
              )}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-white/5 flex flex-col justify-center sm:col-span-2">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500">Expected</div>
                <div className="text-sm font-bold text-emerald-400 mt-0.5">
                  {scenarios?.expected !== undefined ? `${symbol}${scenarios.expected.toLocaleString("en-IN")}` : "—"}
                </div>
              </div>
              <div className="border-x border-white/5 px-1">
                <div className="text-[10px] uppercase font-bold text-slate-500">+20% Spend</div>
                <div className="text-sm font-bold text-rose-400 mt-0.5">
                  {scenarios?.high_spending !== undefined ? `${symbol}${scenarios.high_spending.toLocaleString("en-IN")}` : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500">Optimized (-15%)</div>
                <div className="text-sm font-bold text-cyan-400 mt-0.5">
                  {scenarios?.low_spending !== undefined ? `${symbol}${scenarios.low_spending.toLocaleString("en-IN")}` : "—"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Trajectory Area Chart */}
        <div className="h-44 sm:h-48 w-full mt-2">
          {hasChartData ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorExpected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} vertical={false} />
                <XAxis dataKey="day" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#64748b"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(val) => `${symbol}${val >= 1000 ? `${Math.round(val / 1000)}k` : val}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "rgba(255,255,255,0.1)",
                    borderRadius: "1rem",
                    fontSize: "12px",
                  }}
                  formatter={(value: any) => [`${symbol}${Number(value).toLocaleString("en-IN")}`, ""]}
                />
                {(activeScenario === "all" || activeScenario === "low") && (
                  <Area
                    type="monotone"
                    dataKey="low_spend"
                    name="Optimized Plan"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorLow)"
                  />
                )}
                {(activeScenario === "all" || activeScenario === "expected") && (
                  <Area
                    type="monotone"
                    dataKey="expected"
                    name="Expected Trajectory"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorExpected)"
                  />
                )}
                {(activeScenario === "all" || activeScenario === "high") && (
                  <Area
                    type="monotone"
                    dataKey="high_spend"
                    name="High Spending Risk"
                    stroke="#f43f5e"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    fillOpacity={1}
                    fill="url(#colorHigh)"
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full w-full flex flex-col items-center justify-center rounded-2xl bg-slate-900/40 border border-white/5 text-center p-4">
              <span className="text-xs font-semibold text-slate-400">Trajectory Chart Unavailable</span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Forecast curves generate automatically as monthly expense records accumulate.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      {onViewForecastPage && (
        <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
          <span className="text-[11px] text-slate-500">
            Current burn rate: {dailyBurnRate !== undefined ? `${symbol}${dailyBurnRate.toLocaleString("en-IN")}/day` : "—"}
          </span>
          <button
            onClick={onViewForecastPage}
            className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 group transition-colors text-[11px]"
          >
            Detailed forecast analytics <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      )}
    </div>
  );
};
