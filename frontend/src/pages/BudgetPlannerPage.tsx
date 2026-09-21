import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { api } from "../services/api";
import {
  Sliders, Plus, Loader2, Sparkles,
  AlertCircle, Check
} from "lucide-react";

export const BudgetPlannerPage: React.FC = () => {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const currentMonthStr = new Date().toISOString().slice(0, 7);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthStr);

  const [form, setForm] = useState({
    category: "",
    monthly_limit: ""
  });

  const categories = [
    "Food", "Shopping", "Rent", "Bills", "Travel",
    "Healthcare", "Entertainment", "Education", "Other"
  ];

  const loadBudgets = async (monthToLoad?: string) => {
    try {
      const data = await api.getBudgets(monthToLoad || selectedMonth);
      setBudgets(data || []);
    } catch (err) {
      console.error("Failed to load budgets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateLimit = async (id: number, currentLimit: number) => {
    const newLimitStr = prompt("Enter new monthly limit (₹):", currentLimit.toString());
    if (newLimitStr === null) return;
    const newLimit = Number(newLimitStr);
    if (isNaN(newLimit) || newLimit <= 0) {
      alert("Please enter a valid positive number.");
      return;
    }
    try {
      await api.updateBudget(id, { monthly_limit: newLimit });
      loadBudgets();
      setSuccess("Budget limit updated successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError("Failed to update: " + err.message);
      setTimeout(() => setError(""), 3000);
    }
  };

  const handleDeleteBudget = async (id: number, category: string) => {
    if (!confirm(`Are you sure you want to remove the budget limit for '${category}'?\n\nNote: Any past transactions under this category will remain completely intact in your records.`)) {
      return;
    }
    try {
      const res = await api.deleteBudget(id);
      loadBudgets();
      setSuccess(res?.message || `Budget category '${category}' deleted.`);
      setTimeout(() => setSuccess(""), 4000);
    } catch (err: any) {
      setError("Failed to delete budget: " + err.message);
      setTimeout(() => setError(""), 4000);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!form.category || form.monthly_limit === "") return;
    const limitNum = Number(form.monthly_limit);
    if (isNaN(limitNum) || limitNum < 0) {
      setError("Please enter a valid monthly limit (₹0 or more).");
      return;
    }
    setSubmitting(true);

    try {
      await api.createBudget({
        category: form.category,
        monthly_limit: limitNum
      });
      setForm({ category: "", monthly_limit: "" });
      loadBudgets();
      setSuccess("Budget category configured successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to create budget limit.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    loadBudgets(selectedMonth);
  }, [selectedMonth]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      
      <Header />

      <main className="max-w-6xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-8 relative z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-emerald-400" />
              <h1 className="text-2xl font-black text-white">Monthly Budget Planner</h1>
            </div>
            <p className="text-xs text-slate-400">
              Set and monitor maximum monthly spending boundaries strictly scoped to the selected calendar month.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Period:</span>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500/50"
            />
            {selectedMonth === currentMonthStr && (
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
                Current Month
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center gap-2 animate-pulse">
            <AlertCircle className="w-4.5 h-4.5 shrink-0" /> {error}
          </div>
        )}
        {success && (
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-2">
            <Check className="w-4.5 h-4.5 shrink-0" /> {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form to configure new budget */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-fit flex flex-col gap-4">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <Plus className="w-4.5 h-4.5" /> Create Category Cap
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Expense Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm(prev => ({ ...prev, category: e.target.value }))}
                  className="bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                  required
                >
                  <option value="">Select Category</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Monthly Limit (₹)</label>
                <input
                  type="number"
                  placeholder="e.g. 15000"
                  value={form.monthly_limit}
                  onChange={(e) => setForm(prev => ({ ...prev, monthly_limit: e.target.value }))}
                  className="bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                  required
                  min="0"
                  step="any"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-2 py-3 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 hover:border-emerald-500/40 text-emerald-400 text-xs font-semibold rounded-2xl transition-all flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Plus className="w-4 h-4" /> Save Budget Cap
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Active budget list progress indicators */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white font-bold uppercase tracking-wider">Active Category Thresholds</span>
              <Sparkles className="w-4.5 h-4.5 text-emerald-400" />
            </div>

            {loading ? (
              <div className="py-12 flex items-center justify-center flex-col gap-2">
                <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                <span className="text-xs text-slate-400">Loading limits...</span>
              </div>
            ) : budgets.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">No active category limits configured. Build one using the panel on the left!</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {budgets.map((b) => {
                  const limit = Number(b.monthly_limit) || 0;
                  const spent = Number(b.spent) || 0;
                  const remaining = b.remaining !== undefined ? b.remaining : Math.max(0, limit - spent);
                  const percentage = b.utilization_pct !== undefined 
                    ? b.utilization_pct 
                    : (limit > 0 ? Math.round((spent / limit) * 100) : (spent > 0 ? 100 : 0));
                  const isOver = spent > limit;
                  const isClose = !isOver && limit > 0 && percentage >= 80;

                  return (
                    <div
                      key={b.id}
                      className={`p-4 rounded-2xl border bg-slate-900/40 hover:bg-slate-900/60 transition-all flex flex-col gap-3 justify-between ${
                        isOver ? "border-red-500/30 bg-red-950/10" : isClose ? "border-amber-500/30" : "border-white/5"
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-bold text-white uppercase tracking-wider">{b.category}</h4>
                            {isOver && (
                              <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 uppercase">
                                Over Cap
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-400 mt-1 block">
                            ₹{spent.toLocaleString("en-IN")} spent of ₹{limit.toLocaleString("en-IN")} limit
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleUpdateLimit(b.id, b.monthly_limit)}
                            className="text-[9px] text-emerald-400 hover:text-emerald-300 font-bold uppercase tracking-wider px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 transition-all"
                            title="Edit monthly budget cap"
                          >
                            Modify
                          </button>
                          <button
                            onClick={() => handleDeleteBudget(b.id, b.category)}
                            className="text-[9px] text-red-400 hover:text-red-300 font-bold uppercase tracking-wider px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-all"
                            title="Delete category budget (transactions preserved)"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[9px] text-slate-400 font-medium">
                          <span>Remaining: <strong className={isOver ? "text-red-400" : "text-slate-200"}>₹{remaining.toLocaleString("en-IN")}</strong></span>
                          <span className={isOver ? "text-red-400 font-black" : isClose ? "text-amber-400 font-bold" : "text-slate-400"}>
                            {percentage}% utilized
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${isOver ? "bg-red-500" : isClose ? "bg-amber-400" : "bg-emerald-500"}`}
                            style={{ width: `${Math.min(100, percentage)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
export default BudgetPlannerPage;
