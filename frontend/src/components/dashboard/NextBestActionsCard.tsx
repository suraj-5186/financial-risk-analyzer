import React, { useState } from "react";
import { Sparkles, CheckCircle2, Loader2, MessageSquare, Sliders, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../../services/api";

export interface NextBestAction {
  id: string;
  type: string;
  title: string;
  explanation: string;
  estimated_financial_impact: string;
  recommended_action: string;
  target_id?: number | string;
  suggested_amount?: number;
  badge?: string;
  is_applied?: boolean;
}

interface NextBestActionsCardProps {
  actions: NextBestAction[];
  onActionApplied?: () => void;
  onRefresh?: () => void;
}

export const NextBestActionsCard: React.FC<NextBestActionsCardProps> = ({
  actions = [],
  onActionApplied,
  onRefresh,
}) => {
  const navigate = useNavigate();
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [dismissingId, setDismissingId] = useState<string | null>(null);
  const [modifyingAction, setModifyingAction] = useState<NextBestAction | null>(null);
  const [modifiedAmount, setModifiedAmount] = useState<string>("");
  const [feedback, setFeedback] = useState<{ id: string; message: string; type: "success" | "error" } | null>(null);

  const handleApply = async (action: NextBestAction, customAmount?: number) => {
    setApplyingId(action.id);
    setFeedback(null);
    try {
      const payload = {
        ...action,
        suggested_amount: customAmount ?? action.suggested_amount,
      };
      const res = await api.applyRecommendation(action.id, payload);
      setFeedback({ id: action.id, message: res?.message || "Action applied successfully!", type: "success" });
      setModifyingAction(null);
      setTimeout(() => {
        if (onActionApplied) onActionApplied();
        else if (onRefresh) onRefresh();
      }, 1000);
    } catch (err: any) {
      setFeedback({ id: action.id, message: err?.message || "Failed to apply action.", type: "error" });
    } finally {
      setApplyingId(null);
    }
  };

  const handleDismiss = async (actionId: string) => {
    setDismissingId(actionId);
    setFeedback(null);
    try {
      await api.dismissRecommendation(actionId);
      setFeedback({ id: actionId, message: "Recommendation dismissed.", type: "success" });
      setTimeout(() => {
        if (onRefresh) onRefresh();
      }, 800);
    } catch (err: any) {
      setFeedback({ id: actionId, message: err?.message || "Failed to dismiss.", type: "error" });
    } finally {
      setDismissingId(null);
    }
  };

  const handleAskAI = (action: NextBestAction) => {
    const prompt = `Can you explain more about the recommendation "${action.title}" (${action.recommended_action})? Why is it advised for my financial risk profile?`;
    navigate("/chat", { state: { prefillMessage: prompt } });
  };

  if (!actions || actions.length === 0) {
    return (
      <div className="glass-panel p-6 rounded-3xl border border-white/5 text-center">
        <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-white mb-1">Risk Profile Optimized</h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          No critical risk interventions needed right now. All dynamic recommendations have either been addressed or your metrics are within safe boundaries.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-violet-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              Next Best Actions
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-semibold border border-violet-500/30">
                Rule Engine
              </span>
            </h2>
            <p className="text-xs text-slate-400">Prescriptive interventions to de-risk your financial profile</p>
          </div>
        </div>
      </div>

      {/* Grid of Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => {
          const isApplying = applyingId === action.id;
          const isDismissing = dismissingId === action.id;
          const isApplied = Boolean(action.is_applied);
          const cardFeedback = feedback?.id === action.id ? feedback : null;

          return (
            <div
              key={action.id}
              className={`p-4 rounded-2xl border transition-all flex flex-col justify-between ${
                isApplied
                  ? "bg-emerald-950/10 border-emerald-500/30"
                  : "bg-white/[0.02] border-white/10 hover:border-violet-500/40"
              }`}
            >
              <div>
                {/* Header Badge */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-md border ${
                        isApplied
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : action.badge === "High Priority"
                          ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                          : action.badge === "Smart Saving"
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                          : "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
                      }`}
                    >
                      {isApplied ? "Applied" : action.badge || "Recommended"}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                    {action.type.replace("_", " ")}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-white mb-1">{action.title}</h3>
                <p className="text-xs text-slate-300 mb-2.5 leading-relaxed">{action.explanation}</p>

                <div className="p-2.5 rounded-xl bg-black/40 border border-white/5 mb-3 text-xs">
                  <div className="text-[11px] text-slate-400 font-semibold uppercase">Financial Impact</div>
                  <div className="font-bold text-emerald-400">{action.estimated_financial_impact}</div>
                </div>

                {/* Feedback Alert */}
                {cardFeedback && (
                  <div
                    className={`mb-3 p-2 rounded-xl text-xs flex items-center gap-1.5 ${
                      cardFeedback.type === "success"
                        ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                        : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                    }`}
                  >
                    {cardFeedback.type === "success" ? (
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    )}
                    <span>{cardFeedback.message}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons: Apply, Modify, Dismiss, Ask AI */}
              <div className="space-y-2 pt-2 border-t border-white/5">
                {isApplied ? (
                  <div className="flex items-center gap-2">
                    <button
                      disabled
                      className="flex-1 py-2 text-xs font-bold rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 cursor-default flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Applied
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleApply(action)}
                      disabled={isApplying || isDismissing}
                      className="flex-1 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-violet-600 to-emerald-600 text-white hover:from-violet-500 hover:to-emerald-500 transition-all flex items-center justify-center gap-1.5 shadow-md shadow-violet-500/20 disabled:opacity-50"
                    >
                      {isApplying ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Applying...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Apply
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setModifyingAction(action);
                        setModifiedAmount(String(action.suggested_amount || ""));
                      }}
                      className="p-2 text-xs font-semibold rounded-xl bg-white/5 border border-white/10 hover:border-white/25 text-slate-300 hover:text-white transition-colors"
                      title="Customize parameters"
                    >
                      <Sliders className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                <div className="flex items-center justify-between text-xs pt-1">
                  <button
                    onClick={() => handleAskAI(action)}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium transition-colors"
                  >
                    <MessageSquare className="w-3 h-3" />
                    Ask AI Advisor
                  </button>

                  {!isApplied && (
                    <button
                      onClick={() => handleDismiss(action.id)}
                      disabled={isDismissing}
                      className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {isDismissing ? "Dismissing..." : "Dismiss"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modify Modal */}
      {modifyingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-panel p-6 rounded-3xl border border-violet-500/30 max-w-sm w-full shadow-2xl">
            <h3 className="text-base font-bold text-white mb-1">Customize Action</h3>
            <p className="text-xs text-slate-400 mb-4">{modifyingAction.title}</p>

            <div className="mb-4">
              <label className="block text-xs text-slate-400 mb-1">Adjust Amount (₹)</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-sm text-slate-500">₹</span>
                <input
                  type="number"
                  value={modifiedAmount}
                  onChange={(e) => setModifiedAmount(e.target.value)}
                  className="w-full pl-7 pr-3 py-1.5 text-sm rounded-xl bg-black/50 border border-white/10 text-white focus:outline-none focus:border-violet-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setModifyingAction(null)}
                className="flex-1 py-2 text-xs font-semibold rounded-xl border border-white/10 text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleApply(modifyingAction, Number(modifiedAmount))}
                className="flex-1 py-2 text-xs font-bold rounded-xl bg-violet-600 hover:bg-violet-500 text-white transition-colors"
              >
                Apply Custom
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
