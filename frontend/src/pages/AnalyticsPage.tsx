import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { api } from "../services/api";
import { transactionsApi } from "../services/transactions";
import {
  TrendingUp, Sparkles, Loader2, ArrowUpRight, ArrowDownRight,
  PieChart as PieIcon, BarChart2
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, LineChart, Line, CartesianGrid, Legend
} from "recharts";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e"];

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const summary = await api.getSummary();
      const transList = await transactionsApi.list();
      setData(summary);
      setTransactions(transList);
    } catch (err) {
      console.error("Failed to load analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-emerald-400 animate-spin" />
          <div className="text-emerald-400 font-semibold tracking-wider text-xs">Aggregating Ledger Analytics...</div>
        </div>
      </div>
    );
  }

  // 1. Pie Chart: Expenses by Category
  const categoryExpenses = data?.budgets?.map((b: any) => ({
    name: b.category,
    value: b.spent
  })).filter((item: any) => item.value > 0) || [];

  // 2. Line Chart: Monthly Income vs Expenses
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

  const timeChartData = Object.keys(monthlyDataMap).reverse().map(key => monthlyDataMap[key]);

  // 3. Bar Chart: Budget Utilization
  const budgetUtilizationData = data?.budgets?.map((b: any) => ({
    category: b.category,
    Limit: b.monthly_limit,
    Spent: b.spent
  })) || [];

  // Calculate highest spending category
  let topSpentCat = "N/A";
  let topSpentAmount = 0;
  if (categoryExpenses.length > 0) {
    const sorted = [...categoryExpenses].sort((a, b) => b.value - a.value);
    topSpentCat = sorted[0].name;
    topSpentAmount = sorted[0].value;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      
      <Header />

      <main className="max-w-7xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-8 relative z-10">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-black text-white">Visual Analytics Dashboard</h1>
          </div>
          <p className="text-xs text-slate-400">
            Deep dive into your transaction distributions, budget limits, and income vs. spending trajectories.
          </p>
        </div>

        {/* Analytical Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Top Spending Category</span>
              <h3 className="text-xl font-black text-amber-400">{topSpentCat}</h3>
              <p className="text-[9px] text-slate-500">₹{topSpentAmount.toLocaleString("en-IN")} spent this month</p>
            </div>
            <div className="w-12 h-12 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-2xl flex items-center justify-center">
              <PieIcon className="w-5 h-5" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Net Savings Rate</span>
              <h3 className="text-xl font-black text-emerald-400">{data?.profile?.savings_rate || 0}%</h3>
              <p className="text-[9px] text-slate-500">Target rate for monthly savings</p>
            </div>
            <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl flex items-center justify-center">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Debt-to-Income Ratio</span>
              <h3 className="text-xl font-black text-red-400">{data?.profile?.debt_ratio || 0}%</h3>
              <p className="text-[9px] text-slate-500">Lower this ratio to boost health score</p>
            </div>
            <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl flex items-center justify-center">
              <ArrowDownRight className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Visual Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Income vs Expenses Over Time */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white font-bold uppercase tracking-wider">Income vs Expenses Over Time</span>
              <Sparkles className="w-4.5 h-4.5 text-emerald-400" />
            </div>
            <div className="h-72 w-full">
              {timeChartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">No transaction trends found.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={timeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.05)" }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line type="monotone" dataKey="Income" stroke="#10b981" strokeWidth={2} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="Expense" stroke="#ef4444" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Expense breakdown by Category */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white font-bold uppercase tracking-wider">Expense Distribution</span>
              <PieIcon className="w-4.5 h-4.5 text-emerald-400" />
            </div>
            <div className="h-72 w-full flex items-center justify-center">
              {categoryExpenses.length === 0 ? (
                <div className="text-xs text-slate-500">No expense records found.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryExpenses}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    >
                      {categoryExpenses.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.05)" }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Budget Limits vs actual spending */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col gap-4 lg:col-span-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white font-bold uppercase tracking-wider">Budget Caps vs. Actual Expenses</span>
              <BarChart2 className="w-4.5 h-4.5 text-emerald-400" />
            </div>
            <div className="h-72 w-full">
              {budgetUtilizationData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">No budgets initialized. Create a budget in the planner.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={budgetUtilizationData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" />
                    <XAxis dataKey="category" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={10} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.05)" }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="Limit" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Spent" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
};
export default AnalyticsPage;
