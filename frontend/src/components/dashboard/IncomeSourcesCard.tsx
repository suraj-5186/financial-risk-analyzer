import React, { useState } from "react";
import { Wallet, Plus, Trash2, Zap, Loader2, AlertCircle } from "lucide-react";
import { api } from "../../services/api";

export interface IncomeSource {
  id: number;
  name: string;
  amount: number;
  income_type: string; // "recurring" | "one_time"
  frequency: string;
  is_recurring: boolean;
  is_active: boolean;
  next_expected_date?: string | null;
  allocated_to_goals?: number;
  free_cash?: number;
  unallocated_amount?: number;
}

interface IncomeSourcesCardProps {
  sources: IncomeSource[];
  totalMonthlyIncome: number;
  profileMonthlyIncome: number;
  oneTimeAvailableCash?: number;
  oneTimeAllocated?: number;
  oneTimeFreeCash?: number;
  onAllocate?: (source: IncomeSource) => void;
  onRefresh?: () => void;
}

const SOURCE_PRESETS = ["Salary", "Freelance", "Bonus", "Stipend", "Gift", "Investment", "Consulting", "Rental"];

export const IncomeSourcesCard: React.FC<IncomeSourcesCardProps> = ({
  sources = [],
  totalMonthlyIncome,
  profileMonthlyIncome,
  oneTimeAvailableCash = 0,
  oneTimeAllocated = 0,
  oneTimeFreeCash = 0,
  onAllocate,
  onRefresh,
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    amount: "",
    income_type: "recurring",
    frequency: "monthly",
    next_expected_date: "",
  });

  const recurringSources = sources.filter((s) => s.income_type === "recurring");
  const oneTimeSources = sources.filter((s) => s.income_type === "one_time");

  const displayMonthly = totalMonthlyIncome > 0 ? totalMonthlyIncome : profileMonthlyIncome;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    if (!form.name || !form.amount) return;

    setSubmitting(true);
    try {
      const payload: any = {
        name: form.name,
        amount: Number(form.amount),
        income_type: form.income_type,
        frequency: form.income_type === "one_time" ? "one_time" : form.frequency,
        is_recurring: form.income_type === "recurring",
        is_active: true,
      };
      if (form.next_expected_date) {
        payload.next_expected_date = form.next_expected_date;
      }
      const newSource = await api.createIncomeSource(payload);
      setForm({ name: "", amount: "", income_type: "recurring", frequency: "monthly", next_expected_date: "" });
      setShowAddForm(false);

      if (form.income_type === "one_time" && onAllocate) {
        onAllocate(newSource);
      } else if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to add income source");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (s: IncomeSource) => {
    setErrorMsg(null);
    const hasAllocations = (s.allocated_to_goals && s.allocated_to_goals > 0) || (s.free_cash && s.free_cash > 0);
    if (hasAllocations) {
      setErrorMsg(`Cannot delete '${s.name}' because it has active allocations. To preserve historical audit integrity, you can deactivate it instead.`);
      return;
    }

    setDeletingId(s.id);
    try {
      await api.deleteIncomeSource(s.id);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to delete income source");
    } finally {
      setDeletingId(null);
    }
  };

  const handleToggleActive = async (s: IncomeSource) => {
    try {
      await api.updateIncomeSource(s.id, { is_active: !s.is_active });
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to update income source status");
    }
  };

  return (
    <div className="glass-panel p-6 rounded-3xl border border-white/10 relative overflow-hidden">
      {/* Decorative Glow */}
      <div className="absolute top-0 right-1/4 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
            <Wallet className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">Income Command Center</h2>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active Sources
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Recurring cash flow drives daily safe spending; discrete windfalls route to goals.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 transition-all w-fit"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Income Stream
        </button>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center gap-2.5 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Recurring Cash Flow Card */}
        <div className="p-4 rounded-2xl bg-slate-900/50 border border-white/5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recurring Monthly Inflow</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              Monthly Baseline
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-white">₹{displayMonthly.toLocaleString("en-IN")}</span>
            <span className="text-xs text-slate-400">/month</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Calculated from {recurringSources.filter((s) => s.is_active).length} recurring stream(s)
          </p>
        </div>

        {/* One-Time Events Card */}
        <div className="p-4 rounded-2xl bg-slate-900/50 border border-white/5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">One-Time Capital Events</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 font-medium">
              Isolated Capital
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-violet-400">₹{oneTimeAvailableCash.toLocaleString("en-IN")}</span>
            <span className="text-xs text-slate-400">total windfalls</span>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
            <span>To Goals: <strong className="text-white">₹{oneTimeAllocated.toLocaleString("en-IN")}</strong></span>
            <span>•</span>
            <span>Free Cash: <strong className="text-emerald-400">₹{oneTimeFreeCash.toLocaleString("en-IN")}</strong></span>
          </div>
        </div>
      </div>

      {/* Add Income Form (Inline) */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 rounded-2xl bg-white/5 border border-white/10 animate-in fade-in duration-200">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">New Income Stream</h3>

          {/* Type Selector Tabs */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <button
              type="button"
              onClick={() => setForm({ ...form, income_type: "recurring", frequency: "monthly" })}
              className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                form.income_type === "recurring"
                  ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
                  : "bg-black/30 border-white/10 text-slate-400"
              }`}
            >
              🔄 Recurring Stream
            </button>
            <button
              type="button"
              onClick={() => setForm({ ...form, income_type: "one_time", frequency: "one_time" })}
              className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                form.income_type === "one_time"
                  ? "bg-violet-500/20 border-violet-500/50 text-violet-300"
                  : "bg-black/30 border-white/10 text-slate-400"
              }`}
            >
              ⚡ One-Time Windfall
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Source Name</label>
              <input
                type="text"
                placeholder="e.g. Primary Salary or Annual Bonus"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-xl bg-black/40 border border-white/10 text-white focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Amount (₹)</label>
              <input
                type="number"
                placeholder="35000"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-xl bg-black/40 border border-white/10 text-white focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
          </div>

          {form.income_type === "recurring" && (
            <div className="mb-3">
              <label className="block text-[11px] text-slate-400 mb-1">Frequency</label>
              <div className="flex gap-2">
                {["monthly", "weekly"].map((freq) => (
                  <button
                    key={freq}
                    type="button"
                    onClick={() => setForm({ ...form, frequency: freq })}
                    className={`px-3 py-1.5 text-xs rounded-xl border capitalize ${
                      form.frequency === freq
                        ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                        : "bg-black/30 border-white/10 text-slate-400"
                    }`}
                  >
                    {freq}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Preset Buttons */}
          <div className="flex items-center gap-1.5 flex-wrap mb-4">
            <span className="text-[10px] text-slate-500">Presets:</span>
            {SOURCE_PRESETS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => setForm({ ...form, name: preset })}
                className="px-2 py-0.5 text-[10px] rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-200 border border-white/5"
              >
                {preset}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 text-xs rounded-xl text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 text-xs font-bold rounded-xl bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              Save Source
            </button>
          </div>
        </form>
      )}

      {/* Streams Listing */}
      <div className="space-y-4">
        {/* Section 1: Recurring Streams */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-2">
            <span>Recurring Inflow Channels</span>
            <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-300">{recurringSources.length}</span>
          </h4>

          {recurringSources.length === 0 ? (
            <p className="text-xs text-slate-500 py-2">No recurring income streams configured. Using profile baseline.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {recurringSources.map((s) => (
                <div
                  key={s.id}
                  className={`p-3 rounded-2xl border transition-all flex items-center justify-between ${
                    s.is_active
                      ? "bg-slate-900/40 border-white/5 hover:border-white/15"
                      : "bg-slate-900/20 border-white/5 opacity-50"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-semibold text-white truncate">{s.name}</p>
                      <span className="px-1.5 py-0.5 text-[9px] rounded font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {s.frequency}
                      </span>
                    </div>
                    <p className="text-sm font-black text-slate-200 mt-0.5">
                      ₹{s.amount.toLocaleString("en-IN")}
                      <span className="text-[10px] font-normal text-slate-500 ml-1">
                        {s.frequency === "weekly" ? "(~₹" + Math.round(s.amount * 4.33).toLocaleString("en-IN") + "/mo)" : "/mo"}
                      </span>
                    </p>
                  </div>

                  <div className="flex items-center gap-1 ml-2">
                    <button
                      onClick={() => handleToggleActive(s)}
                      className={`text-[10px] px-2 py-1 rounded-lg border font-medium ${
                        s.is_active
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                      title={s.is_active ? "Deactivate stream" : "Activate stream"}
                    >
                      {s.is_active ? "Active" : "Paused"}
                    </button>
                    <button
                      onClick={() => handleDelete(s)}
                      disabled={deletingId === s.id}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Delete stream"
                    >
                      {deletingId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: One-Time Windfalls */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-2">
            <span>One-Time Windfall Events</span>
            <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-300">{oneTimeSources.length}</span>
          </h4>

          {oneTimeSources.length === 0 ? (
            <p className="text-xs text-slate-500 py-2">No one-time windfalls recorded.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {oneTimeSources.map((s) => {
                const isFullyAllocated = (s.unallocated_amount ?? 0) === 0 && ((s.allocated_to_goals ?? 0) + (s.free_cash ?? 0)) > 0;
                const unallocated = s.unallocated_amount ?? s.amount;

                return (
                  <div
                    key={s.id}
                    className="p-3 rounded-2xl bg-slate-900/40 border border-violet-500/20 hover:border-violet-500/40 transition-all flex flex-col justify-between"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-semibold text-white truncate">{s.name}</p>
                          <span className="px-1.5 py-0.5 text-[9px] rounded font-bold uppercase bg-violet-500/15 text-violet-300 border border-violet-500/30">
                            One-Time
                          </span>
                        </div>
                        <p className="text-sm font-black text-violet-400 mt-0.5">
                          ₹{s.amount.toLocaleString("en-IN")}
                        </p>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDelete(s)}
                          disabled={deletingId === s.id}
                          className={`p-1.5 rounded-lg transition-colors ${
                            isFullyAllocated
                              ? "text-slate-600 hover:text-slate-400"
                              : "text-slate-500 hover:text-rose-400 hover:bg-rose-500/10"
                          }`}
                          title={isFullyAllocated ? "Historical allocation record (protected)" : "Delete windfall"}
                        >
                          {deletingId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Breakdown & Allocation Action */}
                    <div className="pt-2 border-t border-white/5 flex items-center justify-between gap-2">
                      {isFullyAllocated ? (
                        <div className="flex items-center gap-2 text-[10px] text-slate-400">
                          <span className="text-emerald-400 font-semibold">✓ Committed</span>
                          <span>(Goals: ₹{(s.allocated_to_goals || 0).toLocaleString("en-IN")}, Free: ₹{(s.free_cash || 0).toLocaleString("en-IN")})</span>
                        </div>
                      ) : (
                        <>
                          <span className="text-[10px] text-amber-400 font-medium">
                            ₹{unallocated.toLocaleString("en-IN")} unallocated
                          </span>
                          {onAllocate && (
                            <button
                              onClick={() => onAllocate(s)}
                              className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-violet-500/20 text-violet-300 border border-violet-500/40 hover:bg-violet-500/30 transition-all flex items-center gap-1"
                            >
                              <Zap className="w-3 h-3 text-violet-400" />
                              Allocate Windfall
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
