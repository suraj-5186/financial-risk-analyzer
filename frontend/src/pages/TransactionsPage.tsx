import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL, getAvatarUrl } from "../services/api";
import { transactionsApi } from "../services/transactions";
import type { Transaction, ParseCsvItem } from "../services/transactions";
import {
  Search, Plus, Edit2, Trash2, ArrowUpDown, X, Loader2,
  Calendar, Check, AlertCircle, Sparkles, ChevronLeft, ChevronRight, LogOut, Activity, Upload, Download, User as UserIcon, Building2
} from "lucide-react";

// Form validation schema using Zod
const transactionSchema = z.object({
  type: z.enum(["Income", "Expense"]),
  category: z.string().min(1, "Category is required"),
  amount: z.number().gt(0, "Amount must be greater than 0"),
  transaction_date: z.string().refine((val) => {
    const selected = new Date(val);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    selected.setHours(0, 0, 0, 0);
    return selected <= today;
  }, { message: "Future dates are not allowed" }),
  payment_method: z.string().min(1, "Payment method is required"),
  description: z.string().optional(),
});



export const INCOME_CATEGORIES = ["Salary", "Freelance", "Business", "Investment", "Transfers", "Other"];
export const EXPENSE_CATEGORIES = ["Food", "Shopping", "Transport", "Bills & Utilities", "Healthcare", "Entertainment", "Rent", "Education", "Transfers", "Other", "Needs Review"];
const PAYMENT_METHODS = ["Cash", "Card", "UPI", "Bank Transfer"];

