import React, { useState } from "react";
import { X, CheckCircle2, Zap, Loader2, ArrowRight, AlertCircle, Sparkles } from "lucide-react";
import { api } from "../../services/api";

interface Goal {
  id: number;
  title: string;
  target_amount: number;
  current_amount: number;
}

interface GoalAllocationModalProps {
  incomeSourceId: number;
  incomeAmount: number;
  incomeName: string;
  goals: Goal[];
  onClose: () => void;
  onAllocated?: () => void;
}

export const GoalAllocationModal: React.FC<GoalAllocationModalProps> = ({
  incomeSourceId,
  incomeAmount,
  incomeName,
  goals,
  onClose,
  onAllocated,
}) => {
  const [allocations, setAllocations] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const totalAllocatedToGoals = Object.values(allocations).reduce(
    (sum, v) => sum + (Number(v) || 0),
    0
  );
  const freeCash = Math.max(0, Number((incomeAmount - totalAllocatedToGoals).toFixed(2)));

  const handleGoalAmountChange = (goalId: number, val: string) => {
    setError(null);
    const numVal = Math.max(0, Number(val) || 0);
    const otherAllocations = Object.entries(allocations)
      .filter(([id]) => Number(id) !== goalId)
      .reduce((sum, [, v]) => sum + (Number(v) || 0), 0);

    if (numVal + otherAllocations > incomeAmount) {
      // Cap to remaining available
      const maxAllowed = Math.max(0, incomeAmount - otherAllocations);
      setAllocations((prev) => ({ ...prev, [goalId]: String(maxAllowed) }));
    } else {
      setAllocations((prev) => ({ ...prev, [goalId]: val }));
    }
  };

  const handleQuickDistribute = (strategy: "even" | "focus_first" | "all_free") => {
    setError(null);
    if (strategy === "all_free") {
      setAllocations({});
      return;
    }

    const activeGoals = goals.filter((g) => g.current_amount < g.target_amount);
    if (activeGoals.length === 0) return;

    if (strategy === "even") {
      const share = Math.floor((incomeAmount / activeGoals.length) / 100) * 100;
      const newMap: Record<number, string> = {};
      activeGoals.forEach((g) => {
        const remainingGoal = Math.max(0, g.target_amount - g.current_amount);
        newMap[g.id] = String(Math.min(share, remainingGoal));
      });
      setAllocations(newMap);
    } else if (strategy === "focus_first") {
      const first = activeGoals[0];
      const remainingGoal = Math.max(0, first.target_amount - first.current_amount);
      const alloc = Math.min(incomeAmount, remainingGoal);
      setAllocations({ [first.id]: String(alloc) });
    }
  };

  const handleSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const goalList = Object.entries(allocations)
        .filter(([, v]) => Number(v) > 0)
        .map(([id, v]) => ({
          goal_id: Number(id),
          amount: Number(Number(v).toFixed(2)),
          notes: `Allocated from ${incomeName}`,
        }));

      // Single atomic backend call
      await api.allocateIncomeSource(incomeSourceId, {
        allocations: goalList,
        free_cash_amount: freeCash,
      });

      setDone(true);
      setTimeout(() => {
        onClose();
        if (onAllocated) onAllocated();
      }, 1400);
    } catch (err: any) {
      setError(err?.message || "Failed to commit allocation. Please check amounts.");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-200">
        <div className="glass-panel rounded-3xl border border-emerald-500/40 p-8 max-w-sm w-full text-center shadow-2xl">
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto mb-4 animate-bounce">
            <CheckCircle2 className="w-10 h-10 text-emerald-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Atomic Allocation Committed</h3>
          <p className="text-sm text-slate-300">
            ₹{totalAllocatedToGoals.toLocaleString("en-IN")} routed to goals and ₹{freeCash.toLocaleString("en-IN")} preserved as free cash reserve.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="glass-panel rounded-3xl border border-violet-500/30 p-6 max-w-lg w-full max-h-[92vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center">
              <Zap className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Allocate Extra Cash</h2>
              <p className="text-xs text-slate-400">Atomic allocation for {incomeName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl border border-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center gap-2.5 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Summary Card */}
        <div className="mb-5 p-4 rounded-2xl bg-gradient-to-br from-violet-500/10 via-slate-900/60 to-emerald-500/10 border border-violet-500/25">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Total Windfall</p>
              <p className="text-2xl font-black text-violet-400">₹{incomeAmount.toLocaleString("en-IN")}</p>
              <p className="text-xs text-slate-400">{incomeName}</p>
            </div>
            <ArrowRight className="w-5 h-5 text-violet-400/40" />
            <div className="text-right">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Free Cash Reserve</p>
              <p className={`text-2xl font-black ${freeCash > 0 ? "text-emerald-400" : "text-slate-400"}`}>
                ₹{freeCash.toLocaleString("en-IN")}
              </p>
              <p className="text-[11px] text-slate-500">Uncommitted surplus</p>
            </div>
          </div>

          {/* Allocation Gauge */}
          <div className="mt-3.5">
            <div className="flex justify-between text-[11px] text-slate-400 mb-1.5">
              <span>Allocated to Goals: ₹{totalAllocatedToGoals.toLocaleString("en-IN")}</span>
              <span>Free Cash: {Math.round((freeCash / incomeAmount) * 100)}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-800/90 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-violet-500 transition-all duration-300"
                style={{ width: `${Math.min(100, (totalAllocatedToGoals / incomeAmount) * 100)}%` }}
              />
              <div
                className="h-full bg-emerald-500/60 transition-all duration-300"
                style={{ width: `${Math.max(0, (freeCash / incomeAmount) * 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Quick Strategies */}
        <div className="mb-5 flex items-center gap-2">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-violet-400" /> Presets:
          </span>
          <button
            type="button"
            onClick={() => handleQuickDistribute("focus_first")}
            className="px-2.5 py-1 text-xs rounded-lg bg-white/5 border border-white/10 hover:border-violet-500/40 text-slate-300 hover:text-white transition-colors"
          >
            Top Priority First
          </button>
          <button
            type="button"
            onClick={() => handleQuickDistribute("even")}
            className="px-2.5 py-1 text-xs rounded-lg bg-white/5 border border-white/10 hover:border-violet-500/40 text-slate-300 hover:text-white transition-colors"
          >
            Split Evenly
          </button>
          <button
            type="button"
            onClick={() => handleQuickDistribute("all_free")}
            className="px-2.5 py-1 text-xs rounded-lg bg-white/5 border border-white/10 hover:border-emerald-500/40 text-slate-300 hover:text-white transition-colors"
          >
            Keep All Free Cash
          </button>
        </div>

        {/* Goals Distribution List */}
        <div className="space-y-3 mb-6">
          <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">Select Goal Allocations</p>
          {goals.length === 0 ? (
            <p className="text-sm text-slate-500 py-3 text-center">No active goals found. Entire windfall will remain as Free Cash Reserve.</p>
          ) : (
            goals.map((g) => {
              const remaining = Math.max(0, g.target_amount - g.current_amount);
              const isCompleted = remaining <= 0;
              const currentVal = allocations[g.id] || "";

              return (
                <div
                  key={g.id}
                  className={`p-3.5 rounded-2xl border transition-all ${
                    Number(currentVal) > 0
                      ? "bg-violet-500/10 border-violet-500/40"
                      : "bg-slate-900/50 border-white/5 hover:border-white/15"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-semibold text-white">{g.title}</h4>
                      <p className="text-xs text-slate-400">
                        ₹{g.current_amount.toLocaleString("en-IN")} / ₹{g.target_amount.toLocaleString("en-IN")}{" "}
                        <span className="text-slate-500">(₹{remaining.toLocaleString("en-IN")} needed)</span>
                      </p>
                    </div>
                    {isCompleted && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        Completed
                      </span>
                    )}
                  </div>

                  {!isCompleted && (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="relative flex-1">
                        <span className="absolute left-3 top-2 text-sm text-slate-500">₹</span>
                        <input
                          type="number"
                          min="0"
                          max={incomeAmount}
                          value={currentVal}
                          placeholder="0"
                          onChange={(e) => handleGoalAmountChange(g.id, e.target.value)}
                          className="w-full pl-7 pr-3 py-1.5 text-sm rounded-xl bg-black/40 border border-white/10 text-white focus:outline-none focus:border-violet-500 transition-colors"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          const otherAllocations = Object.entries(allocations)
                            .filter(([id]) => Number(id) !== g.id)
                            .reduce((sum, [, v]) => sum + (Number(v) || 0), 0);
                          const maxPossible = Math.min(remaining, incomeAmount - otherAllocations);
                          setAllocations((prev) => ({ ...prev, [g.id]: String(maxPossible) }));
                        }}
                        className="px-2.5 py-1.5 text-xs rounded-xl bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25 transition-colors font-medium whitespace-nowrap"
                      >
                        Max (₹{Math.min(remaining, incomeAmount).toLocaleString("en-IN")})
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="flex-1 py-2.5 text-sm font-semibold rounded-xl border border-white/10 text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 py-2.5 text-sm font-bold rounded-xl bg-gradient-to-r from-violet-600 to-emerald-600 text-white hover:from-violet-500 hover:to-emerald-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20 disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Committing...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Commit Allocation
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
