import React from "react";
import { Activity, ShieldCheck, ArrowUpRight, TrendingUp, Info } from "lucide-react";

interface BreakdownItem {
  score: number;
  max: number;
  label: string;
  value: string;
  status: string;
}

interface FinancialHealthCardProps {
  score: number;
  grade: string;
  statusText?: string;
  breakdown?: {
    savings?: BreakdownItem;
    spending?: BreakdownItem;
    debt?: BreakdownItem;
    emergency_fund?: BreakdownItem;
    goal_progress?: BreakdownItem;
  };
  onManageProfile?: () => void;
}

export const FinancialHealthCard: React.FC<FinancialHealthCardProps> = ({
  score,
  grade,
  statusText,
  breakdown,
  onManageProfile,
}) => {
  const isScoreAvailable = score !== undefined && score !== null;
  const currentScore = isScoreAvailable ? Math.max(0, Math.min(100, score)) : 0;
  const currentGrade = grade || (isScoreAvailable ? (currentScore >= 80 ? "Good" : currentScore >= 60 ? "Moderate" : "At Risk") : "Pending");
  const currentStatusText = statusText || (isScoreAvailable ? (currentScore >= 80 ? "Optimal stability" : "Needs attention") : "Health diagnostic pending profile completion");

  // Score color styling
  const getScoreColor = (s: number) => {
    if (!isScoreAvailable) return { text: "text-slate-400", ring: "stroke-slate-700", badge: "bg-slate-800 text-slate-400 border-white/10" };
    if (s >= 85) return { text: "text-emerald-400", ring: "stroke-emerald-400", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
    if (s >= 70) return { text: "text-cyan-400", ring: "stroke-cyan-400", badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" };
    if (s >= 50) return { text: "text-amber-400", ring: "stroke-amber-400", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
    return { text: "text-rose-400", ring: "stroke-rose-400", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30" };
  };

  const style = getScoreColor(currentScore);
  const circumference = 2 * Math.PI * 42;
  const strokeDashoffset = isScoreAvailable
    ? circumference - (currentScore / 100) * circumference
    : circumference;

  const breakdownItems = [
    { label: "Savings Habit", item: breakdown?.savings, max: 35 },
    { label: "Spending Discipline", item: breakdown?.spending, max: 30 },
    { label: "Debt Safety", item: breakdown?.debt, max: 20 },
    { label: "Emergency Cushion", item: breakdown?.emergency_fund, max: 15 },
  ];

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden flex flex-col justify-between">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Financial Health</h3>
              <p className="text-xs text-slate-500">Live Diagnostic Index</p>
            </div>
          </div>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${style.badge}`}>
            {currentGrade}
          </span>
        </div>

        {/* Score & Gauge Section */}
        <div className="flex items-center justify-between gap-4 my-2">
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className={`text-4xl sm:text-5xl font-extrabold tracking-tight ${style.text}`}>
                {isScoreAvailable ? currentScore : "—"}
              </span>
              <span className="text-lg font-bold text-slate-500">/ 100</span>
            </div>
            <p className="text-sm font-medium text-slate-200 mt-1 flex items-center gap-1.5">
              <ShieldCheck className={`w-4 h-4 shrink-0 ${isScoreAvailable ? "text-emerald-400" : "text-slate-500"}`} />
              <span>{currentStatusText}</span>
            </p>
          </div>

          {/* Circular Progress Gauge */}
          <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="42"
                className="stroke-slate-800"
                strokeWidth="7"
                fill="transparent"
              />
              <circle
                cx="50"
                cy="50"
                r="42"
                className={`${style.ring} transition-all duration-1000 ease-out`}
                strokeWidth="7"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <TrendingUp className={`w-5 h-5 ${style.text}`} />
            </div>
          </div>
        </div>

        {/* Contributing Areas Breakdown */}
        <div className="mt-5 space-y-2.5 pt-4 border-t border-white/5">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Contributing Factor Breakdown
          </div>
          {breakdownItems.map((entry, idx) => {
            const item = entry.item;
            const hasData = item !== undefined && item !== null;
            const scoreVal = item ? item.score : 0;
            const displayVal = item ? item.value : "—";
            const pct = item && entry.max > 0 ? Math.min(100, Math.round((scoreVal / entry.max) * 100)) : 0;

            return (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-300 font-medium">{entry.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-[11px]">{displayVal}</span>
                    <span className={hasData ? "text-emerald-400 font-semibold" : "text-slate-500 font-semibold"}>
                      {hasData ? `${scoreVal}/${entry.max}` : `—/${entry.max}`}
                    </span>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      hasData ? "bg-gradient-to-r from-emerald-500 to-cyan-400" : "bg-slate-700 opacity-20"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      {onManageProfile && (
        <button
          onClick={onManageProfile}
          className="mt-4 pt-3 border-t border-white/5 text-xs text-slate-400 hover:text-emerald-400 flex items-center justify-between w-full transition-colors group"
        >
          <span className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            Adjust benchmark weights
          </span>
          <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-transform" />
        </button>
      )}
    </div>
  );
};
