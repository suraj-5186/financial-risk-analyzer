import React, { useState } from "react";
import { Wallet, ArrowRight, CheckCircle, Info } from "lucide-react";

interface SafeToSpendProps {
  safeToSpendToday?: number;
  monthlySafeSpending?: number;
  spentSoFar?: number;
  remainingSafeSpending?: number;
  daysRemainingInMonth?: number;
  fixedObligations?: number;
  goalCommitments?: number;
  mandatoryGoalCommitments?: number;
  plannedGoalCommitments?: number;
  emergencyAllocation?: number;
  supplementalFreeCash?: number;
  explanation?: string;
  currency?: string;
  onOpenTransactions?: () => void;
}

export const SafeToSpendCard: React.FC<SafeToSpendProps> = ({
  safeToSpendToday,
  monthlySafeSpending,
  spentSoFar = 0,
  remainingSafeSpending,
  daysRemainingInMonth,
  fixedObligations = 0,
  goalCommitments: _goalCommitments,
  mandatoryGoalCommitments = 0,
  plannedGoalCommitments: _plannedGoalCommitments,
  emergencyAllocation = 0,
  supplementalFreeCash = 0,
  explanation,
  currency = "INR",
  onOpenTransactions,
}) => {
  const [showExplanation, setShowExplanation] = useState(false);
  const symbol = currency === "USD" ? "$" : currency === "EUR" ? "€" : "₹";

  const isDataAvailable = safeToSpendToday !== undefined && monthlySafeSpending !== undefined && remainingSafeSpending !== undefined;

  const validMonthlySafeSpending = monthlySafeSpending ?? 0;
  const validRemainingSafeSpending = remainingSafeSpending ?? 0;

  const spendingRatio = validMonthlySafeSpending > 0
    ? Math.min(100, Math.round(((spentSoFar || 0) / validMonthlySafeSpending) * 100))
    : 0;

  const isNearingLimit = isDataAvailable && spendingRatio >= 80;
  const isOverLimit = isDataAvailable && validRemainingSafeSpending <= 0;

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden flex flex-col justify-between">
      {/* Background radial glow */}
      <div className={`absolute top-0 right-0 w-48 h-48 rounded-full blur-3xl pointer-events-none ${
        isOverLimit ? "bg-rose-500/10" : isNearingLimit ? "bg-amber-500/10" : "bg-emerald-500/15"
      }`} />

      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
              isOverLimit
                ? "bg-rose-500/15 border-rose-500/30 text-rose-400"
                : isNearingLimit
                ? "bg-amber-500/15 border-amber-500/30 text-amber-400"
                : "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
            }`}>
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Live Pacing Guide</h3>
              <p className="text-xs text-slate-500">Discretionary Spending Capacity</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {supplementalFreeCash > 0 && (
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded-full" title="Unallocated one-time windfall cash reserve">
                +₹{supplementalFreeCash.toLocaleString("en-IN")} Free Cash
              </span>
            )}
            <span className="text-[11px] font-semibold text-slate-400 bg-white/5 border border-white/5 px-2.5 py-1 rounded-full">
              {daysRemainingInMonth} days left
            </span>
          </div>
        </div>

        {/* Hero Value: Safe to spend today */}
        <div className="mt-2 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Safe to Spend Today
            </span>
            {explanation && (
              <button
                type="button"
                onClick={() => setShowExplanation(!showExplanation)}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
              >
                <Info className="w-3 h-3" />
                {showExplanation ? "Hide breakdown" : "Why this number?"}
              </button>
            )}
          </div>

          <div className="flex items-baseline gap-2 mt-1">
            <span className={`text-4xl sm:text-5xl font-extrabold tracking-tight ${
              !isDataAvailable
                ? "text-slate-500"
                : isOverLimit
                ? "text-rose-400"
                : isNearingLimit
                ? "text-amber-400"
                : "text-white"
            }`}>
              {isDataAvailable ? `${symbol}${safeToSpendToday.toLocaleString("en-IN")}` : "—"}
            </span>
            {isDataAvailable && <span className="text-xs text-slate-400 font-medium">/ day</span>}
          </div>

          {showExplanation && explanation ? (
            <div className="mt-2 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-xs text-cyan-200 animate-in fade-in duration-200">
              {explanation}
            </div>
          ) : (
            <p className="text-xs text-slate-400 mt-1">
              {!isDataAvailable
                ? "Discretionary spending limit is currently unavailable or calculating."
                : isOverLimit
                ? "Discretionary allowance exhausted. Pause non-essential spending to protect your goals."
                : isNearingLimit
                ? "Approaching limit. Keep daily spending under this target to avoid goal shortfall."
                : "Spending capacity after deducting essential bills, urgent goal commitments, and emergency reserves."}
            </p>
          )}
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5 my-4">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Monthly Discretionary Usage</span>
            <span className={`font-semibold ${!isDataAvailable ? "text-slate-500" : isOverLimit ? "text-rose-400" : isNearingLimit ? "text-amber-400" : "text-emerald-400"}`}>
              {isDataAvailable ? `${spendingRatio}% used` : "—"}
            </span>
          </div>
          <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-white/5">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                !isDataAvailable
                  ? "bg-slate-700 opacity-30"
                  : isOverLimit
                  ? "bg-rose-500"
                  : isNearingLimit
                  ? "bg-gradient-to-r from-amber-500 to-rose-400"
                  : "bg-gradient-to-r from-emerald-500 to-cyan-400"
              }`}
              style={{ width: `${isDataAvailable ? Math.min(100, spendingRatio) : 0}%` }}
            />
          </div>
        </div>

        {/* Breakdown 3-Column Metrics */}
        <div className="grid grid-cols-3 gap-2 p-3.5 rounded-2xl bg-slate-900/80 border border-white/5 text-center">
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500">Monthly Safe</div>
            <div className="text-sm sm:text-base font-bold text-slate-200 mt-0.5">
              {monthlySafeSpending !== undefined ? `${symbol}${monthlySafeSpending.toLocaleString("en-IN")}` : "—"}
            </div>
          </div>
          <div className="border-x border-white/5 px-1">
            <div className="text-[10px] uppercase font-bold text-slate-500">Spent So Far</div>
            <div className="text-sm sm:text-base font-bold text-amber-400 mt-0.5">
              {spentSoFar !== undefined ? `${symbol}${spentSoFar.toLocaleString("en-IN")}` : "—"}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500">Remaining</div>
            <div className={`text-sm sm:text-base font-bold mt-0.5 ${!isDataAvailable ? "text-slate-500" : isOverLimit ? "text-rose-400" : "text-emerald-400"}`}>
              {remainingSafeSpending !== undefined ? `${symbol}${remainingSafeSpending.toLocaleString("en-IN")}` : "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Footer / Calculation Transparency */}
      <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1 text-[11px] truncate">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          Protected: {symbol}{(mandatoryGoalCommitments + emergencyAllocation).toLocaleString("en-IN")} reserve & urgent goals + {symbol}{fixedObligations.toLocaleString("en-IN")} bills
        </span>
        {onOpenTransactions && (
          <button
            type="button"
            onClick={onOpenTransactions}
            aria-label="View Transactions Breakdown"
            className="text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1 text-[11px] group transition-colors shrink-0 ml-2"
          >
            View Transactions Breakdown <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>
    </div>
  );
};