export const TransactionsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Statement Review & Auto-Categorization Modal states
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [parsedItems, setParsedItems] = useState<ParseCsvItem[]>([]);
  const [selectedTempIds, setSelectedTempIds] = useState<Set<string>>(new Set());
  const [parsingCsv, setParsingCsv] = useState(false);
  const [confirmingImport, setConfirmingImport] = useState(false);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleExportCsv = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/transactions/export-csv`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transactions_${user?.full_name.toLowerCase().replace(" ", "_") || "user"}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      showToast(err.message || "Failed to export CSV", "error");
    }
  };

  const handleExportPdf = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/transactions/export-pdf`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transactions_${user?.full_name.toLowerCase().replace(" ", "_") || "user"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      showToast(err.message || "Failed to export PDF", "error");
    }
  };

  const handleSelectCsvFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setParsingCsv(true);
    try {
      const res = await transactionsApi.parseCsv(file);
      setParsedItems(res.items);
      // Pre-select non-duplicate items by default
      const nonDups = new Set(res.items.filter(it => !it.is_duplicate).map(it => it.temp_id));
      setSelectedTempIds(nonDups);
      setPreviewModalOpen(true);
    } catch (err: any) {
      showToast(err.message || "Failed to parse bank statement CSV", "error");
    } finally {
      setParsingCsv(false);
      e.target.value = "";
    }
  };

  const handleConfirmImport = async () => {
    const toImport = parsedItems.filter(it => selectedTempIds.has(it.temp_id));
    if (toImport.length === 0) {
      showToast("Please select at least one transaction to import", "error");
      return;
    }
    setConfirmingImport(true);
    try {
      const res = await transactionsApi.confirmImport(toImport, false);
      showToast(res.message || `Successfully imported ${toImport.length} transactions!`, "success");
      setPreviewModalOpen(false);
      setParsedItems([]);
      loadTransactions();
    } catch (err: any) {
      showToast(err.message || "Failed to import transactions", "error");
    } finally {
      setConfirmingImport(false);
    }
  };

  const handleItemCategoryChange = (tempId: string, newCat: string) => {
    setParsedItems(prev => prev.map(it => {
      if (it.temp_id === tempId) {
        return {
          ...it,
          category: newCat,
          is_reviewed: true,
          category_confidence: 1.0,
        };
      }
      return it;
    }));
  };

  const handleToggleSelectTempId = (tempId: string) => {
    setSelectedTempIds(prev => {
      const next = new Set(prev);
      if (next.has(tempId)) {
        next.delete(tempId);
      } else {
        next.add(tempId);
      }
      return next;
    });
  };

  const handleSelectAllNonDuplicates = () => {
    const nonDups = new Set(parsedItems.filter(it => !it.is_duplicate).map(it => it.temp_id));
    setSelectedTempIds(nonDups);
  };

  const handleSelectAll = () => {
    setSelectedTempIds(new Set(parsedItems.map(it => it.temp_id)));
  };

  const handleDeselectAll = () => {
    setSelectedTempIds(new Set());
  };

  const loadTransactions = async () => {
    setLoading(true);
    try {
      let data: Transaction[] = [];
      if (searchQuery.trim() !== "") {
        data = await transactionsApi.search(searchQuery);
      } else {
        const params: any = {};
        if (typeFilter !== "All") params.type = typeFilter;
        if (categoryFilter !== "All") params.category = categoryFilter;
        data = await transactionsApi.list(params);
      }
      setTransactions(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load transactions", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
    setCurrentPage(1);
  }, [typeFilter, categoryFilter, searchQuery]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      type: "Expense",
      category: "",
      amount: 0,
      transaction_date: new Date().toISOString().split("T")[0],
      payment_method: "UPI",
      description: "",
    },
  });

  const transactionType = watch("type");

  // Reset category selection when switching transaction type
  useEffect(() => {
    setValue("category", "");
  }, [transactionType, setValue]);

  const openAddModal = () => {
    setEditingId(null);
    reset({
      type: "Expense",
      category: "",
      amount: 0,
      transaction_date: new Date().toISOString().split("T")[0],
      payment_method: "UPI",
      description: "",
    });
    setIsModalOpen(true);
  };

  const openEditModal = (t: Transaction) => {
    setEditingId(t.id);
    reset({
      type: t.type,
      category: t.category,
      amount: t.amount,
      transaction_date: t.transaction_date,
      payment_method: t.payment_method,
      description: t.description || "",
    });
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (data: any) => {
    try {
      if (editingId) {
        await transactionsApi.update(editingId, data);
        showToast("Transaction successfully updated.");
      } else {
        await transactionsApi.create(data);
        showToast("Transaction successfully registered.");
      }
      setIsModalOpen(false);
      loadTransactions();
    } catch (err: any) {
      showToast(err.message || "Operation failed", "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this transaction?")) return;
    try {
      await transactionsApi.delete(id);
      showToast("Transaction deleted successfully.");
      loadTransactions();
    } catch (err: any) {
      showToast(err.message || "Deletion failed", "error");
    }
  };

  const toggleSort = () => {
    setSortOrder(prev => prev === "asc" ? "desc" : "asc");
  };

  // Sort local copy
  const sortedTransactions = [...transactions].sort((a, b) => {
    const dateA = new Date(a.transaction_date).getTime();
    const dateB = new Date(b.transaction_date).getTime();
    return sortOrder === "asc" ? dateA - dateB : dateB - dateA;
  });

  // Client side pagination
  const totalPages = Math.ceil(sortedTransactions.length / itemsPerPage);
  const paginatedTransactions = sortedTransactions.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
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
            <Link to="/dashboard" className="hover:text-emerald-400 transition-colors">Dashboard</Link>
            <Link to="/transactions" className="text-white hover:text-emerald-400 transition-colors">Transactions</Link>
            <Link to="/subscriptions" className="hover:text-emerald-400 transition-colors">Subscriptions</Link>
            <Link to="/bank-sync" className="hover:text-emerald-400 transition-colors">Bank Sync</Link>
            <Link to="/insights" className="hover:text-emerald-400 transition-colors">Insights</Link>
            <Link to="/settings" className="hover:text-emerald-400 transition-colors">Settings</Link>
            {user?.is_admin && (
              <Link to="/admin" className="hover:text-red-400 transition-colors text-red-400 font-bold">Admin</Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
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

      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-24 right-6 z-50 px-5 py-3.5 rounded-2xl glass-panel border shadow-2xl flex items-center gap-3 transition-all duration-300 transform translate-y-0 animate-bounce ${
          notification.type === "error" ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
        }`}>
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-xs font-semibold">{notification.message}</span>
        </div>
      )}

      {/* Header and filters */}
      <div className="max-w-7xl mx-auto w-full px-6 md:px-12 pt-8 relative z-10 flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-emerald-400 bg-clip-text text-transparent">
              Ledger Transactions
            </h1>
            <p className="text-slate-400 text-xs mt-1">Review, search, filter, and export transaction archives</p>
          </div>
          <div className="flex flex-wrap gap-2.5 items-center justify-end">
            <Link
              to="/bank-sync"
              className="px-4 py-2.5 bg-slate-900 border border-indigo-500/30 hover:border-indigo-500/60 text-indigo-300 font-bold rounded-xl hover:bg-slate-800 transition-all flex items-center justify-center gap-1.5 text-xs shadow-sm"
            >
              <Building2 className="w-4 h-4 text-indigo-400" />
              <span>Bank Sync</span>
            </Link>

            <label className="px-4 py-2.5 bg-slate-900 border border-white/10 hover:border-emerald-500/20 text-slate-300 font-bold rounded-xl cursor-pointer hover:bg-slate-800 transition-all flex items-center justify-center gap-1.5 text-xs">
              {parsingCsv ? <Loader2 className="w-4 h-4 animate-spin text-emerald-400" /> : <Upload className="w-4 h-4 text-emerald-400" />}
              <span>{parsingCsv ? "Analyzing Statement..." : "Import Statement"}</span>
              <input type="file" className="hidden" accept=".csv" disabled={parsingCsv} onChange={handleSelectCsvFile} />
            </label>

            <button
              onClick={handleExportCsv}
              className="px-4 py-2.5 bg-slate-900 border border-white/10 hover:border-emerald-500/20 text-slate-300 font-bold rounded-xl hover:bg-slate-800 transition-all flex items-center justify-center gap-1.5 text-xs"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>

            <button
              onClick={handleExportPdf}
              className="px-4 py-2.5 bg-slate-900 border border-white/10 hover:border-emerald-500/20 text-slate-300 font-bold rounded-xl hover:bg-slate-800 transition-all flex items-center justify-center gap-1.5 text-xs"
            >
              <Download className="w-4 h-4" />
              Export PDF
            </button>

            <button
              onClick={openAddModal}
              className="px-5 py-2.5 bg-emerald-500 text-slate-950 font-bold rounded-xl hover:bg-emerald-400 transition-all flex items-center justify-center gap-2 shadow-lg hover:shadow-emerald-500/20 text-xs"
            >
              <Plus className="w-4 h-4" />
              Add Transaction
            </button>
          </div>
        </div>

        {/* Filter controls */}
        <div className="glass-panel p-5 rounded-2xl border border-white/5 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
          {/* Search bar */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-slate-500" />
            </div>
            <input
              type="text"
              placeholder="Search description or category..."
              className="w-full pl-9 pr-4 py-2 text-xs rounded-xl glass-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Type Filter */}
          <div>
            <select
              className="w-full px-3.5 py-2 text-xs rounded-xl glass-input"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="All">All Types</option>
              <option value="Income">Income</option>
              <option value="Expense">Expense</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <select
              className="w-full px-3.5 py-2 text-xs rounded-xl glass-input"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="All">All Categories</option>
              <option value="Needs Review">⚠️ Needs Review</option>
              <option disabled className="text-slate-500">-- Income Categories --</option>
              {INCOME_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              <option disabled className="text-slate-500">-- Expense Categories --</option>
              {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Sorting and items count */}
          <div className="flex justify-between items-center px-2">
            <button
              onClick={toggleSort}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-2 py-2 px-3 border border-white/5 hover:bg-white/5 rounded-xl transition-all"
            >
              <ArrowUpDown className="w-4 h-4" />
              <span>Sort: {sortOrder === "asc" ? "Oldest First" : "Newest First"}</span>
            </button>
            <span className="text-xs text-slate-500 font-mono">
              Total: {transactions.length} record(s)
            </span>
          </div>
        </div>

        {/* Transactions Table container */}
        <div className="glass-panel rounded-3xl border border-white/5 overflow-hidden shadow-2xl">
          {loading ? (
            <div className="h-96 flex flex-col justify-center items-center gap-4 bg-slate-900/10">
              <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
              <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Syncing Ledger...</span>
            </div>
          ) : paginatedTransactions.length === 0 ? (
            <div className="h-96 flex flex-col justify-center items-center gap-4 text-center p-6 bg-slate-900/10">
              <Calendar className="w-12 h-12 text-slate-600" />
              <h3 className="text-sm font-bold text-slate-400">No transactions recorded</h3>
              <p className="text-xs text-slate-500 max-w-sm">There are no records matching your current filter limits. Try clearing your search parameters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-900/50 text-slate-400 uppercase tracking-wider font-semibold border-b border-white/5 text-[10px]">
                    <th className="py-4.5 px-6">Date</th>
                    <th className="py-4.5 px-6">Category</th>
                    <th className="py-4.5 px-6">Type</th>
                    <th className="py-4.5 px-6">Amount</th>
                    <th className="py-4.5 px-6">Payment Method</th>
                    <th className="py-4.5 px-6">Description</th>
                    <th className="py-4.5 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-medium">
                  {paginatedTransactions.map((t) => (
                    <tr key={t.id} className="hover:bg-white/[0.02] transition-colors text-slate-200">
                      <td className="py-4 px-6">{t.transaction_date}</td>
                      <td className="py-4 px-6 text-slate-300 font-semibold">
                        <div className="flex items-center gap-1.5">
                          <span>{t.category}</span>
                          {t.category === "Needs Review" && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-0.5 font-bold">
                              <AlertCircle className="w-2.5 h-2.5" /> Review
                            </span>
                          )}
                          {t.category_confidence && t.category !== "Needs Review" && t.category_confidence >= 0.9 && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                              Auto
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          t.type === "Income"
                            ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                            : "bg-red-500/10 border border-red-500/20 text-red-400"
                        }`}>
                          {t.type}
                        </span>
                      </td>
                      <td className="py-4 px-6 font-semibold">
                        ₹{Number(t.amount).toLocaleString("en-IN")}
                      </td>
                      <td className="py-4 px-6 text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <span>{t.payment_method}</span>
                          {t.source === "bank_sync" && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 font-mono">
                              Bank Sync
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6 max-w-xs truncate text-slate-400" title={t.description}>
                        {t.description || "-"}
                      </td>
                      <td className="py-4 px-6 text-right flex justify-end gap-2.5">
                        <button
                          onClick={() => openEditModal(t)}
                          className="p-1.5 border border-white/5 hover:border-emerald-500/35 hover:bg-emerald-500/10 rounded-lg text-slate-400 hover:text-emerald-400 transition-all"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="p-1.5 border border-white/5 hover:border-red-500/35 hover:bg-red-500/10 rounded-lg text-slate-400 hover:text-red-400 transition-all"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="py-4 px-6 bg-slate-900/25 border-t border-white/5 flex items-center justify-between gap-4">
              <span className="text-xs text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  className="p-2 border border-white/5 rounded-xl disabled:opacity-30 hover:bg-white/5 transition-all"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  className="p-2 border border-white/5 rounded-xl disabled:opacity-30 hover:bg-white/5 transition-all"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add / Edit Transaction Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md px-4">
          <div className="w-full max-w-lg glass-panel rounded-3xl border border-white/10 shadow-2xl p-6 relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-5 right-5 p-1 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {editingId ? "Modify Transaction" : "Record Transaction"}
                </h3>
                <p className="text-slate-400 text-[10px] mt-0.5">Define transaction parameters and validate data</p>
              </div>
            </div>

            <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
              {/* Type toggle */}
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-xl border border-white/5">
                <button
                  type="button"
                  onClick={() => setValue("type", "Expense")}
                  className={`py-2 text-xs font-bold rounded-lg transition-all ${
                    transactionType === "Expense"
                      ? "bg-red-500/10 border border-red-500/25 text-red-400"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Expense
                </button>
                <button
                  type="button"
                  onClick={() => setValue("type", "Income")}
                  className={`py-2 text-xs font-bold rounded-lg transition-all ${
                    transactionType === "Income"
                      ? "bg-emerald-500/10 border border-emerald-500/25 text-emerald-400"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Income
                </button>
              </div>

              {/* Amount and Date */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
                    Amount (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    className={`w-full px-3.5 py-2.5 rounded-xl glass-input text-xs ${
                      errors.amount ? "border-red-500/40 focus:border-red-500" : ""
                    }`}
                    {...register("amount", { valueAsNumber: true })}
                  />
                  {errors.amount && (
                    <p className="text-red-400 text-[10px] mt-1 font-semibold">{errors.amount.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
                    Transaction Date
                  </label>
                  <input
                    type="date"
                    className={`w-full px-3.5 py-2.5 rounded-xl glass-input text-xs ${
                      errors.transaction_date ? "border-red-500/40 focus:border-red-500" : ""
                    }`}
                    {...register("transaction_date")}
                  />
                  {errors.transaction_date && (
                    <p className="text-red-400 text-[10px] mt-1 font-semibold">{errors.transaction_date.message}</p>
                  )}
                </div>
              </div>

              {/* Category and Payment Method */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
                    Category
                  </label>
                  <select
                    className={`w-full px-3.5 py-2.5 rounded-xl glass-input text-xs ${
                      errors.category ? "border-red-500/40 focus:border-red-500" : ""
                    }`}
                    {...register("category")}
                  >
                    <option value="">Select Category</option>
                    {(transactionType === "Income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                  {errors.category && (
                    <p className="text-red-400 text-[10px] mt-1 font-semibold">{errors.category.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
                    Payment Method
                  </label>
                  <select
                    className={`w-full px-3.5 py-2.5 rounded-xl glass-input text-xs ${
                      errors.payment_method ? "border-red-500/40 focus:border-red-500" : ""
                    }`}
                    {...register("payment_method")}
                  >
                    {PAYMENT_METHODS.map(pm => (
                      <option key={pm} value={pm}>{pm}</option>
                    ))}
                  </select>
                  {errors.payment_method && (
                    <p className="text-red-400 text-[10px] mt-1 font-semibold">{errors.payment_method.message}</p>
                  )}
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
                  Description
                </label>
                <input
                  type="text"
                  placeholder="Optional details (e.g. Weekly grocery bills)"
                  className="w-full px-3.5 py-2.5 rounded-xl glass-input text-xs"
                  {...register("description")}
                />
              </div>

              {/* Submit / Cancel buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2.5 border border-white/10 hover:bg-white/5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-65 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-all"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Recording...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" /> Save Record
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bank Statement Auto-Categorization & Import Review Modal */}
      {previewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 backdrop-blur-md px-4 py-6">
          <div className="w-full max-w-4xl max-h-[90vh] glass-panel rounded-3xl border border-white/10 shadow-2xl p-6 flex flex-col relative animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Bank Statement Auto-Categorization
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                      AI Rule Engine
                    </span>
                  </h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    Review suggested categories, confidence scores, and deduplication flags before committing to your ledger.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="p-1 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Metric Summaries & Bulk Actions */}
            <div className="py-4 flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 px-4 rounded-2xl my-4 border border-white/5">
              <div className="flex flex-wrap items-center gap-4 text-xs">
                <div>
                  <span className="text-slate-400">Parsed: </span>
                  <span className="font-bold text-white">{parsedItems.length}</span>
                </div>
                <div>
                  <span className="text-slate-400">Needs Review: </span>
                  <span className="font-bold text-amber-400">
                    {parsedItems.filter(it => it.category === "Needs Review" || (it.category_confidence && it.category_confidence < 0.7)).length}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Potential Duplicates: </span>
                  <span className="font-bold text-red-400">
                    {parsedItems.filter(it => it.is_duplicate).length}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Selected for Import: </span>
                  <span className="font-bold text-emerald-400">{selectedTempIds.size}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <button
                  type="button"
                  onClick={handleSelectAllNonDuplicates}
                  className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-lg text-slate-300 font-semibold border border-white/10 transition-all text-[11px]"
                >
                  Select Non-Duplicates
                </button>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-lg text-slate-300 font-semibold border border-white/10 transition-all text-[11px]"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={handleDeselectAll}
                  className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-slate-200 border border-white/10 transition-all text-[11px]"
                >
                  Deselect All
                </button>
              </div>
            </div>

            {/* Scrollable Transaction Preview Table */}
            <div className="flex-1 overflow-y-auto min-h-[220px] max-h-[420px] rounded-2xl border border-white/5 bg-slate-950/50">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-slate-900 z-10 border-b border-white/10 text-slate-400 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4 w-10 text-center">Import</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Description / Merchant</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4 min-w-[160px]">Suggested Category</th>
                    <th className="py-3 px-4 text-center">Confidence</th>
                    <th className="py-3 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {parsedItems.map((item) => {
                    const isSelected = selectedTempIds.has(item.temp_id);
                    const isHigh = item.category_confidence && item.category_confidence >= 0.85;
                    const isMedium = item.category_confidence && item.category_confidence >= 0.7 && item.category_confidence < 0.85;
                    const isReview = item.category === "Needs Review" || (item.category_confidence && item.category_confidence < 0.7);

                    return (
                      <tr
                        key={item.temp_id}
                        className={`hover:bg-white/[0.02] transition-colors ${
                          item.is_duplicate ? "bg-red-500/[0.03]" : ""
                        }`}
                      >
                        <td className="py-3 px-4 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleSelectTempId(item.temp_id)}
                            className="rounded border-white/20 text-emerald-500 focus:ring-emerald-400 bg-slate-900 cursor-pointer"
                          />
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap text-slate-300 font-mono text-[11px]">
                          {item.transaction_date}
                        </td>
                        <td className="py-3 px-4 max-w-xs truncate text-slate-200" title={item.description}>
                          {item.description || "—"}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              item.type === "Income"
                                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                                : "bg-red-500/10 border border-red-500/20 text-red-400"
                            }`}
                          >
                            {item.type}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-200 whitespace-nowrap">
                          ₹{Number(item.amount).toLocaleString("en-IN")}
                        </td>
                        <td className="py-3 px-4">
                          <select
                            value={item.category}
                            onChange={(e) => handleItemCategoryChange(item.temp_id, e.target.value)}
                            className={`w-full px-2.5 py-1 text-xs rounded-lg glass-input ${
                              isReview ? "border-amber-500/50 text-amber-300" : ""
                            }`}
                          >
                            <option disabled className="text-slate-500">-- Income Categories --</option>
                            {INCOME_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                            <option disabled className="text-slate-500">-- Expense Categories --</option>
                            {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                        </td>
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          {isHigh ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                              High ({Math.round((item.category_confidence || 0.95) * 100)}%)
                            </span>
                          ) : isMedium ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                              Med ({Math.round((item.category_confidence || 0.8) * 100)}%)
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center justify-center gap-1">
                              <AlertCircle className="w-2.5 h-2.5" /> Review
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          {item.is_duplicate ? (
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/30 cursor-help"
                              title={item.duplicate_reason || "Matching transaction date, amount, and description found in ledger"}
                            >
                              Duplicate
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/5 text-slate-400 border border-white/5">
                              New
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Modal Actions */}
            <div className="pt-4 mt-4 border-t border-white/5 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Ready to import <strong className="text-emerald-400 font-bold">{selectedTempIds.size}</strong> of {parsedItems.length} transactions
              </span>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setPreviewModalOpen(false)}
                  className="px-4 py-2 border border-white/10 hover:bg-white/5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white transition-all"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmImport}
                  disabled={confirmingImport || selectedTempIds.size === 0}
                  className="px-5 py-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-2 transition-all shadow-lg hover:shadow-emerald-500/20"
                >
                  {confirmingImport ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Importing...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Confirm & Import ({selectedTempIds.size})</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
