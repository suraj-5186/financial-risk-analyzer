import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, getAvatarUrl } from "../services/api";
import { ArrowLeft, User as UserIcon, Camera, Loader2, Save, Key, Trash2 } from "lucide-react";

export const SettingsPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [currency, setCurrency] = useState(user?.currency || "INR");
  const [theme, setTheme] = useState(user?.theme || "dark");
  const [budgetExceeded, setBudgetExceeded] = useState(user?.notify_budget_exceeded ?? true);
  const [savingsLow, setSavingsLow] = useState(user?.notify_savings_low ?? true);
  const [highRisk, setHighRisk] = useState(user?.notify_high_risk ?? true);
  const [anomalies, setAnomalies] = useState(user?.notify_anomalies ?? true);

  // Financial Profile Inputs
  const [income, setIncome] = useState(50000); // We will update this via summary / settings load
  const [globalBudget, setGlobalBudget] = useState(50000);
  const [savingsGoalTitle, setSavingsGoalTitle] = useState("Emergency Fund");
  const [savingsGoalTarget, setSavingsGoalTarget] = useState(100000);
  const [savingsGoalCurrent, setSavingsGoalCurrent] = useState(30000);

  // Loading states
  const [updatingProfile, setUpdatingProfile] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [deletingPhoto, setDeletingPhoto] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // Password fields
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Pull initial budget/goal settings on mount
  React.useEffect(() => {
    const loadProfile = async () => {
      try {
        const summary = await api.getSummary();
        setIncome(summary.profile.monthly_income);
        setGlobalBudget(summary.profile.monthly_budget);
        setSavingsGoalTitle(summary.profile.savings_goal_title);
        setSavingsGoalTarget(summary.profile.savings_goal_target);
        setSavingsGoalCurrent(summary.profile.savings_goal_current);
      } catch (err) {
        console.error("Failed to load settings profile:", err);
      }
    };
    loadProfile();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdatingProfile(true);
    setMessage(null);
    try {
      await api.updateProfile({
        full_name: fullName,
        currency,
        theme,
        notify_budget_exceeded: budgetExceeded,
        notify_savings_low: savingsLow,
        notify_high_risk: highRisk,
        notify_anomalies: anomalies,
        monthly_income: income,
        monthly_budget: globalBudget,
        savings_goal_title: savingsGoalTitle,
        savings_goal_target: savingsGoalTarget,
        savings_goal_current: savingsGoalCurrent,
      });
      await refreshUser();
      
      // Update HTML theme tag dynamically
      if (theme === "light") {
        document.documentElement.classList.remove("dark");
      } else {
        document.documentElement.classList.add("dark");
      }
      
      setMessage({ text: "Profile settings updated successfully!", type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to update profile", type: "error" });
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    setMessage(null);
    try {
      await api.uploadProfilePhoto(file);
      await refreshUser();
      setMessage({ text: "Profile picture uploaded successfully!", type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message || "Photo upload failed", type: "error" });
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleDeletePhoto = async () => {
    if (!window.confirm("Are you sure you want to remove your profile picture?")) return;
    setDeletingPhoto(true);
    setMessage(null);
    try {
      await api.deleteProfilePhoto();
      await refreshUser();
      setMessage({ text: "Profile picture removed successfully!", type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to remove photo", type: "error" });
    } finally {
      setDeletingPhoto(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({ text: "New passwords do not match", type: "error" });
      return;
    }
    setChangingPassword(true);
    setMessage(null);
    try {
      await api.changePassword({ old_password: oldPassword, new_password: newPassword });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage({ text: "Password changed successfully!", type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to change password", type: "error" });
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans selection:bg-emerald-500/30">
      {/* Background gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-[40%] -right-[60%] w-[120%] h-[120%] rounded-full bg-emerald-950/10 blur-[150px] animate-pulse" />
        <div className="absolute -bottom-[40%] -left-[60%] w-[120%] h-[120%] rounded-full bg-blue-950/10 blur-[150px]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-8">
        {/* Navigation */}
        <div className="flex items-center justify-between mb-8">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-400 hover:text-white transition-colors duration-200"
          >
            <ArrowLeft className="w-4 h-4" /> BACK TO DASHBOARD
          </Link>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
            Settings & Profile
          </h1>
        </div>

        {message && (
          <div
            className={`p-4 rounded-2xl mb-6 border text-xs font-semibold ${
              message.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border-red-500/20 text-red-400"
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Column 1: Profile photo details */}
          <div className="glass-panel p-6 rounded-3xl border border-white/5 flex flex-col items-center text-center h-fit">
            <div className="relative group mb-4">
              <div className="w-24 h-24 rounded-full bg-slate-800 border-2 border-emerald-500/30 overflow-hidden flex items-center justify-center">
                {user?.profile_photo_url ? (
                  <img
                    src={getAvatarUrl(user.profile_photo_url)}
                    alt="Profile"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "";
                    }}
                  />
                ) : (
                  <UserIcon className="w-10 h-10 text-slate-500" />
                )}
              </div>
              <label className="absolute bottom-0 right-0 p-2 bg-emerald-500 hover:bg-emerald-600 rounded-full cursor-pointer transition-colors duration-200 shadow-lg">
                {uploadingPhoto ? (
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                ) : (
                  <Camera className="w-4 h-4 text-slate-950" />
                )}
                <input type="file" className="hidden" accept="image/jpeg,image/png,image/webp" onChange={handlePhotoUpload} disabled={uploadingPhoto || deletingPhoto} />
              </label>
            </div>
            {user?.profile_photo_url && (
              <button
                type="button"
                onClick={handleDeletePhoto}
                disabled={deletingPhoto || uploadingPhoto}
                className="mb-3 flex items-center gap-1.5 px-3 py-1 rounded-xl text-[10px] font-semibold text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/20 transition-all disabled:opacity-50"
                title="Remove profile photo"
              >
                {deletingPhoto ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Trash2 className="w-3 h-3" />
                )}
                Remove Photo
              </button>
            )}
            <h2 className="text-sm font-bold">{user?.full_name}</h2>
            <p className="text-[10px] text-slate-400 mb-2">{user?.email}</p>
            {user?.is_admin && (
              <span className="px-2 py-0.5 rounded-full text-[8px] font-bold tracking-wider uppercase bg-red-500/10 border border-red-500/20 text-red-400">
                Administrator
              </span>
            )}
          </div>

          {/* Column 2 & 3: Settings inputs */}
          <div className="md:col-span-2 space-y-6">
            <form onSubmit={handleUpdateProfile} className="glass-panel p-6 rounded-3xl border border-white/5 space-y-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 pb-2 border-b border-white/5">
                General Preferences
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Currency Symbol
                  </label>
                  <select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Visual Mode
                  </label>
                  <select
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  >
                    <option value="dark">Dark Theme</option>
                    <option value="light">Light Theme</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Monthly Income
                  </label>
                  <input
                    type="number"
                    value={income}
                    onChange={(e) => setIncome(Number(e.target.value))}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
              </div>

              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-4 pb-2 border-b border-white/5">
                Financial Planning Limits
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Global Monthly Budget
                  </label>
                  <input
                    type="number"
                    value={globalBudget}
                    onChange={(e) => setGlobalBudget(Number(e.target.value))}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Savings Goal Target
                  </label>
                  <input
                    type="number"
                    value={savingsGoalTarget}
                    onChange={(e) => setSavingsGoalTarget(Number(e.target.value))}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Savings Goal Name
                  </label>
                  <input
                    type="text"
                    value={savingsGoalTitle}
                    onChange={(e) => setSavingsGoalTitle(e.target.value)}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Goal Capital Collected
                  </label>
                  <input
                    type="number"
                    value={savingsGoalCurrent}
                    onChange={(e) => setSavingsGoalCurrent(Number(e.target.value))}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
              </div>

              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 pt-4 pb-2 border-b border-white/5">
                Alert Rules Notification Settings
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={budgetExceeded}
                    onChange={(e) => setBudgetExceeded(e.target.checked)}
                    className="rounded border-white/10 bg-slate-900 text-emerald-500 focus:ring-emerald-500/30 focus:ring-offset-slate-950"
                  />
                  <span className="text-[10px] font-medium text-slate-300">Notify budget overspends</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={savingsLow}
                    onChange={(e) => setSavingsLow(e.target.checked)}
                    className="rounded border-white/10 bg-slate-900 text-emerald-500 focus:ring-emerald-500/30"
                  />
                  <span className="text-[10px] font-medium text-slate-300">Notify low savings rate</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={highRisk}
                    onChange={(e) => setHighRisk(e.target.checked)}
                    className="rounded border-white/10 bg-slate-900 text-emerald-500 focus:ring-emerald-500/30"
                  />
                  <span className="text-[10px] font-medium text-slate-300">Notify High risk flags</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={anomalies}
                    onChange={(e) => setAnomalies(e.target.checked)}
                    className="rounded border-white/10 bg-slate-900 text-emerald-500 focus:ring-emerald-500/30"
                  />
                  <span className="text-[10px] font-medium text-slate-300">Notify unusual anomalies</span>
                </label>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={updatingProfile}
                  className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-slate-950 font-bold px-5 py-2.5 rounded-xl text-xs transition-colors duration-200"
                >
                  {updatingProfile ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving Changes...
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5" /> Save Profile Preferences
                    </>
                  )}
                </button>
              </div>
            </form>

            <form onSubmit={handleChangePassword} className="glass-panel p-6 rounded-3xl border border-white/5 space-y-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 pb-2 border-b border-white/5">
                Update Account Password
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="w-full bg-slate-900/60 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-colors"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={changingPassword}
                  className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 text-white font-bold px-5 py-2.5 rounded-xl text-xs transition-colors duration-200"
                >
                  {changingPassword ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Changing...
                    </>
                  ) : (
                    <>
                      <Key className="w-3.5 h-3.5" /> Update Password
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
