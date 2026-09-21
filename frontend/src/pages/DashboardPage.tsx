import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, API_BASE_URL, getAvatarUrl } from "../services/api";
import { transactionsApi } from "../services/transactions";
import {
  Activity, LogOut, AlertTriangle, AlertCircle,
  Plus, Check, Sparkles, Loader2, Sliders, ArrowUpRight, ArrowDownRight,
  PiggyBank, CreditCard, Bell, Trash2, User as UserIcon, Download
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, LineChart, Line, CartesianGrid, Legend
} from "recharts";

import { FinancialHealthCard } from "../components/dashboard/FinancialHealthCard";
import { SafeToSpendCard } from "../components/dashboard/SafeToSpendCard";
import { IncomeSourcesCard } from "../components/dashboard/IncomeSourcesCard";
import type { IncomeSource } from "../components/dashboard/IncomeSourcesCard";
import { GoalProtectionCard } from "../components/dashboard/GoalProtectionCard";
import { FinancialRisksCard } from "../components/dashboard/FinancialRisksCard";
import { FutureBalanceCard } from "../components/dashboard/FutureBalanceCard";
import { NextBestActionsCard } from "../components/dashboard/NextBestActionsCard";
import { GoalAllocationModal } from "../components/dashboard/GoalAllocationModal";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e"];

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [allocatingSource, setAllocatingSource] = useState<IncomeSource | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingProfile, setUpdatingProfile] = useState(false);
  const [submittingBudget, setSubmittingBudget] = useState(false);
  const [submittingGoal, setSubmittingGoal] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Notification Toast
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const showNotification = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Form states
  const [profileForm, setProfileForm] = useState({
    monthly_income: 50000,
    savings_rate: 20,
    debt_ratio: 30,
    spending_consistency: 70,
    emergency_fund_months: 3,
  });

  const [budgetForm, setBudgetForm] = useState({
    category: "",
    monthly_limit: "",
  });

  const [goalForm, setGoalForm] = useState({
    title: "",
    target_amount: "",
    target_date: "",
  });

  const [depositAmount, setDepositAmount] = useState<{ [key: number]: string }>({});

  const loadDashboardData = async () => {
    setError(null);
    try {
      const summary = await api.getSummary();
      const transList = await transactionsApi.list();
      setData(summary);
      setTransactions(transList);
      if (summary?.profile) {
        setProfileForm({
          monthly_income: summary.profile.monthly_income ?? 50000,
          savings_rate: summary.profile.savings_rate ?? 20,
          debt_ratio: summary.profile.debt_ratio ?? 30,
          spending_consistency: summary.profile.spending_consistency ?? 70,
          emergency_fund_months: summary.profile.emergency_fund_months ?? 3,
        });
      }
    } catch (err: any) {
      console.error("Error loading dashboard data:", err);
      const msg = err?.response?.data?.detail || err?.message || "Failed to load financial dashboard data";
      setError(msg);
      showNotification("Could not retrieve real-time financial data: " + msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/download-pdf`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        }
      });
      if (!response.ok) throw new Error("Failed to download PDF report");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `financial_report_${user?.full_name.toLowerCase().replace(" ", "_") || "user"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Failed to download report:", err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleClearNotifications = async () => {
    try {
      await api.clearNotifications();
      loadDashboardData();
    } catch (err) {
      console.error("Failed to clear notifications:", err);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      loadDashboardData();
    } catch (err) {
      console.error("Failed to read notification:", err);
    }
  };

  useEffect(() => {
    loadDashboardData();

    const handleWindowFocus = () => {
      loadDashboardData();
    };

    window.addEventListener("focus", handleWindowFocus);
    document.addEventListener("visibilitychange", handleWindowFocus);
    return () => {
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("visibilitychange", handleWindowFocus);
    };
  }, []);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdatingProfile(true);
    try {
      await api.updateProfile({
        monthly_income: Number(profileForm.monthly_income),
        savings_rate: Number(profileForm.savings_rate),
        debt_ratio: Number(profileForm.debt_ratio),
        spending_consistency: Number(profileForm.spending_consistency),
        emergency_fund_months: Number(profileForm.emergency_fund_months),
      });
      await loadDashboardData();
      showNotification("Financial parameters synchronized! Health Score recalculated.");
    } catch (err: any) {
      showNotification("Failed to update profile: " + err.message, "error");
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleBudgetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!budgetForm.category || !budgetForm.monthly_limit) return;
    setSubmittingBudget(true);
    try {
      await api.createBudget({
        category: budgetForm.category,
        monthly_limit: Number(budgetForm.monthly_limit),
      });
      setBudgetForm({ category: "", monthly_limit: "" });
      await loadDashboardData();
      showNotification("Budget category successfully added.");
    } catch (err: any) {
      showNotification("Failed to create budget: " + err.message, "error");
    } finally {
      setSubmittingBudget(false);
    }
  };

  const handleGoalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalForm.title || !goalForm.target_amount || !goalForm.target_date) return;
    setSubmittingGoal(true);
    try {
      await api.createGoal({
        title: goalForm.title,
        target_amount: Number(goalForm.target_amount),
        target_date: goalForm.target_date,
      });
      setGoalForm({ title: "", target_amount: "", target_date: "" });
      await loadDashboardData();
      showNotification("Savings target successfully added.");
    } catch (err: any) {
      showNotification("Failed to create goal: " + err.message, "error");
    } finally {
      setSubmittingGoal(false);
    }
  };

  const handleDeposit = async (goalId: number) => {
    const amount = Number(depositAmount[goalId] || 0);
    if (isNaN(amount) || amount <= 0) return;
    
    const goal = data.goals.find((g: any) => g.id === goalId);
    if (!goal) return;

    try {
      await api.updateGoal(goalId, {
        current_amount: goal.current_amount + amount,
      });
      setDepositAmount(prev => ({ ...prev, [goalId]: "" }));
      await loadDashboardData();
      showNotification("Deposit successfully recorded!");
    } catch (err: any) {
      showNotification("Deposit failed: " + err.message, "error");
    }
  };

  const handleTakeAction = (risk: any) => {
    if (!risk) return;
    const category = (risk.category || "").toLowerCase();
    const id = (risk.id || "").toLowerCase();

    // 1. Goal-related risks: Scroll to savings goals section or navigate to goals page
    if (category.includes("goal") || id.includes("goal")) {
      const el = document.getElementById("savings-goals-section");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      } else {
        navigate("/goals");
      }
      showNotification(`Focusing on savings goals for: ${risk.title}`, "success");
      return;
    }

    // 2. Budget-related risks: Scroll to budgets section or navigate to budget page
    if (category.includes("budget") || category.includes("overspending") || id.includes("budget")) {
      const el = document.getElementById("budgets-section");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      } else {
        navigate("/budget");
      }
      showNotification(`Focusing on budget allocations for: ${risk.title}`, "success");
      return;
    }

    // 3. Emergency reserve / liquidity risks: Focus recommended actions
    if (category.includes("liquidity") || id.includes("emergency")) {
      const el = document.getElementById("next-best-actions-section");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
        showNotification("Review the guided emergency reserve recommendation below.", "success");
      } else {
        navigate("/goals");
      }
      return;
    }

    // 4. Unusual transactions or spending anomaly risks: Navigate to transactions page
    if (category.includes("anomaly") || category.includes("spending") || id.includes("anomaly")) {
      navigate("/transactions");
      return;
    }

    // 5. Fallback for any other risk: Show informative guidance
    showNotification(
      risk.recommended_action || `Guidance: Review ${risk.title} in your financial overview.`,
      "success"
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-slate-800 border-t-emerald-500 rounded-full animate-spin"></div>
          <div className="text-emerald-400 font-semibold tracking-wider text-sm">Aggregating Financial Metrics...</div>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
        <div className="max-w-md w-full glass-panel border border-red-500/30 p-8 rounded-3xl text-center space-y-4">
          <div className="w-12 h-12 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center justify-center text-red-400 mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Financial Service Unavailable</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {error || "Unable to fetch verified financial metrics from the server. To protect financial integrity, simulated figures are not displayed."}
          </p>
          <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => {
                setLoading(true);
                loadDashboardData();
              }}
              className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-xs transition-all flex items-center justify-center gap-2"
            >
              <Activity className="w-4 h-4" /> Retry Connection
            </button>
            <button
              onClick={logout}
              className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 font-semibold rounded-xl text-xs transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 1. Pie Chart Data (Expense by Category)
  const expenseByCategoryData = data?.budgets?.map((b: any) => ({
    name: b.category,
    value: b.spent,
  })).filter((item: any) => item.value > 0) || [];

  // 2. Line Chart Data (Income vs Expense Over Time)
  const monthlyDataMap: { [key: string]: { month: string; Income: number; Expense: number } } = {};
  transactions.forEach((t: any) => {
    const dateObj = new Date(t.transaction_date);
    const monthKey = dateObj.toLocaleString("default", { month: "short", year: "2-digit" });
    if (!monthlyDataMap[monthKey]) {
      monthlyDataMap[monthKey] = { month: monthKey, Income: 0, Expense: 0 };
    }
    if (t.type === "Income") {
      monthlyDataMap[monthKey].Income += t.amount;
    } else {
      monthlyDataMap[monthKey].Expense += t.amount;
    }
  });

  const sortedMonths = Object.keys(monthlyDataMap).reverse();
  const timeChartData = sortedMonths.map(key => monthlyDataMap[key]);

  const currencySymbol = user?.currency === "USD" ? "$" : user?.currency === "EUR" ? "€" : user?.currency === "GBP" ? "£" : "₹";

  // Helper for metrics: distinguish genuine 0 from missing/undefined
  const formatCurrencyMetric = (val: number | undefined | null, prefix = currencySymbol) => {
    if (val === undefined || val === null || isNaN(Number(val))) {
      return "—";
    }
    return `${prefix}${Number(val).toLocaleString("en-IN")}`;
  };

  const formatCountMetric = (val: number | undefined | null) => {
    if (val === undefined || val === null || isNaN(Number(val))) {
      return "—";
    }
    return Number(val).toString();
  };

  // 3. Forecast Data
  const hasForecastExpense = data?.forecasted_expense !== undefined && data?.forecasted_expense !== null && !isNaN(Number(data?.forecasted_expense));
  const hasMonthlyExpense = data?.monthly_expense !== undefined && data?.monthly_expense !== null && !isNaN(Number(data?.monthly_expense));
  const forecastBarData = [
    { name: "Current Month", Spent: hasMonthlyExpense ? Number(data.monthly_expense) : 0 },
    { name: "Projected Next Month", Spent: hasForecastExpense ? Number(data.forecasted_expense) : 0 }
  ];

  const healthScore = data?.profile?.health_score || 0;
  const strokeDashoffset = 440 - (440 * healthScore) / 100;

  // Active budget limit: accurately represent configured budget categories
  // Distinguish configured budgets (including genuine ₹0 limit) from unavailable budget data.
  // Never silently fall back to legacy profile monthly_budget.
  const hasBudgetsConfigured = Array.isArray(data?.budgets) && data.budgets.length > 0;
  const totalBudgetLimit: number | null = hasBudgetsConfigured
    ? data.budgets.reduce((sum: number, b: any) => sum + (Number(b.monthly_limit) || 0), 0)
    : null;

  // Active primary savings goal: select an active, incomplete goal (status != COMPLETED and current < target)
  // Check goal_protection engine first for canonical status, or fallback to goals list
  const activeIncompleteGoal = (() => {
    if (Array.isArray(data?.goal_protection) && data.goal_protection.length > 0) {
      const active = data.goal_protection.find((g: any) => g.status !== "COMPLETED" && (Number(g.current_amount) || 0) < Number(g.target_amount));
      if (active) return active;
    }
    if (Array.isArray(data?.goals) && data.goals.length > 0) {
      const active = data.goals.find((g: any) => (Number(g.current_amount) || 0) < Number(g.target_amount));
      if (active) return active;
    }
    return null;
  })();

  const primaryGoal = activeIncompleteGoal;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      {/* Toast Banner */}
      {notification && (
        <div className={`fixed top-24 right-6 z-50 px-5 py-3.5 rounded-2xl glass-panel border shadow-2xl flex items-center gap-3 transition-all duration-300 transform translate-y-0 animate-bounce ${
          notification.type === "error" ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
        }`}>
          <Activity className="w-5 h-5 shrink-0" />
          <span className="text-xs font-semibold">{notification.message}</span>
        </div>
      )}

      {/* Glow overlays */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-600/5 blur-[120px] pointer-events-none" />

      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/5 py-4 px-6 md:px-12 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center glow-emerald">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-emerald-400 bg-clip-text text-transparent mr-6">
            FinRisk AI
          </span>
          <div className="hidden md:flex items-center gap-4 text-xs font-semibold text-slate-400">
            <Link to="/dashboard" className="text-white hover:text-emerald-400 transition-colors">Dashboard</Link>
            <Link to="/transactions" className="hover:text-emerald-400 transition-colors">Transactions</Link>
            <Link to="/subscriptions" className="hover:text-emerald-400 transition-colors">Subscriptions</Link>
            <Link to="/bank-sync" className="hover:text-emerald-400 transition-colors">Bank Sync</Link>
            <Link to="/insights" className="hover:text-emerald-400 transition-colors">Insights</Link>
            <Link to="/settings" className="hover:text-emerald-400 transition-colors">Settings</Link>
            {user?.is_admin && (
              <Link to="/admin" className="hover:text-red-400 transition-colors text-red-400 font-bold">Admin</Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 relative">
          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-emerald-400 hover:bg-white/5 transition-all relative"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {data?.notifications && data.notifications.filter((n: any) => !n.is_read).length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[8px] font-bold text-white flex items-center justify-center">
                  {data.notifications.filter((n: any) => !n.is_read).length}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            {showNotifications && (
              <div className="absolute right-0 mt-3 w-85 glass-panel border border-white/10 rounded-2xl shadow-2xl p-4 z-50 text-left max-h-96 overflow-y-auto">
                <div className="flex justify-between items-center pb-2 border-b border-white/5 mb-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300">System Notifications</span>
                  {data?.notifications && data.notifications.length > 0 && (
                    <button
                      onClick={handleClearNotifications}
                      className="text-[9px] font-bold uppercase tracking-wider text-red-400 hover:text-red-300 flex items-center gap-1"
                    >
                      <Trash2 className="w-3 h-3" /> Clear All
                    </button>
                  )}
                </div>
                <div className="space-y-2">
                  {!data?.notifications || data.notifications.length === 0 ? (
                    <p className="text-[10px] text-slate-500 text-center py-4">No active notifications</p>
                  ) : (
                    data.notifications.map((n: any) => (
                      <div
                        key={n.id}
                        onClick={() => !n.is_read && handleMarkRead(n.id)}
                        className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                          n.is_read 
                            ? "bg-slate-900/30 border-white/5 opacity-60" 
                            : "bg-emerald-500/5 border-emerald-500/10 hover:border-emerald-500/20"
                        }`}
                      >
                        <div className="flex justify-between items-start gap-2">
                          <span className="text-[10px] font-bold text-white leading-tight">{n.title}</span>
                          {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 mt-1" />}
                        </div>
                        <p className="text-[9px] text-slate-400 mt-1 leading-normal">{n.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User Photo */}
          {user?.profile_photo_url ? (
            <img
              src={getAvatarUrl(user.profile_photo_url)}
              alt="Profile"
              className="w-9 h-9 rounded-full object-cover border border-emerald-500/30"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-white/5 flex items-center justify-center">
              <UserIcon className="w-4 h-4 text-slate-400" />
            </div>
          )}

          <div className="hidden lg:flex flex-col text-right">
            <span className="text-sm font-semibold text-white">{user?.full_name}</span>
            <span className="text-xs text-slate-400">{user?.email}</span>
          </div>

          <button
            onClick={logout}
            className="p-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-red-400 hover:bg-white/5 transition-all flex items-center gap-2"
            title="Log Out"
          >
            <LogOut className="w-5 h-5" />
            <span className="hidden sm:inline text-xs font-semibold">Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-8 relative z-10">
        
        {/* ROW -1: Anomalies Alert Section */}
        {data?.anomalies && data.anomalies.length > 0 && (
          <div className="glass-panel border-red-500/30 bg-red-500/10 p-5 rounded-3xl flex flex-col gap-2.5 animate-pulse">
            <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
              <AlertTriangle className="w-4.5 h-4.5 shrink-0" /> Anomaly Warnings Detected
            </div>
            <div className="space-y-1.5 pl-1">
              {data.anomalies.map((alert: string, idx: number) => (
                <div key={idx} className="text-xs text-red-300 leading-relaxed font-medium">
                  • {alert}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* COMMAND CENTER: PRIMARY EXECUTIVE VIEWPORT                                */}
        {/* ========================================================================= */}

        {/* 1. HERO ROW: TRACK & UNDERSTAND */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <FinancialHealthCard
            score={data?.profile?.health_score}
            grade={data?.health_score_grade}
            statusText={data?.status_text}
            breakdown={data?.health_breakdown}
          />
          <SafeToSpendCard
            safeToSpendToday={data?.safe_to_spend?.safe_to_spend_today}
            monthlySafeSpending={data?.safe_to_spend?.monthly_safe_spending}
            spentSoFar={data?.safe_to_spend?.spent_so_far}
            remainingSafeSpending={data?.safe_to_spend?.remaining_safe_spending}
            daysRemainingInMonth={data?.safe_to_spend?.days_remaining_in_month}
            fixedObligations={data?.safe_to_spend?.fixed_obligations}
            goalCommitments={data?.safe_to_spend?.goal_commitments}
            mandatoryGoalCommitments={data?.safe_to_spend?.mandatory_goal_commitments}
            plannedGoalCommitments={data?.safe_to_spend?.planned_goal_commitments}
            emergencyAllocation={data?.safe_to_spend?.emergency_allocation}
            supplementalFreeCash={data?.safe_to_spend?.supplemental_free_cash}
            explanation={data?.safe_to_spend?.explanation}
            currency={user?.currency}
            onOpenTransactions={() => navigate("/transactions")}
          />
        </section>

        {/* 2. INCOME COMMAND ROW: TRACK */}
        <section>
          <IncomeSourcesCard
            sources={data?.income_sources || []}
            totalMonthlyIncome={data?.total_monthly_income || 0}
            profileMonthlyIncome={data?.profile?.monthly_income || 50000}
            oneTimeAvailableCash={data?.one_time_available_cash || 0}
            oneTimeAllocated={data?.one_time_allocated_to_goals || 0}
            oneTimeFreeCash={data?.one_time_free_cash || 0}
            onAllocate={(source) => setAllocatingSource(source)}
            onRefresh={loadDashboardData}
          />
        </section>

        {/* 3. PROTECTION ROW: PROTECT */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GoalProtectionCard
            goals={data?.goal_protection || []}
            currency={user?.currency}
            onViewAllGoals={() => navigate("/goals")}
            onCreateGoal={() => {
              const el = document.getElementById("savings-goals-section");
              if (el) el.scrollIntoView({ behavior: "smooth" });
              else navigate("/goals");
            }}
            onDeposit={(_goalId) => {
              const el = document.getElementById("savings-goals-section");
              if (el) el.scrollIntoView({ behavior: "smooth" });
              else navigate("/goals");
            }}
          />
          <FinancialRisksCard
            risks={data?.structured_risks || []}
            onTakeAction={handleTakeAction}
          />
        </section>

        {/* 4. PREDICTION ROW: PREDICT */}
        <section>
          <FutureBalanceCard
            projectedMonthEndBalance={data?.forecast_scenarios?.projected_month_end_balance}
            scenarios={data?.forecast_scenarios?.scenarios}
            chartData={data?.forecast_scenarios?.chart_data}
            dailyBurnRate={data?.forecast_scenarios?.daily_burn_rate}
            currency={user?.currency}
            onViewForecastPage={() => navigate("/forecast")}
          />
        </section>

        {/* 5. ACTION ROW: ACHIEVE */}
        <section id="next-best-actions-section">
          <NextBestActionsCard
            actions={data?.next_best_actions || []}
            onActionApplied={() => {
              showNotification("Action applied successfully!", "success");
              loadDashboardData();
            }}
            onRefresh={loadDashboardData}
          />
        </section>

        {/* Divider: Detailed Operations */}
        <div className="flex items-center gap-4 pt-4">
          <div className="h-px bg-white/10 flex-1" />
          <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
            Operations & Financial Records
          </span>
          <div className="h-px bg-white/10 flex-1" />
        </div>

        {/* ROW 0: Transaction Summary Cards */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Total Income</span>
              <h3 className="text-2xl font-black text-emerald-400">
                {formatCurrencyMetric(data?.total_income, currencySymbol)}
              </h3>
              <p className="text-[10px] text-slate-500">All-time earnings database</p>
            </div>
            <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl flex items-center justify-center">
              <ArrowUpRight className="w-6 h-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Total Expense</span>
              <h3 className="text-2xl font-black text-red-400">
                {formatCurrencyMetric(data?.total_expense, currencySymbol)}
              </h3>
              <p className="text-[10px] text-slate-500">All-time spending records</p>
            </div>
            <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl flex items-center justify-center">
              <ArrowDownRight className="w-6 h-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Net Savings</span>
              <h3 className={`text-2xl font-black ${(Number(data?.savings) || 0) >= 0 ? "text-blue-400" : "text-amber-500"}`}>
                {formatCurrencyMetric(data?.savings, currencySymbol)}
              </h3>
              <p className="text-[10px] text-slate-500">Income minus total expenses</p>
            </div>
            <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-2xl flex items-center justify-center">
              <PiggyBank className="w-6 h-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Transactions</span>
              <h3 className="text-2xl font-black text-white">
                {formatCountMetric(data?.transaction_count)}
              </h3>
              <p className="text-[10px] text-slate-500">Total registered records</p>
            </div>
            <div className="w-12 h-12 bg-slate-800 border border-white/5 text-slate-300 rounded-2xl flex items-center justify-center">
              <CreditCard className="w-6 h-6" />
            </div>
          </div>
        </section>

        {/* ROW 0.5: Budget Planner & Goal Tracking */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Budget Planner */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col justify-between">
            {totalBudgetLimit !== null ? (
              <>
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Monthly Budget</span>
                    {totalBudgetLimit > 0 && (Number(data?.monthly_expense) || 0) > totalBudgetLimit && (
                      <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-red-500/10 border border-red-500/20 text-red-400 animate-pulse">
                        Overspending Alert
                      </span>
                    )}
                  </div>
                  <div className="flex justify-between items-end mb-2">
                    <div>
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Spent</p>
                      <p className="text-xl font-black text-white">
                        {formatCurrencyMetric(data?.monthly_expense, currencySymbol)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Limit</p>
                      <p className="text-xs font-bold text-slate-400">
                        {formatCurrencyMetric(totalBudgetLimit, currencySymbol)}
                      </p>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden mb-2">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        (Number(totalBudgetLimit) > 0 && ((Number(data?.monthly_expense) || 0) / Number(totalBudgetLimit)) > 1) || (Number(totalBudgetLimit) === 0 && (Number(data?.monthly_expense) || 0) > 0) ? "bg-red-500" : "bg-emerald-500"
                      }`}
                      style={{ width: `${Number(totalBudgetLimit) > 0 ? Math.min(100, ((Number(data?.monthly_expense) || 0) / Number(totalBudgetLimit)) * 100) : (Number(data?.monthly_expense) > 0 ? 100 : 0)}%` }}
                    />
                  </div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-semibold">
                  <span>Used: {Number(totalBudgetLimit) > 0 ? Math.round(((Number(data?.monthly_expense) || 0) / Number(totalBudgetLimit)) * 100) : (Number(data?.monthly_expense) > 0 ? 100 : 0)}%</span>
                  <span>Remaining: {formatCurrencyMetric(Math.max(0, (Number(totalBudgetLimit) || 0) - (Number(data?.monthly_expense) || 0)), currencySymbol)}</span>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center text-center py-4 my-auto">
                <span className="text-xs font-semibold text-slate-400 mb-1">No Budget Configured</span>
                <p className="text-[11px] text-slate-500 max-w-[200px] mb-3">Set up category limits below to start tracking your monthly spending pace.</p>
                <button
                  onClick={() => {
                    const el = document.getElementById("budgets-section");
                    if (el) el.scrollIntoView({ behavior: "smooth" });
                    else navigate("/budget");
                  }}
                  className="px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold transition-all"
                >
                  Configure Budget
                </button>
              </div>
            )}
          </div>

          {/* Card 2: Savings Goal Tracker */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col justify-between">
            {primaryGoal ? (
              <>
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Savings Goal</span>
                    <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-blue-500/10 border border-blue-500/20 text-blue-400">
                      Target Fund
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-300 font-semibold uppercase truncate">{primaryGoal.title}</p>
                  <div className="flex justify-between items-end mb-2">
                    <div>
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Current</p>
                      <p className="text-xl font-black text-blue-400">
                        {formatCurrencyMetric(primaryGoal.current_amount, currencySymbol)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Target</p>
                      <p className="text-xs font-bold text-slate-400">
                        {formatCurrencyMetric(primaryGoal.target_amount, currencySymbol)}
                      </p>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden mb-2">
                    <div 
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${Number(primaryGoal.target_amount) > 0 ? Math.min(100, ((Number(primaryGoal.current_amount) || 0) / Number(primaryGoal.target_amount)) * 100) : 0}%` }}
                    />
                  </div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-semibold">
                  <span>Goal Met: {Number(primaryGoal.target_amount) > 0 ? Math.round(((Number(primaryGoal.current_amount) || 0) / Number(primaryGoal.target_amount)) * 100) : 0}%</span>
                  <span>Missing: {formatCurrencyMetric(Math.max(0, (Number(primaryGoal.target_amount) || 0) - (Number(primaryGoal.current_amount) || 0)), currencySymbol)}</span>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center text-center py-4 my-auto">
                <span className="text-xs font-semibold text-slate-400 mb-1">No Active Savings Goals</span>
                <p className="text-[11px] text-slate-500 max-w-[200px] mb-3">Define a goal milestone below to activate tracking.</p>
                <button
                  onClick={() => {
                    const el = document.getElementById("savings-goals-section");
                    if (el) el.scrollIntoView({ behavior: "smooth" });
                    else navigate("/goals");
                  }}
                  className="px-3 py-1.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-semibold transition-all"
                >
                  Create First Goal
                </button>
              </div>
            )}
          </div>

          {/* Card 3: Forecast & PDF Export */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">AI Forecast & Actions</span>
                <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  Linear Trend
                </span>
              </div>
              <div className="space-y-1 mb-3">
                <p className="text-[10px] text-slate-500 font-semibold uppercase leading-none">Projected Next Month Spent</p>
                <h4 className="text-md font-extrabold text-white">
                  {formatCurrencyMetric(data?.forecasted_expense, currencySymbol)}
                </h4>
                <p className="text-[8px] text-slate-500">Based on historical transactions slope</p>
              </div>
            </div>
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-slate-950 font-bold py-2 px-4 rounded-xl text-xs transition-colors duration-200"
            >
              {downloadingPdf ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating PDF...
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5" /> Download PDF Report
                </>
              )}
            </button>
          </div>
        </section>

        {/* ROW 1: Risk Parameters (sliders) & Diagnostics */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Sliders (4 cols) */}
          <div className="lg:col-span-4 glass-panel p-6 rounded-3xl border border-white/5">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                <Sliders className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-white">Risk Parameters</h2>
            </div>

            <form onSubmit={handleProfileSubmit} className="space-y-4">
              <div>
                <label className="flex justify-between text-xs text-slate-400 mb-1.5 font-medium">
                  <span>Monthly Income</span>
                  <span className="text-emerald-400 font-semibold">₹{Number(profileForm.monthly_income).toLocaleString("en-IN")}</span>
                </label>
                <input
                  type="range"
                  min="10000"
                  max="500000"
                  step="5000"
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  value={profileForm.monthly_income}
                  onChange={(e) => setProfileForm({ ...profileForm, monthly_income: Number(e.target.value) })}
                />
              </div>

              <div>
                <label className="flex justify-between text-xs text-slate-400 mb-1.5 font-medium">
                  <span>Savings Rate</span>
                  <span className="text-emerald-400 font-semibold">{profileForm.savings_rate}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="90"
                  step="1"
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  value={profileForm.savings_rate}
                  onChange={(e) => setProfileForm({ ...profileForm, savings_rate: Number(e.target.value) })}
                />
              </div>

              <div>
                <label className="flex justify-between text-xs text-slate-400 mb-1.5 font-medium">
                  <span>Debt-to-Income Ratio</span>
                  <span className={`${profileForm.debt_ratio > 40 ? "text-amber-400" : "text-emerald-400"} font-semibold`}>
                    {profileForm.debt_ratio}%
                  </span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  value={profileForm.debt_ratio}
                  onChange={(e) => setProfileForm({ ...profileForm, debt_ratio: Number(e.target.value) })}
                />
              </div>

              <div>
                <label className="flex justify-between text-xs text-slate-400 mb-1.5 font-medium">
                  <span>Spending Consistency</span>
                  <span className="text-emerald-400 font-semibold">{profileForm.spending_consistency}%</span>
                </label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  value={profileForm.spending_consistency}
                  onChange={(e) => setProfileForm({ ...profileForm, spending_consistency: Number(e.target.value) })}
                />
              </div>

              <div>
                <label className="flex justify-between text-xs text-slate-400 mb-1.5 font-medium">
                  <span>Emergency Fund Reserves</span>
                  <span className="text-emerald-400 font-semibold">{profileForm.emergency_fund_months} Months</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="12"
                  step="1"
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  value={profileForm.emergency_fund_months}
                  onChange={(e) => setProfileForm({ ...profileForm, emergency_fund_months: Number(e.target.value) })}
                />
              </div>

              <button
                type="submit"
                disabled={updatingProfile}
                className="w-full mt-4 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-65 text-slate-950 font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-emerald-500/20"
              >
                {updatingProfile ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                Recalculate Analysis
              </button>
            </form>
          </div>

          {/* Dial and AI Diagnostics (8 cols) */}
          <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Score Ring (5 cols) */}
            <div className="md:col-span-5 glass-panel p-6 rounded-3xl border border-white/5 flex flex-col justify-between items-center relative overflow-hidden">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Behavior Diagnostics</h2>
              
              <div className="relative w-36 h-36 flex items-center justify-center my-2">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    className="stroke-slate-800"
                    strokeWidth="10"
                    fill="transparent"
                  />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    className="stroke-emerald-400 transition-all duration-1000 ease-out"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray="440"
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-4xl font-extrabold text-white">{healthScore}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">out of 100</span>
                </div>
              </div>
              
              <div className="text-center space-y-2 mt-2 w-full border-t border-white/5 pt-3">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Score Grade:</span>
                  <span className="text-emerald-400 font-bold">{data?.health_score_grade}</span>
                </div>
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">ML Risk Profile:</span>
                  <span className={`font-bold ${
                    data?.risk_level === "High"
                      ? "text-red-400"
                      : data?.risk_level === "Medium"
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}>
                    {data?.risk_level} ({Math.round(data?.risk_confidence * 100)}% Conf)
                  </span>
                </div>
              </div>
            </div>

            {/* AI insights (7 cols) */}
            <div className="md:col-span-7 glass-panel p-6 rounded-3xl border border-white/5 flex flex-col relative overflow-hidden">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-bold text-white">AI Diagnostics & Advice</h2>
              </div>
              
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 max-h-[190px] overflow-y-auto pr-1">
                {/* Observations */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-2">Observations</h4>
                  <div className="space-y-2">
                    {(!data?.insights || data.insights.length === 0) ? (
                      <p className="text-[10px] text-slate-500 py-2">No observations recorded.</p>
                    ) : (
                      data.insights.map((insight: string, idx: number) => (
                        <div key={idx} className="p-2.5 rounded-xl text-[10px] bg-white/[0.02] border border-white/5 text-slate-300 leading-relaxed font-medium">
                          {insight}
                        </div>
                      ))
                    )}
                  </div>
                </div>
                {/* Recommendations */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-2">Recommendations</h4>
                  <div className="space-y-2">
                    {(!data?.recommendations || data.recommendations.length === 0) ? (
                      <p className="text-[10px] text-slate-500 py-2">No recommendations generated.</p>
                    ) : (
                      data.recommendations.map((rec: string, idx: number) => (
                        <div key={idx} className="p-2.5 rounded-xl text-[10px] bg-emerald-500/5 border border-emerald-500/10 text-emerald-300 flex gap-1.5 items-start leading-relaxed font-semibold">
                          <span className="text-emerald-400 font-black">•</span>
                          <span>{rec}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ROW 2: Recharts Charts */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Pie Chart: Expense by Category */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Expense by Category</h3>
            <div className="flex-1 min-h-0 relative flex items-center justify-center">
              {expenseByCategoryData.length === 0 ? (
                <div className="text-xs text-slate-500">No expenses recorded</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={expenseByCategoryData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={65}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {expenseByCategoryData.map((_entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                      labelStyle={{ color: "white", fontSize: "11px", fontWeight: "bold" }}
                      itemStyle={{ fontSize: "10px" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="flex flex-wrap gap-x-2.5 gap-y-1 justify-center mt-2 text-[9px] text-slate-400">
              {expenseByCategoryData.slice(0, 4).map((item: any, idx: number) => (
                <div key={item.name} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                  <span>{item.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar Chart: Monthly Spending History */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Monthly Spending</h3>
            <div className="flex-1 min-h-0">
              {timeChartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">No transaction records</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={timeChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="month" stroke="#64748b" fontSize={9} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                      labelStyle={{ color: "white", fontSize: "11px", fontWeight: "bold" }}
                      itemStyle={{ fontSize: "10px" }}
                    />
                    <Bar dataKey="Expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Bar Chart: Expense Forecast */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Monthly Expense Forecast</h3>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forecastBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={9} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                    labelStyle={{ color: "white", fontSize: "11px", fontWeight: "bold" }}
                    itemStyle={{ fontSize: "10px" }}
                  />
                  <Bar dataKey="Spent" name="Expense Amount" radius={[4, 4, 0, 0]}>
                    <Cell fill="#3b82f6" />
                    <Cell fill="#8b5cf6" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 text-center text-[9px] text-slate-500 font-medium">
              Linear Trend: {data?.forecasted_expense !== undefined && data?.forecasted_expense !== null && !isNaN(Number(data?.forecasted_expense)) ? formatCurrencyMetric(data.forecasted_expense, currencySymbol) : "Unavailable"}
            </div>
          </div>

          {/* Line Chart: Income vs Expense Trend */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Income vs Expense Trend</h3>
            <div className="flex-1 min-h-0">
              {timeChartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">No transaction trends found</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={timeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" stroke="#64748b" fontSize={9} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                      labelStyle={{ color: "white", fontSize: "12px", fontWeight: "bold" }}
                      itemStyle={{ fontSize: "11px" }}
                    />
                    <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: "10px" }} />
                    <Line type="monotone" dataKey="Income" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="Expense" stroke="#ef4444" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </section>

        {/* ROW 3: Budgets and Goals */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Budget Limit Allocations */}
          <div id="budgets-section" className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col">
            <h3 className="text-base font-bold text-white mb-6">Budget Limit Utilizations</h3>
            
            <div className="space-y-4 max-h-[260px] overflow-y-auto pr-1 mb-6 flex-1">
              {(!data?.budgets || data.budgets.length === 0) ? (
                <div className="h-full flex flex-col items-center justify-center text-center py-8 text-slate-500 text-xs">
                  <CreditCard className="w-8 h-8 text-slate-600 mb-2 opacity-60" />
                  <span>No budget categories established</span>
                  <span className="text-[10px] text-slate-600 mt-0.5">Add your first category below</span>
                </div>
              ) : (
                data.budgets.map((b: any) => {
                  const limit = Number(b.monthly_limit) || 0;
                  const spent = Number(b.spent) || 0;
                  const percent = b.utilization_pct !== undefined
                    ? b.utilization_pct
                    : (limit > 0 ? Math.round((spent / limit) * 100) : (spent > 0 ? 100 : 0));
                  const isOver = spent > limit || (limit === 0 && spent > 0);
                  const isClose = !isOver && limit > 0 && percent >= 75;
                  
                  return (
                    <div key={b.id} className="p-4 rounded-2xl bg-slate-900/40 border border-white/5 animate-in fade-in duration-200">
                      <div className="flex justify-between items-start text-xs font-semibold mb-2">
                        <span className="text-slate-300 font-bold">{b.category}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400">
                            ₹{spent.toLocaleString()} <span className="text-slate-600">/ ₹{limit.toLocaleString()}</span>
                          </span>
                          <button
                            onClick={async () => {
                              if (!confirm(`Remove budget for '${b.category}'? Associated transactions will remain safely in your ledger.`)) return;
                              try {
                                await api.deleteBudget(b.id);
                                loadDashboardData();
                                showNotification(`Budget category '${b.category}' removed.`);
                              } catch (err: any) {
                                showNotification("Failed to delete budget: " + err.message, "error");
                              }
                            }}
                            className="text-[10px] text-red-400 hover:text-red-300 px-1.5 py-0.5 rounded bg-red-500/10 hover:bg-red-500/20 transition-colors"
                            title="Delete budget limit"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 relative overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isOver ? "bg-red-500" : isClose ? "bg-amber-400" : "bg-emerald-500"
                          }`}
                          style={{ width: `${Math.min(100, percent)}%` }}
                        />
                      </div>
                      <div className="flex justify-between items-center mt-2.5">
                        <span className="text-[10px] text-slate-500">Utilization: {percent}%</span>
                        {isOver && <span className="text-[10px] font-bold text-red-400">Overspending Limit</span>}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <form onSubmit={handleBudgetSubmit} className="grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-white/5 pt-4">
              <input
                type="text"
                placeholder="Category (e.g. Shopping)"
                className="w-full px-3.5 py-2 rounded-xl glass-input text-xs"
                value={budgetForm.category}
                onChange={(e) => setBudgetForm({ ...budgetForm, category: e.target.value })}
                required
              />
              <input
                type="number"
                placeholder="Limit (₹)"
                className="w-full px-3.5 py-2 rounded-xl glass-input text-xs"
                value={budgetForm.monthly_limit}
                onChange={(e) => setBudgetForm({ ...budgetForm, monthly_limit: e.target.value })}
                required
                min="1"
              />
              <button
                type="submit"
                disabled={submittingBudget}
                className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl transition-all text-xs flex items-center justify-center gap-1.5 shadow-md"
              >
                {submittingBudget ? <Loader2 className="w-4.5 h-4.5 animate-spin" /> : <Plus className="w-4 h-4" />}
                Add Budget
              </button>
            </form>
          </div>

          {/* Goal milestones */}
          <div id="savings-goals-section" className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col">
            <h3 className="text-base font-bold text-white mb-6">Savings Goal Progress</h3>
            
            <div className="space-y-4 max-h-[260px] overflow-y-auto pr-1 mb-6 flex-1">
              {(!data?.goals || data.goals.length === 0) ? (
                <div className="h-full flex flex-col items-center justify-center text-center py-8 text-slate-500 text-xs">
                  <PiggyBank className="w-8 h-8 text-slate-600 mb-2 opacity-60" />
                  <span>No savings goals registered</span>
                  <span className="text-[10px] text-slate-600 mt-0.5">Define your first target below</span>
                </div>
              ) : (
                data.goals.map((g: any) => {
                  const percent = Math.round((g.current_amount / g.target_amount) * 100);
                  
                  return (
                    <div key={g.id} className="p-4 rounded-2xl bg-slate-900/40 border border-white/5">
                      <div className="flex justify-between text-xs font-semibold mb-2">
                        <span className="text-slate-300">{g.title}</span>
                        <span className="text-slate-400">
                          ₹{g.current_amount.toLocaleString()} <span className="text-slate-600">/ ₹{g.target_amount.toLocaleString()}</span>
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 relative overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500 bg-emerald-500"
                          style={{ width: `${Math.min(100, percent)}%` }}
                        />
                      </div>
                      <div className="flex justify-between items-center mt-3">
                        <span className="text-[10px] text-slate-500">Target: {g.target_date}</span>
                        <span className="text-[10px] text-slate-500">Progress: {percent}%</span>
                      </div>
                      <div className="flex items-center gap-2 mt-3.5 pt-3.5 border-t border-white/5">
                        <input
                          type="number"
                          placeholder="Amount (₹)"
                          className="w-24 px-2.5 py-1 rounded-lg glass-input text-xs"
                          value={depositAmount[g.id] || ""}
                          onChange={(e) => setDepositAmount({ ...depositAmount, [g.id]: e.target.value })}
                          min="1"
                        />
                        <button
                          onClick={() => handleDeposit(g.id)}
                          className="px-3 py-1 bg-emerald-500/10 hover:bg-emerald-500 hover:text-slate-950 border border-emerald-500/35 rounded-lg text-emerald-400 text-xs font-bold transition-all"
                        >
                          Deposit
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <form onSubmit={handleGoalSubmit} className="grid grid-cols-1 sm:grid-cols-4 gap-3 border-t border-white/5 pt-4">
              <input
                type="text"
                placeholder="Milestone target"
                className="w-full px-3.5 py-2 rounded-xl glass-input text-xs sm:col-span-2"
                value={goalForm.title}
                onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })}
                required
              />
              <input
                type="number"
                placeholder="Target (₹)"
                className="w-full px-3.5 py-2 rounded-xl glass-input text-xs"
                value={goalForm.target_amount}
                onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                required
                min="1"
              />
              <input
                type="date"
                className="w-full px-3.5 py-2 rounded-xl glass-input text-xs"
                value={goalForm.target_date}
                onChange={(e) => setGoalForm({ ...goalForm, target_date: e.target.value })}
                required
              />
              <button
                type="submit"
                disabled={submittingGoal}
                className="w-full sm:col-span-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-md"
              >
                {submittingGoal ? <Loader2 className="w-4.5 h-4.5 animate-spin" /> : <Plus className="w-4 h-4" />}
                Add Goal Target
              </button>
            </form>
          </div>
        </section>

        {/* Goal Allocation Modal for One-Time Windfalls */}
        {allocatingSource && (
          <GoalAllocationModal
            incomeSourceId={allocatingSource.id}
            incomeAmount={allocatingSource.unallocated_amount ?? allocatingSource.amount}
            incomeName={allocatingSource.name}
            goals={data?.goals || []}
            onClose={() => setAllocatingSource(null)}
            onAllocated={() => {
              showNotification("Windfall successfully allocated to goals & free cash!", "success");
              loadDashboardData();
            }}
          />
        )}

      </main>
    </div>
  );
};
