import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, getAvatarUrl } from "../services/api";
import {
  Activity, LogOut, Bell, Trash2, User as UserIcon, Menu, X
} from "lucide-react";

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(data || []);
    } catch (err) {
      console.error("Failed to load notifications:", err);
    }
  };

  const handleClearNotifications = async () => {
    try {
      await api.clearNotifications();
      setNotifications([]);
    } catch (err) {
      console.error("Failed to clear notifications:", err);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      loadNotifications();
    } catch (err) {
      console.error("Failed to read notification:", err);
    }
  };

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { path: "/dashboard", label: "Dashboard" },
    { path: "/transactions", label: "Transactions" },
    { path: "/analytics", label: "Analytics" },
    { path: "/forecast", label: "Forecast" },
    { path: "/budget", label: "Budgets" },
    { path: "/goals", label: "Goals" },
    { path: "/reports", label: "Reports" },
    { path: "/chatbot", label: "AI Chat" },
    { path: "/settings", label: "Settings" }
  ];

  const unreadCount = notifications.filter((n: any) => !n.is_read).length;

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/5 py-4 px-6 md:px-12 flex justify-between items-center bg-slate-950/80 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center glow-emerald">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-emerald-400 bg-clip-text text-transparent">
            FinRisk AI
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden xl:flex items-center gap-4 text-xs font-semibold text-slate-400 ml-8">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`transition-colors py-1.5 px-3 rounded-lg hover:text-emerald-400 ${
                location.pathname === link.path 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/10" 
                  : "hover:bg-white/5"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {user?.is_admin && (
            <Link
              to="/admin"
              className={`transition-colors py-1.5 px-3 rounded-lg text-red-400 hover:text-red-300 ${
                location.pathname === "/admin" 
                  ? "bg-red-500/10 border border-red-500/10" 
                  : "hover:bg-white/5"
              }`}
            >
              Admin
            </Link>
          )}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-emerald-400 hover:bg-white/5 transition-all relative"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[8px] font-bold text-white flex items-center justify-center animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-3 w-80 md:w-96 glass-panel border border-white/10 rounded-2xl shadow-2xl p-4 z-50 text-left max-h-96 overflow-y-auto bg-slate-950/95">
              <div className="flex justify-between items-center pb-2 border-b border-white/5 mb-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300">System Notifications</span>
                {notifications.length > 0 && (
                  <button
                    onClick={handleClearNotifications}
                    className="text-[9px] font-bold uppercase tracking-wider text-red-400 hover:text-red-300 flex items-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" /> Clear All
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {notifications.length === 0 ? (
                  <p className="text-[10px] text-slate-500 text-center py-4">No active notifications</p>
                ) : (
                  notifications.map((n: any) => (
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
          className="hidden sm:flex p-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-red-400 hover:bg-white/5 transition-all items-center gap-2"
          title="Sign Out"
        >
          <LogOut className="w-5 h-5" />
          <span className="text-xs font-semibold">Sign Out</span>
        </button>

        {/* Mobile Navigation Trigger */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="xl:hidden p-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-emerald-400 hover:bg-white/5 transition-all"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer menu */}
      {mobileMenuOpen && (
        <div className="absolute top-16 left-0 w-full glass-panel bg-slate-950/95 border-b border-white/10 p-6 flex flex-col gap-3 xl:hidden z-30">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => setMobileMenuOpen(false)}
              className={`py-2.5 px-4 rounded-xl font-bold text-sm ${
                location.pathname === link.path 
                  ? "bg-emerald-500/10 text-emerald-400" 
                  : "text-slate-300 hover:bg-white/5"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {user?.is_admin && (
            <Link
              to="/admin"
              onClick={() => setMobileMenuOpen(false)}
              className={`py-2.5 px-4 rounded-xl font-bold text-sm text-red-400 ${
                location.pathname === "/admin" 
                  ? "bg-red-500/10 text-red-400" 
                  : "hover:bg-white/5"
              }`}
            >
              Admin Dashboard
            </Link>
          )}
          <button
            onClick={logout}
            className="flex items-center gap-2 py-2.5 px-4 rounded-xl font-bold text-sm text-red-400 hover:bg-red-500/10 transition-all border border-red-500/20"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      )}
    </header>
  );
};
