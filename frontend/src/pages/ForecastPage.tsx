import React, { useState, useEffect, useCallback } from "react";
import { Header } from "../components/Header";
import { api } from "../services/api";
import {
  Sparkles, Loader2, Target, RefreshCw,
  AlertTriangle, ShieldCheck, LineChart as ChartIcon,
  TrendingUp, TrendingDown, Minus, Info,
  ArrowUpRight, ArrowDownRight, AlertCircle
} from "lucide-react";
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
  AreaChart, Area
} from "recharts";

// ── Types ──────────────────────────────────────────────────────────────────────
interface ForecastScenarios {
  projected_month_end_balance: number;
  scenarios: {
    expected: number;
    high_spending: number;
    low_spending: number;
  };
  chart_data: Array<{
    day: string;
    expected: number;
    high_spend: number;
    low_spend: number;
  }>;
  daily_burn_rate: number;
}

interface ForecastAssumptions {
  method: string;
  income_source: string;
  inflation_rate_pct: number;
  expense_data_months: number;
  has_sufficient_history: boolean;
  disclaimer: string;
}

interface Projections {
  projected_income: number;
  projected_expense: number;
  projected_savings: number;
  risk_trend: string;
  goal_completion_months: number;
  goal_completion_date: string;
  goal_completion_title: string;
  chart_data: Array<{
    month: string;
    projected_income: number;
    projected_expense: number;
    projected_savings: number;
  }>;
  forecast_scenarios: ForecastScenarios | null;
  has_sufficient_history: boolean;
  assumptions: ForecastAssumptions;
}

// ── Helpers ────────────────────────────────────────────────────────────────────
/** Safely formats a numeric value as ₹ currency. Returns "—" if the value is
 *  null, undefined, NaN, or Infinity so we never show misleading zeros. */
function fmtCurrency(value: number | undefined | null): string {
  if (value === null || value === undefined || !isFinite(value)) return "—";
  return "₹" + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function fmtNumber(value: number | undefined | null): string {
  if (value === null || value === undefined || !isFinite(value)) return "—";
  return String(value);
}

/** Returns true only when value is a real finite number (not null/undefined/NaN). */
function isValidNumber(v: unknown): v is number {
  return typeof v === "number" && isFinite(v);
}

/** Savings efficiency: ratio of projected savings to income, 0–100, clamped. */
function savingsEfficiencyPct(savings: number | undefined | null, income: number | undefined | null): number {
  if (!isValidNumber(savings) || !isValidNumber(income) || income <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((savings / income) * 100)));
}

