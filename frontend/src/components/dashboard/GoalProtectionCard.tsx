import React from "react";
import { Target, Clock, Plus, ArrowUpRight, CheckCircle2 } from "lucide-react";

export interface GoalItem {
  id: number;
  title: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  formatted_target_date?: string;
  progress_pct: number;
  required_monthly_contribution: number;
  months_left?: number;
  days_left?: number;
  status: "ON_TRACK" | "NEEDS_ATTENTION" | "AT_RISK" | "DELAYED" | "COMPLETED";
  status_label: string;
  risk_badge: string;
  projected_shortfall?: number;
  delay_days?: number;
  explanation?: string;
}

interface GoalProtectionProps {
  goals: GoalItem[];
  currency?: string;
  onDeposit?: (goalId: number) => void;
  onCreateGoal?: () => void;
  onViewAllGoals?: () => void;
}

export const GoalProtectionCard: React.FC<GoalProtectionProps> = ({
  goals = [],
  currency = "INR",
  onDeposit,
  onCreateGoal,
  onViewAllGoals,
}) => {
  const symbol = currency === "USD" ? "$" : currency === "EUR" ? "€" : "₹";

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ON_TRACK":
        return {
          bg: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
          icon: <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />,
          label: "🟢 ON TRACK",
        };
      case "NEEDS_ATTENTION":
        return {
          bg: "bg-amber-500/15 text-amber-400 border-amber-500/30",
          icon: <span className="w-2 h-2 rounded-full bg-amber-400" />,
          label: "🟡 NEEDS ATTENTION",
        };
      case "AT_RISK":
        return {
          bg: "bg-rose-500/15 text-rose-400 border-rose-500/30",
          icon: <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />,
          label: "🔴 AT RISK",
        };
      case "DELAYED":
        return {
          bg: "bg-rose-500/20 text-rose-300 border-rose-500/40",
          icon: <span className="w-2 h-2 rounded-full bg-rose-500" />,
          label: "🔴 DELAYED",
        };
      case "COMPLETED":
        return {
          bg: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />,
          label: "✅ COMPLETED",
        };
      default:
        return {
          bg: "bg-slate-500/15 text-slate-400 border-slate-500/30",
          icon: <span className="w-2 h-2 rounded-full bg-slate-400" />,
          label: "TRACKING",
        };
    }
  };

  const onTrackCount = goals.filter((g) => g.status === "ON_TRACK" || g.status === "COMPLETED").length;
  const atRiskCount = goals.filter((g) => g.status === "NEEDS_ATTENTION" || g.status === "AT_RISK" || g.status === "DELAYED").length;

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden">
      {/* Glow */}
      <div className="absolute top-0 left-1/3 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
            <Target className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">Goal Protection Engine</h2>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active Defenses
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Predicts completion timelines and defends your savings against cash leakage.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {goals.length > 0 && (
            <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/5 mr-1">
              <span className="text-emerald-400">{onTrackCount} On Track</span>
              {atRiskCount > 0 && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="text-amber-400">{atRiskCount} Need Attention</span>
                </>
              )}
            </div>
          )}
          {onCreateGoal && (
            <button
              onClick={onCreateGoal}
              className="px-3.5 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              New Goal
            </button>
          )}
        </div>
      </div>

      {/* Goal Cards Grid */}
      {goals.length === 0 ? (
        <div className="text-center py-10 px-4 rounded-2xl border border-dashed border-white/10 bg-slate-900/40">
          <Target className="w-10 h-10 text-slate-600 mx-auto mb-2.5" />
          <h4 className="text-sm font-bold text-slate-300">No active goals yet</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Create goals like a new Laptop, Emergency Fund, or Travel to activate automatic protection algorithms.
          </p>
          {onCreateGoal && (
            <button
              onClick={onCreateGoal}
              className="px-4 py-2 bg-emerald-500 text-slate-950 text-xs font-bold rounded-xl hover:bg-emerald-400 transition-colors inline-flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> Create First Goal
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {goals.map((goal) => {
            const badge = getStatusBadge(goal.status);
            const isRisk = goal.status === "NEEDS_ATTENTION" || goal.status === "AT_RISK" || goal.status === "DELAYED";

            return (
              <div
                key={goal.id}
                className={`p-4 rounded-2xl border transition-all duration-200 flex flex-col justify-between ${
                  isRisk
                    ? "bg-slate-900/90 border-amber-500/30 hover:border-amber-500/50"
                    : "bg-slate-900/60 border-white/10 hover:border-white/20"
                }`}
              >
                <div>
                  {/* Card Header: Title & Status */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <h3 className="text-sm font-bold text-white leading-snug">{goal.title}</h3>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>Target: {goal.formatted_target_date || goal.target_date}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1.5 whitespace-nowrap ${badge.bg}`}>
                      {badge.icon}
                      {badge.label}
                    </span>
                  </div>

                  {/* Amounts & Progress */}
                  <div className="my-3">
                    <div className="flex justify-between items-baseline mb-1.5">
                      <span className="text-xs text-slate-400 font-medium">
                        {symbol}{goal.current_amount.toLocaleString("en-IN")}
                        <span className="text-slate-500"> / {symbol}{goal.target_amount.toLocaleString("en-IN")}</span>
                      </span>
                      <span className="text-xs font-extrabold text-white">{goal.progress_pct}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          goal.progress_pct >= 100
                            ? "bg-cyan-400"
                            : isRisk
                            ? "bg-gradient-to-r from-amber-500 to-rose-400"
                            : "bg-gradient-to-r from-emerald-500 to-cyan-400"
                        }`}
                        style={{ width: `${Math.min(100, goal.progress_pct)}%` }}
                      />
                    </div>
                  </div>

                  {/* Required contribution pill */}
                  <div className="flex items-center justify-between py-2 px-2.5 rounded-xl bg-slate-950/60 border border-white/5 text-[11px] mb-2.5">
                    <span className="text-slate-400 font-medium">Required Saving:</span>
                    <span className="font-bold text-slate-200">
                      {symbol}{goal.required_monthly_contribution.toLocaleString("en-IN")}/month
                    </span>
                  </div>

                  {/* Threat / Shortfall Alert if any */}
                  {goal.explanation && isRisk && (
                    <div className={`p-2 rounded-xl text-[11px] leading-relaxed mb-3 ${
                      goal.status === "AT_RISK" || goal.status === "DELAYED"
                        ? "bg-rose-500/10 border border-rose-500/20 text-rose-300"
                        : "bg-amber-500/10 border border-amber-500/20 text-amber-300"
                    }`}>
                      <div className="flex items-center gap-1.5 font-semibold mb-1">
                        <span>⚠️</span>
                        <span>{goal.status === "DELAYED" ? "Timeline Delayed" : "Shortfall Warning"}</span>
                        {goal.delay_days && goal.delay_days > 0 ? (
                          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300">
                            ~{goal.delay_days}d delay
                          </span>
                        ) : null}
                      </div>
                      <div>{goal.explanation}</div>
                    </div>
                  )}
                </div>

                {/* Card Action */}
                <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">
                    {goal.months_left ? `${goal.months_left} months left` : "Active"}
                  </span>
                  {onDeposit && (
                    <button
                      onClick={() => onDeposit(goal.id)}
                      className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-emerald-500/20 hover:text-emerald-300 text-slate-300 font-semibold text-xs transition-colors flex items-center gap-1 border border-white/5 hover:border-emerald-500/30"
                    >
                      <Plus className="w-3 h-3" />
                      Add Deposit
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer link to Goals page */}
      {onViewAllGoals && goals.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/5 flex justify-end">
          <button
            onClick={onViewAllGoals}
            className="text-xs text-slate-400 hover:text-cyan-400 font-medium flex items-center gap-1 group transition-colors"
          >
            Manage all financial goals & targets <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>
      )}
    </div>
  );
};
