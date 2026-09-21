import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getAvatarUrl } from "../services/api";
import { recurringApi } from "../services/recurring";
import type { RecurringPayment, RecurringPaymentSummary } from "../services/recurring";
import {
  Activity, Sparkles, Check, X, AlertCircle, Loader2,
  Calendar, LogOut, Trash2,
  CreditCard, Clock, Layers, User as UserIcon
} from "lucide-react";

export const SubscriptionsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [payments, setPayments] = useState<RecurringPayment[]>([]);
  const [summary, setSummary] = useState<RecurringPaymentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | "confirmed" | "detected" | "dismissed">("all");
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [items, sum] = await Promise.all([
        recurringApi.list(),
        recurringApi.summary(),
      ]);
      setPayments(items);
      setSummary(sum);
    } catch (err: any) {
      showToast(err.message || "Failed to load recurring payments", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await recurringApi.scan();
      showToast(res.message || "Transaction scan completed!", "success");
      setPayments(res.items);
      const sum = await recurringApi.summary();
      setSummary(sum);
    } catch (err: any) {
      showToast(err.message || "Failed to scan transactions", "error");
    } finally {
      setScanning(false);
    }
  };

  const handleStatusChange = async (id: string, newStatus: "confirmed" | "dismissed" | "detected") => {
    setActionInProgress(id);
    try {
      const updated = await recurringApi.update(id, { status: newStatus });
      setPayments(prev => prev.map(p => p.id === id ? updated : p));
      const sum = await recurringApi.summary();
      setSummary(sum);
      showToast(`Subscription marked as ${newStatus}`, "success");
    } catch (err: any) {
      showToast(err.message || `Failed to update status`, "error");
    } finally {
      setActionInProgress(null);
    }
  };

  const handleDelete = async (id: string, merchant: string) => {
    if (!confirm(`Are you sure you want to remove ${merchant} from your recurring list?`)) return;
    setActionInProgress(id);
    try {
      await recurringApi.delete(id);
      setPayments(prev => prev.filter(p => p.id !== id));
      const sum = await recurringApi.summary();
      setSummary(sum);
      showToast(`Removed ${merchant} from recurring payments`, "success");
    } catch (err: any) {
      showToast(err.message || "Failed to delete record", "error");
    } finally {
      setActionInProgress(null);
    }
  };

  const filteredPayments = payments.filter(p => {
    if (statusFilter === "all") return true;
    return p.status === statusFilter;
  });

  const formatCurrency = (val: number) => `₹${Number(val || 0).toLocaleString("en-IN")}`;

  const getFrequencyLabel = (freq: string) => {
    switch (freq) {
      case "weekly": return "Weekly";
      case "biweekly": return "Bi-Weekly";
      case "monthly": return "Monthly";
      case "quarterly": return "Quarterly";
      case "annual": return "Annual";
      default: return freq;
    }
  };

  const getDaysUntil = (dateStr: string | null) => {
    if (!dateStr) return null;
    const target = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    target.setHours(0, 0, 0, 0);
    const diff = Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-blue-500/5 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/5 py-4 px-6 md:px-12 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center glow-emerald">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-emerald-400 bg-clip-text text-transparent mr-6">
            FinRisk AI
          </span>
          <div className="hidden md:flex items-center gap-4 text-xs font-semibold text-slate-400">
            <Link to="/dashboard" className="hover:text-emerald-400 transition-colors">Dashboard</Link>
            <Link to="/transactions" className="hover:text-emerald-400 transition-colors">Transactions</Link>
            <Link to="/subscriptions" className="text-white hover:text-emerald-400 transition-colors font-bold">Subscriptions</Link>
            <Link to="/settings" className="hover:text-emerald-400 transition-colors">Settings</Link>
            {user?.is_admin && (
              <Link to="/admin" className="hover:text-red-400 transition-colors text-red-400 font-bold">Admin</Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
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

      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-24 right-6 z-50 px-5 py-3.5 rounded-2xl glass-panel border shadow-2xl flex items-center gap-3 transition-all duration-300 transform translate-y-0 animate-bounce ${
          notification.type === "error" ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
        }`}>
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-xs font-semibold">{notification.message}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto w-full px-6 md:px-12 pt-8 relative z-10 flex flex-col gap-8">
        {/* Title and Scan Trigger */}
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-emerald-400 bg-clip-text text-transparent">
                Recurring Commitments & Subscriptions
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                Pattern AI
              </span>
            </div>
            <p className="text-slate-400 text-xs mt-1">
              Deterministic detection of recurring bills, streaming subscriptions, and scheduled financial commitments.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 disabled:opacity-60 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-2 shadow-lg hover:shadow-emerald-500/20 transition-all cursor-pointer"
            >
              {scanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  <span>Scanning Ledger...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-slate-950" />
                  <span>Scan Transactions</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Summary Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Estimated Monthly Commitment */}
          <div className="glass-panel p-5 rounded-3xl border border-white/5 relative overflow-hidden flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider">Est. Monthly Cost</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-white">
                {summary ? formatCurrency(summary.total_monthly_commitment) : "—"}
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                Normalized monthly obligation
              </p>
            </div>
          </div>

          {/* Projected Annual Commitment */}
          <div className="glass-panel p-5 rounded-3xl border border-white/5 relative overflow-hidden flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider">Projected Annual Cost</span>
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Calendar className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-white">
                {summary ? formatCurrency(summary.total_annual_commitment) : "—"}
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                Annual commitment across active items
              </p>
            </div>
          </div>

          {/* Active Subscriptions Count */}
          <div className="glass-panel p-5 rounded-3xl border border-white/5 relative overflow-hidden flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider">Active Subscriptions</span>
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-white">
                {summary ? summary.active_subscriptions_count : "—"}
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                {summary?.confirmed_count || 0} confirmed · {summary?.detected_count || 0} to review
              </p>
            </div>
          </div>

          {/* Upcoming in Next 30 Days */}
          <div className="glass-panel p-5 rounded-3xl border border-white/5 relative overflow-hidden flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider">Upcoming (30 Days)</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-white">
                {summary ? summary.upcoming_payments_next_30_days.length : "—"}
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                Estimated payments in next 30 days
              </p>
            </div>
          </div>
        </div>

        {/* Upcoming Obligations Timeline */}
        {summary && summary.upcoming_payments_next_30_days.length > 0 && (
          <div className="glass-panel p-6 rounded-3xl border border-white/5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Upcoming Obligations (Next 30 Days)</h3>
              </div>
              <span className="text-[10px] text-slate-400">Dates are estimated projections</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {summary.upcoming_payments_next_30_days.map((item) => {
                const daysUntil = getDaysUntil(item.next_estimated_date);
                return (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-2xl bg-slate-900/60 border border-white/5 flex flex-col justify-between"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-white truncate max-w-[140px]">{item.merchant_name}</h4>
                        <span className="text-[10px] text-slate-400">{item.category}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                        {formatCurrency(item.last_amount)}
                      </span>
                    </div>

                    <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between text-[11px]">
                      <span className="text-slate-400 font-mono text-[10px]">{item.next_estimated_date}</span>
                      <span className={`font-semibold text-[10px] ${
                        daysUntil !== null && daysUntil <= 5 ? "text-amber-400 font-bold" : "text-slate-400"
                      }`}>
                        {daysUntil !== null ? (daysUntil === 0 ? "Due Today" : `In ${daysUntil} day${daysUntil > 1 ? "s" : ""}`) : "—"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Filter Controls & List Header */}
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900/80 border border-white/5 w-fit">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === "all"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              All ({payments.length})
            </button>
            <button
              onClick={() => setStatusFilter("confirmed")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === "confirmed"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Confirmed ({payments.filter(p => p.status === "confirmed").length})
            </button>
            <button
              onClick={() => setStatusFilter("detected")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === "detected"
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              To Review ({payments.filter(p => p.status === "detected").length})
            </button>
            <button
              onClick={() => setStatusFilter("dismissed")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === "dismissed"
                  ? "bg-slate-700/40 text-slate-300 border border-white/10"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Dismissed ({payments.filter(p => p.status === "dismissed").length})
            </button>
          </div>

          <span className="text-xs text-slate-400 font-mono">
            Showing {filteredPayments.length} of {payments.length} items
          </span>
        </div>

        {/* Subscriptions Table */}
        <div className="glass-panel rounded-3xl border border-white/5 overflow-hidden shadow-2xl">
          {loading ? (
            <div className="h-80 flex flex-col justify-center items-center gap-4 bg-slate-900/10">
              <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
              <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Loading commitments...</span>
            </div>
          ) : filteredPayments.length === 0 ? (
            <div className="h-80 flex flex-col justify-center items-center gap-4 text-center p-8 bg-slate-900/10">
              <Calendar className="w-12 h-12 text-slate-600" />
              <h3 className="text-sm font-bold text-slate-300">
                {statusFilter === "all"
                  ? "No recurring payments detected yet"
                  : `No ${statusFilter} subscriptions found`}
              </h3>
              <p className="text-xs text-slate-500 max-w-md">
                {statusFilter === "all"
                  ? "Click 'Scan Transactions' above to analyze your transaction history for recurring bills and subscriptions."
                  : `Switch your filter to 'All' or run a scan to detect new recurring payments.`}
              </p>
              {statusFilter === "all" && (
                <button
                  onClick={handleScan}
                  disabled={scanning}
                  className="mt-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-bold hover:bg-emerald-500/30 transition-all flex items-center gap-2 cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" />
                  Scan Now
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-900/50 text-slate-400 uppercase tracking-wider font-semibold border-b border-white/5 text-[10px]">
                    <th className="py-4 px-6">Merchant / Commitment</th>
                    <th className="py-4 px-6">Frequency</th>
                    <th className="py-4 px-6">Estimated Cost</th>
                    <th className="py-4 px-6">Last Observed</th>
                    <th className="py-4 px-6">Next Estimated Date</th>
                    <th className="py-4 px-6 text-center">Confidence</th>
                    <th className="py-4 px-6 text-center">Status</th>
                    <th className="py-4 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-medium">
                  {filteredPayments.map((p) => {
                    const isBusy = actionInProgress === p.id;
                    const isHigh = p.confidence >= 0.85;
                    const isMed = p.confidence >= 0.70 && p.confidence < 0.85;

                    return (
                      <tr
                        key={p.id}
                        className={`hover:bg-white/[0.02] transition-colors text-slate-200 ${
                          p.status === "dismissed" ? "opacity-50" : ""
                        }`}
                      >
                        {/* Merchant & Category */}
                        <td className="py-4 px-6">
                          <div className="flex flex-col">
                            <span className="font-bold text-white text-xs">{p.merchant_name}</span>
                            <span className="text-[10px] text-slate-400">{p.category} · {p.transaction_count} txs</span>
                          </div>
                        </td>

                        {/* Frequency */}
                        <td className="py-4 px-6">
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-800 border border-white/10 text-slate-300">
                            {getFrequencyLabel(p.frequency)}
                          </span>
                        </td>

                        {/* Estimated Amount & Monthly Cost */}
                        <td className="py-4 px-6">
                          <div className="flex flex-col">
                            <span className="font-bold text-white">{formatCurrency(p.last_amount)}</span>
                            <span className="text-[10px] text-emerald-400 font-semibold font-mono">
                              ~{formatCurrency(p.estimated_monthly_cost)}/mo
                            </span>
                          </div>
                        </td>

                        {/* Last Observed Date */}
                        <td className="py-4 px-6 font-mono text-slate-400 text-[11px]">
                          {p.last_payment_date}
                        </td>

                        {/* Next Estimated Date */}
                        <td className="py-4 px-6">
                          {p.next_estimated_date ? (
                            <div className="flex flex-col">
                              <span className="font-mono text-slate-300 text-[11px]">{p.next_estimated_date}</span>
                              <span className="text-[9px] text-slate-500">Estimated projection</span>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-[11px] italic">Unavailable</span>
                          )}
                        </td>

                        {/* Confidence Score */}
                        <td className="py-4 px-6 text-center">
                          {isHigh ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                              High ({Math.round(p.confidence * 100)}%)
                            </span>
                          ) : isMed ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                              Med ({Math.round(p.confidence * 100)}%)
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                              Low ({Math.round(p.confidence * 100)}%)
                            </span>
                          )}
                        </td>

                        {/* Status */}
                        <td className="py-4 px-6 text-center">
                          {p.status === "confirmed" ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              Confirmed
                            </span>
                          ) : p.status === "detected" ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                              Detected
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-white/10">
                              Dismissed
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {p.status === "detected" && (
                              <>
                                <button
                                  onClick={() => handleStatusChange(p.id, "confirmed")}
                                  disabled={isBusy}
                                  className="p-1.5 rounded-lg border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 transition-all"
                                  title="Confirm recurring payment"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleStatusChange(p.id, "dismissed")}
                                  disabled={isBusy}
                                  className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
                                  title="Dismiss (false positive)"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}

                            {p.status === "confirmed" && (
                              <button
                                onClick={() => handleStatusChange(p.id, "dismissed")}
                                disabled={isBusy}
                                className="px-2 py-1 rounded-lg border border-slate-700 text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all text-[10px]"
                                title="Dismiss subscription"
                              >
                                Dismiss
                              </button>
                            )}

                            {p.status === "dismissed" && (
                              <button
                                onClick={() => handleStatusChange(p.id, "confirmed")}
                                disabled={isBusy}
                                className="px-2 py-1 rounded-lg border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 transition-all text-[10px]"
                                title="Restore subscription"
                              >
                                Restore
                              </button>
                            )}

                            <button
                              onClick={() => handleDelete(p.id, p.merchant_name)}
                              disabled={isBusy}
                              className="p-1.5 rounded-lg border border-transparent hover:border-red-500/30 text-slate-500 hover:text-red-400 transition-all"
                              title="Delete record"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
