import React from "react";
import { AlertOctagon, AlertTriangle, AlertCircle, ShieldAlert, CheckCircle, ArrowRight, Info } from "lucide-react";

export interface RiskItem {
  id: string;
  severity: "high" | "medium" | "low";
  category: string;
  title: string;
  explanation: string;
  financial_impact: string;
  recommended_action: string;
}

interface FinancialRisksProps {
  risks: RiskItem[];
  onTakeAction?: (risk: RiskItem) => void;
}

export const FinancialRisksCard: React.FC<FinancialRisksProps> = ({
  risks = [],
  onTakeAction,
}) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "high":
        return {
          cardBorder: "border-rose-500/30 hover:border-rose-500/50 bg-rose-950/10",
          badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
          icon: <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
          label: "HIGH SEVERITY",
        };
      case "medium":
        return {
          cardBorder: "border-amber-500/30 hover:border-amber-500/50 bg-amber-950/10",
          badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
          icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
          label: "MEDIUM",
        };
      default:
        return {
          cardBorder: "border-blue-500/30 hover:border-blue-500/50 bg-blue-950/10",
          badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
          icon: <AlertCircle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />,
          label: "ADVISORY",
        };
    }
  };

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden flex flex-col justify-between">
      {/* Background glow */}
      <div className="absolute top-0 right-1/4 w-48 h-48 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />

      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">Active Financial Risks</h3>
              <p className="text-xs text-slate-400">Automated Threat Detection & Anomaly Alerts</p>
            </div>
          </div>
          {risks.length > 0 ? (
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30">
              {risks.length} Threat{risks.length > 1 ? "s" : ""} Identified
            </span>
          ) : (
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" /> All Clear
            </span>
          )}
        </div>

        {/* Risks List */}
        {risks.length === 0 ? (
          <div className="text-center py-8 px-4 rounded-2xl bg-slate-900/40 border border-white/5">
            <CheckCircle className="w-9 h-9 text-emerald-400 mx-auto mb-2" />
            <h4 className="text-xs font-bold text-slate-200">No Critical Financial Threats Detected</h4>
            <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
              Your spending velocity, active goals, and debt ratios are currently operating within safe risk thresholds.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {risks.map((risk) => {
              const style = getSeverityBadge(risk.severity);
              return (
                <div
                  key={risk.id}
                  className={`p-4 rounded-2xl border transition-all duration-200 ${style.cardBorder}`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-start gap-2">
                      {style.icon}
                      <div>
                        <h4 className="text-xs font-bold text-white leading-tight">{risk.title}</h4>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">{risk.category}</span>
                      </div>
                    </div>
                    <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-md border ${style.badge}`}>
                      {style.label}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 mt-2 mb-2 leading-relaxed">
                    {risk.explanation}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-white/5 text-[11px]">
                    <div className="p-2 rounded-xl bg-slate-950/60 border border-white/5">
                      <span className="text-slate-500 uppercase font-bold text-[9px] block">Impact</span>
                      <span className="text-rose-300 font-semibold">{risk.financial_impact}</span>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-950/60 border border-white/5">
                      <span className="text-slate-500 uppercase font-bold text-[9px] block">Recommended Action</span>
                      <span className="text-emerald-300 font-medium">{risk.recommended_action}</span>
                    </div>
                  </div>

                  {/* Interactive Action Trigger */}
                  <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500 flex items-center gap-1">
                      <Info className="w-3 h-3 text-slate-500 shrink-0" />
                      Guided resolution
                    </span>
                    {onTakeAction ? (
                      <button
                        type="button"
                        onClick={() => onTakeAction(risk)}
                        aria-label={`Take Action on ${risk.title}`}
                        className="px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold flex items-center gap-1 transition-colors group cursor-pointer"
                      >
                        Take Action <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    ) : (
                      <span className="text-[10px] text-slate-500 italic">
                        {risk.recommended_action}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
