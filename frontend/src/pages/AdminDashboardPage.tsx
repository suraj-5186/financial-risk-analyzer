import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { ArrowLeft, Users, ShieldAlert, Cpu, Activity, LayoutGrid, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from "recharts";

const COLORS = ["#10b981", "#f59e0b", "#ef4444"];

export const AdminDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Redirect if not admin
    if (user && !user.is_admin) {
      navigate("/dashboard");
      return;
    }

    const loadStats = async () => {
      try {
        const adminData = await api.getAdminStats();
        setStats(adminData);
      } catch (err: any) {
        console.error("Failed to load admin stats:", err);
        setError(err.message || "Unauthorized access.");
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white">
        <Loader2 className="w-10 h-10 animate-spin text-emerald-500 mb-4" />
        <p className="text-xs font-semibold text-slate-400 tracking-widest uppercase">Loading Admin Console...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white p-4">
        <div className="glass-panel p-8 rounded-3xl border border-red-500/10 text-center max-w-sm">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-sm font-bold mb-2">Access Forbidden</h2>
          <p className="text-xs text-slate-400 mb-6">{error}</p>
          <Link
            to="/dashboard"
            className="inline-block bg-slate-900 hover:bg-slate-800 border border-white/5 text-xs font-bold px-5 py-2.5 rounded-xl transition-colors"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Prep risk chart data
  const riskData = [
    { name: "Low Risk", value: stats?.risk_level_distribution?.Low || 0 },
    { name: "Medium Risk", value: stats?.risk_level_distribution?.Medium || 0 },
    { name: "High Risk", value: stats?.risk_level_distribution?.High || 0 }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans selection:bg-emerald-500/30">
      {/* Background gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-[40%] -right-[60%] w-[120%] h-[120%] rounded-full bg-red-950/5 blur-[150px] animate-pulse" />
        <div className="absolute -bottom-[40%] -left-[60%] w-[120%] h-[120%] rounded-full bg-emerald-950/10 blur-[150px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {/* Navigation */}
        <div className="flex items-center justify-between mb-8">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-400 hover:text-white transition-colors duration-200"
          >
            <ArrowLeft className="w-4 h-4" /> LEAVE ADMIN CONSOLE
          </Link>
          <h1 className="text-xl font-bold bg-gradient-to-r from-red-400 to-amber-200 bg-clip-text text-transparent flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-400" /> Admin Command Center
          </h1>
        </div>

        {/* Analytics cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Card 1: Users */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/10">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Total System Users</p>
              <h3 className="text-lg font-black mt-0.5">{stats?.total_users}</h3>
            </div>
          </div>

          {/* Card 2: Transactions */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/10">
              <LayoutGrid className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Total Transactions</p>
              <h3 className="text-lg font-black mt-0.5">{stats?.total_transactions}</h3>
            </div>
          </div>

          {/* Card 3: Avg Health */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/10">
              <Activity className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Average Health Score</p>
              <h3 className="text-lg font-black mt-0.5">{stats?.average_health_score}/100</h3>
            </div>
          </div>

          {/* Card 4: System State */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center border border-red-500/10">
              <Cpu className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Database Engine</p>
              <h3 className="text-lg font-black mt-0.5">{stats?.system?.database_type}</h3>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Pie: Risk Demographics */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">User Risk Profiles</h3>
            <div className="flex-1 min-h-0 relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {riskData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 mt-2 text-[9px] text-slate-400">
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span>Low Risk: {stats?.risk_level_distribution?.Low || 0}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span>Medium Risk: {stats?.risk_level_distribution?.Medium || 0}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span>High Risk: {stats?.risk_level_distribution?.High || 0}</span>
              </div>
            </div>
          </div>

          {/* Bar: Top Categories */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 h-80 flex flex-col">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Common User Categories</h3>
            <div className="flex-1 min-h-0">
              {stats?.top_categories?.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">No category statistics</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats?.top_categories}>
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px" }}
                    />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Server metrics logs */}
        <div className="glass-panel p-6 rounded-3xl border border-white/5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">System Operational Diagnostics</h3>
          <div className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <span className="text-slate-400 font-medium">Gateway Health State</span>
              <span className="px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 uppercase">
                Active & Running
              </span>
            </div>
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <span className="text-slate-400 font-medium">Active SQLAlchemy Bind Connections</span>
              <span className="font-semibold text-slate-200">{stats?.system?.active_connections}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">API Base URL Connection</span>
              <span className="font-semibold text-slate-200">http://127.0.0.1:8000</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
