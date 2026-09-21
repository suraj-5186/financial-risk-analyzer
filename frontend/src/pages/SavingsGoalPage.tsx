import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { api } from "../services/api";
import {
  PiggyBank, Plus, Loader2, Calendar, Check,
  AlertCircle, Sparkles
} from "lucide-react";

export const SavingsGoalPage: React.FC = () => {
  const [goals, setGoals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [depositAmount, setDepositAmount] = useState<{ [key: number]: string }>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    title: "",
    target_amount: "",
    target_date: ""
  });

  const loadGoals = async () => {
    try {
      const data = await api.getGoals();
      setGoals(data || []);
    } catch (err) {
      console.error("Failed to load goals:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeposit = async (id: number) => {
    setError("");
    setSuccess("");
    const amount = Number(depositAmount[id] || 0);
    if (isNaN(amount) || amount <= 0) {
      alert("Please enter a valid deposit amount.");
      return;
    }
    const goal = goals.find(g => g.id === id);
    if (!goal) return;

    try {
      await api.updateGoal(id, {
        current_amount: goal.current_amount + amount
      });
      setDepositAmount(prev => ({ ...prev, [id]: "" }));
      loadGoals();
      setSuccess(`Successfully added ₹${amount.toLocaleString("en-IN")} deposit!`);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError("Deposit failed: " + err.message);
      setTimeout(() => setError(""), 3000);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!form.title || !form.target_amount || !form.target_date) return;
    setSubmitting(true);

    try {
      await api.createGoal({
        title: form.title,
        target_amount: Number(form.target_amount),
        target_date: form.target_date
      });
      setForm({ title: "", target_amount: "", target_date: "" });
      loadGoals();
      setSuccess("Savings target added successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to create savings goal.");
      setTimeout(() => setError(""), 3000);
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    loadGoals();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      
      <Header />

      <main className="max-w-6xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-8 relative z-10">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <PiggyBank className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-black text-white">Savings Goal Tracker</h1>
          </div>
          <p className="text-xs text-slate-400">
            Design savings milestones, fund targets dynamically, and monitor progress bars.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center gap-2 animate-pulse">
            <AlertCircle className="w-4.5 h-4.5" /> {error}
          </div>
        )}
        {success && (
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-2">
            <Check className="w-4.5 h-4.5" /> {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configure new goal card */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-fit flex flex-col gap-4">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <Plus className="w-4.5 h-4.5" /> Create Savings Target
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Goal Name</label>
                <input
                  type="text"
                  placeholder="e.g. Buy Laptop"
                  value={form.title}
                  onChange={(e) => setForm(prev => ({ ...prev, title: e.target.value }))}
                  className="bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Target Amount (₹)</label>
                <input
                  type="number"
                  placeholder="e.g. 80000"
                  value={form.target_amount}
                  onChange={(e) => setForm(prev => ({ ...prev, target_amount: e.target.value }))}
                  className="bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Target Date</label>
                <input
                  type="date"
                  value={form.target_date}
                  onChange={(e) => setForm(prev => ({ ...prev, target_date: e.target.value }))}
                  className="bg-slate-900 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                  required
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
                    <Plus className="w-4 h-4" /> Save Target
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Active target milestones grid */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white font-bold uppercase tracking-wider">Active Savings Milestones</span>
              <Sparkles className="w-4.5 h-4.5 text-emerald-400" />
            </div>

            {loading ? (
              <div className="py-12 flex items-center justify-center flex-col gap-2">
                <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                <span className="text-xs text-slate-400">Loading milestones...</span>
              </div>
            ) : goals.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">No active savings targets set. Create one using the menu on the left!</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {goals.map((g) => {
                  const percent = Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) || 0;
                  return (
                    <div
                      key={g.id}
                      className="p-5 rounded-2xl border border-white/5 bg-slate-900/40 hover:bg-slate-900/60 transition-all flex flex-col gap-4 justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex justify-between items-start">
                          <h4 className="text-xs font-bold text-white uppercase tracking-wider">{g.title}</h4>
                          <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10">
                            {percent}% funded
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1 font-semibold">
                          ₹{g.current_amount.toLocaleString("en-IN")} saved of ₹{g.target_amount.toLocaleString("en-IN")} target
                        </p>
                        <div className="text-[8px] text-slate-500 font-medium flex items-center gap-1 mt-1.5">
                          <Calendar className="w-3.5 h-3.5" /> Target: {new Date(g.target_date).toLocaleDateString("en-IN", { day: 'numeric', month: 'short', year: 'numeric' })}
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-300"
                          style={{ width: `${percent}%` }}
                        />
                      </div>

                      {/* Fund goal form */}
                      <div className="flex gap-2">
                        <input
                          type="number"
                          placeholder="₹ Amount"
                          value={depositAmount[g.id] || ""}
                          onChange={(e) => setDepositAmount(prev => ({ ...prev, [g.id]: e.target.value }))}
                          className="w-full bg-slate-950 border border-white/10 rounded-xl px-3 py-2 text-[11px] text-white focus:outline-none focus:border-emerald-500/50"
                        />
                        <button
                          onClick={() => handleDeposit(g.id)}
                          className="px-3 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold uppercase rounded-xl transition-all"
                        >
                          Deposit
                        </button>
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
export default SavingsGoalPage;