// ── Scenario Card ──────────────────────────────────────────────────────────────
interface ScenarioCardProps {
  label: string;
  description: string;
  balance: number | undefined | null;
  color: "emerald" | "rose" | "cyan";
  Icon: React.ElementType;
}
const ScenarioCard: React.FC<ScenarioCardProps> = ({ label, description, balance, color, Icon }) => {
  const colorMap = {
    emerald: { text: "text-emerald-400", border: "border-emerald-500/20", bg: "bg-emerald-500/10" },
    rose: { text: "text-rose-400", border: "border-rose-500/20", bg: "bg-rose-500/10" },
    cyan: { text: "text-cyan-400", border: "border-cyan-500/20", bg: "bg-cyan-500/10" },
  };
  const c = colorMap[color];
  return (
    <div className={`glass-panel p-5 rounded-2xl border ${c.border} flex flex-col gap-2`}>
      <div className={`w-8 h-8 rounded-xl ${c.bg} flex items-center justify-center ${c.text}`}>
        <Icon className="w-4 h-4" />
      </div>
      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{label}</span>
      <p className={`text-xl font-black ${isValidNumber(balance) ? c.text : "text-slate-500"}`}>
        {fmtCurrency(balance)}
      </p>
      <p className="text-[10px] text-slate-500 leading-relaxed">{description}</p>
    </div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────────────
export const ForecastPage: React.FC = () => {
  const [projections, setProjections] = useState<Projections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const loadProjections = useCallback(async (isRetry = false) => {
    if (isRetry) setRetrying(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await api.getProjections();
      setProjections(data);
    } catch (err: any) {
      const msg = err?.message || "Failed to load forecast data. Please try again.";
      setError(msg);
      console.error("Forecast load failed:", err);
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  }, []);

  useEffect(() => {
    loadProjections();
  }, [loadProjections]);

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <Header />
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <Loader2 className="w-12 h-12 text-emerald-400 animate-spin" />
          <div className="text-emerald-400 font-semibold tracking-wider text-xs">
            Computing Financial Trajectories…
          </div>
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <Header />
        <div className="flex-1 flex flex-col items-center justify-center gap-5 px-6">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <div className="text-center max-w-sm">
            <h2 className="text-white font-bold text-lg mb-1">Forecast Unavailable</h2>
            <p className="text-slate-400 text-sm">{error}</p>
          </div>
          <button
            onClick={() => loadProjections(true)}
            disabled={retrying}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-sm font-semibold hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
            {retrying ? "Retrying…" : "Retry"}
          </button>
        </div>
      </div>
    );
  }

  // ── Derived values (all guarded) ───────────────────────────────────────────
  const isRiskIncreasing = projections?.risk_trend?.toLowerCase().includes("increasing");
  const isRiskDecreasing = projections?.risk_trend?.toLowerCase().includes("decreasing");
  const hasChartData = Array.isArray(projections?.chart_data) && projections!.chart_data.length > 0;
  const hasScenarios = projections?.forecast_scenarios?.scenarios != null;
  const hasBalanceChartData =
    Array.isArray(projections?.forecast_scenarios?.chart_data) &&
    projections!.forecast_scenarios!.chart_data.length > 0;
  const hasGoalData = projections?.goal_completion_months != null &&
    projections.goal_completion_months > 0 &&
    projections?.goal_completion_date !== "N/A";
  const effPct = savingsEfficiencyPct(projections?.projected_savings, projections?.projected_income);
  const sufficientHistory = projections?.has_sufficient_history ?? false;

  const RiskIcon = isRiskIncreasing ? AlertTriangle : isRiskDecreasing ? TrendingDown : ShieldCheck;
  const riskColor = isRiskIncreasing ? "text-amber-500" : isRiskDecreasing ? "text-cyan-400" : "text-emerald-400";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-20">
      {/* Background glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none" />

      <Header />

      <main className="max-w-7xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-8 relative z-10">

        {/* ── Page header ────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h1 className="text-2xl font-black text-white">Financial Forecast</h1>
            </div>
            <button
              onClick={() => loadProjections(true)}
              disabled={retrying}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-white/10 text-slate-400 text-xs font-semibold hover:text-emerald-400 hover:border-emerald-500/30 transition-all disabled:opacity-50"
              title="Refresh forecast"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${retrying ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
          <p className="text-xs text-slate-400">
            Deterministic projections based on your recorded transaction history.
            Estimates reflect trends — they are not guaranteed outcomes.
          </p>
          {!sufficientHistory && (
            <div className="flex items-start gap-2 mt-1 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <Info className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-300">
                <strong>Limited history detected.</strong> Projections are based on fewer than 2 months of expense
                data and use a conservative average fallback. Add more transactions to improve forecast accuracy.
              </p>
            </div>
          )}
        </div>

        {/* ── Summary cards ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-3xl border border-white/5 space-y-1.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Projected Income</span>
            <h3 className="text-xl font-black text-emerald-400">{fmtCurrency(projections?.projected_income)}</h3>
            <p className="text-[9px] text-slate-500">Monthly income baseline</p>
          </div>

          <div className="glass-panel p-5 rounded-3xl border border-white/5 space-y-1.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Projected Expenses</span>
            <h3 className="text-xl font-black text-red-400">{fmtCurrency(projections?.projected_expense)}</h3>
            <p className="text-[9px] text-slate-500">
              {sufficientHistory ? "Linear-trend estimate" : "Average-based fallback"}
            </p>
          </div>

          <div className="glass-panel p-5 rounded-3xl border border-white/5 space-y-1.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Projected Net Savings</span>
            <h3 className={`text-xl font-black ${isValidNumber(projections?.projected_savings) && projections!.projected_savings >= 0 ? "text-blue-400" : "text-rose-400"}`}>
              {fmtCurrency(projections?.projected_savings)}
            </h3>
            <p className="text-[9px] text-slate-500">Income minus projected expenses</p>
          </div>

          <div className="glass-panel p-5 rounded-3xl border border-white/5 space-y-1.5">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Expense Risk Trend</span>
            <div className="flex items-center gap-1.5 mt-1">
              <RiskIcon className={`w-4 h-4 ${riskColor} ${isRiskIncreasing ? "animate-pulse" : ""}`} />
              <h3 className={`text-sm font-bold leading-tight ${riskColor}`}>
                {projections?.risk_trend || "Stable"}
              </h3>
            </div>
            <p className="text-[9px] text-slate-500">Based on current vs. prior-period spending</p>
          </div>
        </div>

        {/* ── 6-month cashflow chart + Goal completion panel ────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 lg:col-span-2 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-xs text-white font-bold uppercase tracking-wider">6-Month Cashflow Trend</span>
                <p className="text-[10px] text-slate-500 mt-0.5">1% monthly inflation growth applied to expense baseline</p>
              </div>
              <ChartIcon className="w-4 h-4 text-emerald-400 shrink-0" />
            </div>

            <div className="h-64 w-full">
              {!hasChartData ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2 rounded-2xl bg-slate-900/40 border border-white/5">
                  <ChartIcon className="w-8 h-8 text-slate-600" />
                  <span className="text-xs text-slate-500 font-semibold">Insufficient data for trend chart</span>
                  <p className="text-[10px] text-slate-600 max-w-xs">
                    Record at least one expense transaction to generate cashflow projections.
                  </p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={projections!.chart_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis
                      stroke="#94a3b8"
                      fontSize={10}
                      tickLine={false}
                      tickFormatter={(v) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "0.75rem" }}
                      formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, ""]}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line type="monotone" dataKey="projected_income" name="Projected Income" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                    <Line type="monotone" dataKey="projected_expense" name="Projected Expense" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="projected_savings" name="Projected Savings" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Goal completion */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <Target className="w-4 h-4" /> Savings Goal Progress
            </div>

            {hasGoalData ? (
              <>
                <p className="text-xs text-slate-400 leading-relaxed">
                  At your projected monthly savings rate, you are on track to complete:
                </p>
                <div className="bg-slate-900/40 p-4 rounded-2xl border border-white/5 space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-semibold">Goal:</span>
                    <span className="text-white font-bold text-right max-w-[130px] truncate" title={projections!.goal_completion_title}>
                      {projections!.goal_completion_title}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-semibold">Months Required:</span>
                    <span className="text-white font-bold">{fmtNumber(projections?.goal_completion_months)} months</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-semibold">Estimated Completion:</span>
                    <span className="text-emerald-400 font-bold">{projections?.goal_completion_date}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 rounded-2xl bg-slate-900/40 border border-white/5 py-8 px-4">
                <Target className="w-8 h-8 text-slate-600" />
                <span className="text-xs text-slate-500 font-semibold">No active goals</span>
                <p className="text-[10px] text-slate-600">
                  {!isValidNumber(projections?.projected_savings) || projections!.projected_savings <= 0
                    ? "Positive projected savings are needed to estimate goal completion."
                    : "Add a savings goal to see a completion estimate here."}
                </p>
              </div>
            )}

            {/* Savings efficiency */}
            <div className="mt-auto flex flex-col gap-2">
              <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                <span>Savings Efficiency</span>
                <span>{effPct}% of income</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${effPct >= 20 ? "bg-emerald-500" : effPct > 0 ? "bg-amber-500" : "bg-slate-600"}`}
                  style={{ width: `${effPct}%` }}
                />
              </div>
              <p className="text-[9px] text-slate-600">
                Target: ≥20% savings rate for healthy finances
              </p>
            </div>
          </div>
        </div>

        {/* ── Month-end balance scenarios ─────────────────────────────────── */}
        {hasScenarios && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">Month-End Balance Scenarios</h2>
            </div>
            <p className="text-xs text-slate-500 -mt-2">
              Projected end-of-month balance based on your current daily burn rate and remaining days in the month.
              These are estimates, not guarantees.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ScenarioCard
                label="Expected Outcome"
                description="If current daily spend rate holds for the rest of the month"
                balance={projections?.forecast_scenarios?.scenarios.expected}
                color="emerald"
                Icon={Minus}
              />
              <ScenarioCard
                label="High-Spending Risk"
                description="If expenses run 20% above current pace (overspend scenario)"
                balance={projections?.forecast_scenarios?.scenarios.high_spending}
                color="rose"
                Icon={ArrowUpRight}
              />
              <ScenarioCard
                label="Optimised Plan"
                description="If you trim spending 15% below current pace (disciplined scenario)"
                balance={projections?.forecast_scenarios?.scenarios.low_spending}
                color="cyan"
                Icon={ArrowDownRight}
              />
            </div>

            {/* Intra-month trajectory chart */}
            {hasBalanceChartData && (
              <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white font-bold uppercase tracking-wider">Intra-Month Balance Trajectory</span>
                  <span className="text-[10px] text-slate-500">
                    Daily burn: {fmtCurrency(projections?.forecast_scenarios?.daily_burn_rate)}/day
                  </span>
                </div>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={projections!.forecast_scenarios!.chart_data}>
                      <defs>
                        <linearGradient id="fcExpected" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="fcHigh" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="fcLow" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                      <XAxis dataKey="day" stroke="#64748b" fontSize={10} tickLine={false} />
                      <YAxis
                        stroke="#64748b"
                        fontSize={10}
                        tickLine={false}
                        tickFormatter={(v) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "0.75rem", fontSize: "12px" }}
                        formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, ""]}
                      />
                      <Legend wrapperStyle={{ fontSize: 10 }} />
                      <Area type="monotone" dataKey="low_spend" name="Optimised Plan" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#fcLow)" dot={false} />
                      <Area type="monotone" dataKey="expected" name="Expected" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#fcExpected)" dot={false} />
                      <Area type="monotone" dataKey="high_spend" name="High Spending" stroke="#f43f5e" strokeWidth={1.5} strokeDasharray="4 4" fillOpacity={1} fill="url(#fcHigh)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Assumptions & disclaimer ─────────────────────────────────────── */}
        {projections?.assumptions && (
          <div className="glass-panel p-5 rounded-3xl border border-white/5">
            <div className="flex items-start gap-3">
              <Info className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
              <div className="flex flex-col gap-2">
                <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Forecast Assumptions & Disclaimer</span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-1">
                  <div className="text-[10px] space-y-0.5">
                    <p className="text-slate-500 font-semibold uppercase tracking-wider">Method</p>
                    <p className="text-slate-300">{projections.assumptions.method === "linear_trend" ? "Linear regression on monthly totals" : "Average-based (limited history)"}</p>
                  </div>
                  <div className="text-[10px] space-y-0.5">
                    <p className="text-slate-500 font-semibold uppercase tracking-wider">Expense Data</p>
                    <p className="text-slate-300">{projections.assumptions.expense_data_months} calendar month(s)</p>
                  </div>
                  <div className="text-[10px] space-y-0.5">
                    <p className="text-slate-500 font-semibold uppercase tracking-wider">Inflation Growth</p>
                    <p className="text-slate-300">{projections.assumptions.inflation_rate_pct}% per month (6-month chart)</p>
                  </div>
                  <div className="text-[10px] space-y-0.5">
                    <p className="text-slate-500 font-semibold uppercase tracking-wider">Income Source</p>
                    <p className="text-slate-300">Profile monthly income</p>
                  </div>
                </div>
                <p className="text-[10px] text-slate-600 leading-relaxed mt-1">
                  {projections.assumptions.disclaimer}
                </p>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
};

export default ForecastPage;
