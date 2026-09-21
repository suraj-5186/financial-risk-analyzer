import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  RefreshCw,
  Clock,
  ArrowLeft,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  insightsApi,
} from "../services/insights";
import type {
  CashFlowSummary,
  CashFlowForecast,
  FinancialHealthData,
} from "../services/insights";

export const InsightsPage: React.FC = () => {
  const [timeframe, setTimeframe] = useState<string>("30d");
  const [cashFlow, setCashFlow] = useState<CashFlowSummary | null>(null);
  const [forecast, setForecast] = useState<CashFlowForecast | null>(null);
  const [healthData, setHealthData] = useState<FinancialHealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [showMethodology, setShowMethodology] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadAllInsights = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [cf, fc, hd] = await Promise.all([
        insightsApi.getCashFlow(timeframe),
        insightsApi.getForecast(),
        insightsApi.getFinancialHealth(timeframe),
      ]);
      setCashFlow(cf);
      setForecast(fc);
      setHealthData(hd);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load financial insights");
    } finally {
      setLoading(false);
    }
  }, [timeframe]);

  useEffect(() => {
    loadAllInsights();
  }, [loadAllInsights]);

  const formatCurrency = (val: number) => {
    return `₹${Math.abs(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getDeltaBadge = (pct: number | null | undefined, isExpense: boolean = false) => {
    if (pct === null || pct === undefined) {
      return <span className="text-[11px] text-slate-500 font-medium">New baseline</span>;
    }
    const isPositive = pct > 0;
    // For expenses, an increase is cautionary (amber/red), decrease is favorable (green)
    const isFavorable = isExpense ? !isPositive : isPositive;

    return (
      <span
        className={`inline-flex items-center gap-0.5 text-xs font-semibold px-2 py-0.5 rounded-full ${
          isFavorable
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
        }`}
      >
        {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
        {Math.abs(pct)}% vs prior period
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
              </Link>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Sparkles className="w-8 h-8 text-indigo-400" />
              Cash Flow Forecasting &amp; Financial Insights
            </h1>
            <p className="text-sm text-slate-400">
              Explainable cash flow analysis, forward balance projections, and rule-based observations backed by verified data.
            </p>
          </div>

          {/* Timeframe Selector Pills */}
          <div className="flex items-center gap-1.5 bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 self-start md:self-auto shadow-inner">
            {[
              { id: "30d", label: "30 Days" },
              { id: "month", label: "This Month" },
              { id: "90d", label: "90 Days" },
              { id: "year", label: "Past Year" },
            ].map((tf) => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  timeframe === tf.id
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-rose-950/50 border border-rose-500/30 rounded-2xl p-4 flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-16 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
            <p className="text-sm text-slate-400">Analyzing cash flow and computing projections...</p>
          </div>
        ) : (
          <>
            {/* Cash Flow Summary Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Total Inflow */}
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-medium text-slate-400">
                  <span>Total Inflow (Income)</span>
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {cashFlow ? formatCurrency(cashFlow.total_income) : "₹0.00"}
                </div>
                <div className="pt-1">
                  {getDeltaBadge(cashFlow?.comparison.income_change_pct, false)}
                </div>
              </div>

              {/* Total Outflow */}
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-medium text-slate-400">
                  <span>Total Outflow (Expenses)</span>
                  <TrendingDown className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {cashFlow ? formatCurrency(cashFlow.total_expenses) : "₹0.00"}
                </div>
                <div className="pt-1">
                  {getDeltaBadge(cashFlow?.comparison.expense_change_pct, true)}
                </div>
              </div>

              {/* Net Cash Flow */}
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-medium text-slate-400">
                  <span>Net Cash Flow</span>
                  <Activity className="w-4 h-4 text-indigo-400" />
                </div>
                <div
                  className={`text-2xl font-bold ${
                    (cashFlow?.net_cash_flow || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {(cashFlow?.net_cash_flow || 0) >= 0 ? "+" : "-"}
                  {cashFlow ? formatCurrency(cashFlow.net_cash_flow) : "₹0.00"}
                </div>
                <div className="text-xs text-slate-500 pt-1">
                  {(cashFlow?.net_cash_flow || 0) >= 0 ? "Cash surplus" : "Cash deficit"}
                </div>
              </div>

              {/* Savings Rate */}
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm space-y-2">
                <div className="flex items-center justify-between text-xs font-medium text-slate-400">
                  <span>Savings Rate</span>
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {cashFlow?.savings_rate !== null && cashFlow?.savings_rate !== undefined
                    ? `${cashFlow.savings_rate}%`
                    : "—"}
                </div>
                <div className="text-xs text-slate-500 pt-1">Of total period income</div>
              </div>
            </div>

            {/* Cash Flow Forecast Card */}
            {forecast && (
              <div className="bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-indigo-950/20 border border-indigo-500/20 rounded-3xl p-6 backdrop-blur-md space-y-6 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <Clock className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-white">
                          Month-End Cash Flow Projection ({forecast.month_end_forecast.month_label})
                        </h2>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase">
                          ESTIMATE
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {forecast.month_end_forecast.days_remaining} days remaining •{" "}
                        <span className="text-indigo-300 font-medium">{forecast.confidence_label}</span>
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => setShowMethodology(!showMethodology)}
                    className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 bg-slate-800/80 hover:bg-slate-800 px-3 py-1.5 rounded-xl border border-slate-700/60 transition-colors self-start sm:self-auto"
                  >
                    <Info className="w-3.5 h-3.5" />
                    <span>Calculation Details</span>
                    {showMethodology ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>

                {/* Forecast Metric Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-slate-800/80">
                  <div className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-4 space-y-1">
                    <span className="text-xs text-slate-400">Projected Month-End Expenses</span>
                    <div className="text-xl font-bold text-white">
                      {formatCurrency(forecast.month_end_forecast.projected_total_expenses)}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      ₹{forecast.month_end_forecast.actual_expense_to_date.toLocaleString()} spent + ₹
                      {forecast.month_end_forecast.projected_additional_discretionary.toLocaleString()} variable + ₹
                      {forecast.month_end_forecast.projected_additional_recurring.toLocaleString()} recurring bills
                    </div>
                  </div>

                  <div className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-4 space-y-1">
                    <span className="text-xs text-slate-400">Projected Month-End Income</span>
                    <div className="text-xl font-bold text-white">
                      {formatCurrency(forecast.month_end_forecast.projected_total_income)}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Based on actual receipts &amp; expected monthly baseline
                    </div>
                  </div>

                  <div className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-4 space-y-1">
                    <span className="text-xs text-slate-400">Projected Net Cash Flow</span>
                    <div
                      className={`text-xl font-bold ${
                        forecast.month_end_forecast.projected_net_cash_flow >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {forecast.month_end_forecast.projected_net_cash_flow >= 0 ? "+" : "-"}
                      {formatCurrency(forecast.month_end_forecast.projected_net_cash_flow)}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {forecast.month_end_forecast.projected_net_cash_flow >= 0
                        ? "Expected month-end surplus"
                        : "Expected month-end deficit"}
                    </div>
                  </div>
                </div>

                {/* Upcoming scheduled bills due before month end */}
                {forecast.month_end_forecast.upcoming_recurring_commitments.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-800/60">
                    <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                      <span>
                        Scheduled Recurring Bills Due Before Month-End (
                        {forecast.month_end_forecast.upcoming_recurring_commitments.length})
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
                      {forecast.month_end_forecast.upcoming_recurring_commitments.map((item, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3 flex items-center justify-between"
                        >
                          <div>
                            <div className="text-xs font-medium text-white truncate max-w-[130px]">
                              {item.merchant_name}
                            </div>
                            <div className="text-[10px] text-slate-400">Due {item.due_date}</div>
                          </div>
                          <div className="text-xs font-semibold text-rose-300">
                            ₹{item.amount.toLocaleString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Expandable Methodology Drawer */}
                {showMethodology && (
                  <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-xs text-slate-300 space-y-3">
                    <div className="font-semibold text-indigo-300">Forecasting Methodology &amp; Assumptions:</div>
                    <ul className="space-y-1.5 text-slate-400 list-disc list-inside">
                      {forecast.methodology.explanations.map((exp, idx) => (
                        <li key={idx}>{exp}</li>
                      ))}
                    </ul>
                    <div className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-900">
                      {forecast.methodology.disclaimer}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Trends and Category Distribution Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Monthly Trend Chart (2 cols) */}
              <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <h3 className="font-bold text-white text-base">Monthly Cash Flow Trends</h3>
                    <p className="text-xs text-slate-400">Income vs. Expense trajectory over the last 6 months</p>
                  </div>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <span className="w-3 h-3 rounded bg-emerald-500"></span> Inflow
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <span className="w-3 h-3 rounded bg-rose-500"></span> Outflow
                    </span>
                  </div>
                </div>

                <div className="h-64 w-full pt-4">
                  {cashFlow && cashFlow.trends.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={cashFlow.trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="month_label" stroke="#64748b" fontSize={11} tickLine={false} />
                        <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `₹${v / 1000}k`} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            borderColor: "#334155",
                            borderRadius: "0.75rem",
                            fontSize: "12px",
                          }}
                          formatter={(value: any) => [`₹${Number(value).toLocaleString()}`, ""]}
                        />
                        <Bar dataKey="income" name="Income" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={32} />
                        <Bar dataKey="expenses" name="Expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={32} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-slate-500">
                      No historical trend data available yet.
                    </div>
                  )}
                </div>
              </div>

              {/* Category Spending Breakdown (1 col) */}
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-sm space-y-4">
                <div className="space-y-0.5">
                  <h3 className="font-bold text-white text-base">Outflow by Category</h3>
                  <p className="text-xs text-slate-400">Expense concentration for selected timeframe</p>
                </div>

                <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                  {cashFlow && cashFlow.categories.length > 0 ? (
                    cashFlow.categories.map((cat, idx) => (
                      <div key={idx} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-slate-200">{cat.category}</span>
                          <span className="font-semibold text-white">
                            ₹{cat.amount.toLocaleString()} ({cat.percentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, cat.percentage)}%` }}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500 italic py-8 text-center">
                      No category expenses recorded in this period.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Financial Health Insights Section */}
            <div className="space-y-4 pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-indigo-400" />
                    Financial Health Insights &amp; Observations
                  </h3>
                  <p className="text-xs text-slate-400">
                    Rule-based observations derived from verified transaction and budget trends.
                  </p>
                </div>
                {healthData && (
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                      healthData.health_tone === "risk"
                        ? "bg-rose-500/10 border-rose-500/30 text-rose-400"
                        : healthData.health_tone === "warning"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    }`}
                  >
                    {healthData.overall_health}
                  </span>
                )}
              </div>

              {healthData && healthData.insights.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {healthData.insights.map((insight) => {
                    const isRisk = insight.type === "risk";
                    const isWarn = insight.type === "warning";
                    const isAchieve = insight.type === "achievement";

                    return (
                      <div
                        key={insight.id}
                        className={`rounded-2xl p-5 border backdrop-blur-sm space-y-3.5 transition-all ${
                          isRisk
                            ? "bg-rose-950/20 border-rose-500/30"
                            : isWarn
                            ? "bg-amber-950/20 border-amber-500/30"
                            : isAchieve
                            ? "bg-emerald-950/20 border-emerald-500/30"
                            : "bg-slate-900/50 border-slate-800"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2.5">
                            {isRisk && <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />}
                            {isWarn && <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />}
                            {isAchieve && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
                            {!isRisk && !isWarn && !isAchieve && <Info className="w-5 h-5 text-blue-400 shrink-0" />}
                            <h4 className="font-semibold text-white text-sm">{insight.title}</h4>
                          </div>

                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-700/60 text-slate-300 shrink-0">
                            {insight.metric_impact}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">{insight.description}</p>

                        <div className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-[11px] space-y-1">
                          <span className="font-medium text-slate-400">Trigger Calculation:</span>
                          <p className="text-slate-300 leading-normal">{insight.explanation}</p>
                          <div className="text-[10px] text-slate-500 pt-0.5">Period: {insight.period}</div>
                        </div>

                        <div className="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-2.5 flex items-start gap-2">
                          <Sparkles className="w-4 h-4 shrink-0 mt-0.5 text-indigo-400" />
                          <span>{insight.recommended_action}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="bg-slate-900/30 border border-dashed border-slate-800 rounded-2xl p-8 text-center text-xs text-slate-400 space-y-1">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                  <div className="font-medium text-white">Stable Financial Flow</div>
                  <p className="text-slate-500">
                    No anomalous spending spikes, budget overruns, or recurring commitment imbalances detected for this period.
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
