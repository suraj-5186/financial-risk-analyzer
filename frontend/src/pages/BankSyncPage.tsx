import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Building2,
  RefreshCw,
  Plus,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Wallet,
  CreditCard,
  Lock,
  ExternalLink,
  Clock,
  ArrowLeft,
  Check,
  Trash2,
  Info,
} from "lucide-react";
import { bankSyncApi } from "../services/bankSync";
import type {
  BankConnection,
  ProviderStatus,
  ProviderInstitution,
} from "../services/bankSync";

export const BankSyncPage: React.FC = () => {
  const [connections, setConnections] = useState<BankConnection[]>([]);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<boolean>(false);
  const [showConnectModal, setShowConnectModal] = useState<boolean>(false);
  const [selectedInstId, setSelectedInstId] = useState<string>("");
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const showToast = (text: string, type: "success" | "error" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [conns, status] = await Promise.all([
        bankSyncApi.getConnections(),
        bankSyncApi.getProviderStatus(),
      ]);
      setConnections(conns);
      setProviderStatus(status);
      if (status.supported_institutions.length > 0) {
        setSelectedInstId(status.supported_institutions[0].institution_id);
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to load bank sync data", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    try {
      setConnecting(true);
      const newConn = await bankSyncApi.connectBank({
        provider: providerStatus?.provider || "mock",
        institution_id: selectedInstId,
      });
      setShowConnectModal(false);
      showToast(`Successfully linked ${newConn.institution_name}! Initial transactions synced.`);
      await loadData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to link bank connection", "error");
    } finally {
      setConnecting(false);
    }
  };

  const handleSync = async (connId: string) => {
    try {
      setSyncingId(connId);
      const result = await bankSyncApi.triggerSync(connId);
      showToast(result.message);
      await loadData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Sync failed", "error");
    } finally {
      setSyncingId(null);
    }
  };

  const handleDisconnect = async (connId: string) => {
    try {
      await bankSyncApi.disconnectBank(connId);
      setDisconnectingId(null);
      showToast("Bank connection disconnected. Ledger transactions preserved.");
      await loadData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to disconnect bank", "error");
    }
  };

  // Metrics
  const totalAccounts = connections.reduce((acc, c) => acc + (c.accounts?.length || 0), 0);
  const lastSyncDate = connections
    .map((c) => c.last_sync_at)
    .filter(Boolean)
    .sort()
    .reverse()[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border backdrop-blur-md transition-all ${
            toastMessage.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/50 text-rose-200"
          }`}
        >
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span className="text-sm font-medium">{toastMessage.text}</span>
        </div>
      )}

      {/* Top Header */}
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Link
                to="/transactions"
                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Ledger
              </Link>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Building2 className="w-8 h-8 text-indigo-400" />
              Open Banking &amp; Bank Sync
            </h1>
            <p className="text-sm text-slate-400">
              Securely connect financial institutions to synchronize accounts, balances, and real-time transaction feeds.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowConnectModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all hover:scale-[1.02]"
            >
              <Plus className="w-4 h-4" />
              Connect Bank
            </button>
          </div>
        </div>

        {/* Security & Sandbox Disclosure Banner */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 md:p-5 backdrop-blur-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl shrink-0 text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white text-sm">Read-Only Financial Data Protocol</span>
                {providerStatus?.is_mock && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 border border-amber-500/20 text-amber-300">
                    Sandbox / Demo Mode Active
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                FinRisk AI never stores or handles your online banking login credentials, passwords, or PINs.
                All communication utilizes encrypted token-based read-only consent.
                {providerStatus?.is_mock &&
                  " In sandbox mode, transactions and account balances are safely generated locally without contacting live banks."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800 shrink-0">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tokens 256-Bit Encrypted</span>
          </div>
        </div>

        {/* Summary Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Connected Banks</span>
              <Building2 className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{connections.length}</div>
            <div className="text-xs text-slate-500 mt-1">Authorized institutions</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Linked Accounts</span>
              <CreditCard className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{totalAccounts}</div>
            <div className="text-xs text-slate-500 mt-1">Checking &amp; savings feeds</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Last Synced</span>
              <Clock className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-sm font-semibold text-white mt-2 truncate">
              {lastSyncDate ? new Date(lastSyncDate).toLocaleString() : "Never"}
            </div>
            <div className="text-xs text-slate-500 mt-1">Automated ledger refresh</div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Provider Engine</span>
              <Wallet className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-sm font-semibold text-white mt-2 capitalize flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              {providerStatus?.provider || "mock"} Provider
            </div>
            <div className="text-xs text-slate-500 mt-1">Deduplicating sync engine</div>
          </div>
        </div>

        {/* Connections List */}
        {loading ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center">
            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading authorized bank links...</p>
          </div>
        ) : connections.length === 0 ? (
          <div className="bg-slate-900/30 border border-dashed border-slate-800 rounded-3xl p-12 text-center space-y-4">
            <div className="w-14 h-14 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center mx-auto text-indigo-400">
              <Building2 className="w-7 h-7" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h3 className="text-lg font-semibold text-white">No Bank Connections Yet</h3>
              <p className="text-xs text-slate-400">
                Link your bank account to automatically import transactions, calculate cash flow risks, and track recurring bills.
              </p>
            </div>
            <button
              onClick={() => setShowConnectModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/25"
            >
              <Plus className="w-4 h-4" />
              Connect Sandbox Bank
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((conn) => {
              const isSyncing = syncingId === conn.id;
              return (
                <div
                  key={conn.id}
                  className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 md:p-6 backdrop-blur-sm transition-all hover:border-slate-700/80 space-y-5"
                >
                  {/* Connection Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3.5">
                      <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-indigo-400 shrink-0">
                        <Building2 className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <h3 className="font-semibold text-white text-base">{conn.institution_name}</h3>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                              conn.status === "connected"
                                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                                : conn.status === "syncing"
                                ? "bg-blue-500/10 border-blue-500/20 text-blue-400"
                                : "bg-rose-500/10 border-rose-500/20 text-rose-400"
                            }`}
                          >
                            {conn.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Provider: <span className="text-slate-300 font-mono">{conn.provider}</span> • Linked on{" "}
                          {new Date(conn.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSync(conn.id)}
                        disabled={isSyncing}
                        className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-medium transition-all disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin text-indigo-400" : ""}`} />
                        {isSyncing ? "Syncing..." : "Sync Now"}
                      </button>
                      <button
                        onClick={() => setDisconnectingId(conn.id)}
                        className="p-2 rounded-xl bg-slate-800/60 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-transparent hover:border-rose-500/30 transition-all"
                        title="Disconnect Institution"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Linked Accounts List */}
                  <div className="space-y-2 pt-2 border-t border-slate-800/60">
                    <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Linked Accounts ({conn.accounts?.length || 0})
                    </span>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {conn.accounts && conn.accounts.length > 0 ? (
                        conn.accounts.map((acc) => (
                          <div
                            key={acc.id}
                            className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3.5 flex items-center justify-between"
                          >
                            <div className="flex items-center gap-3">
                              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                                {acc.account_type === "credit" ? (
                                  <CreditCard className="w-4 h-4" />
                                ) : (
                                  <Wallet className="w-4 h-4" />
                                )}
                              </div>
                              <div>
                                <div className="text-sm font-medium text-white">{acc.account_name}</div>
                                <div className="text-xs text-slate-400 flex items-center gap-1.5">
                                  <span>•••• {acc.mask || "0000"}</span>
                                  <span>•</span>
                                  <span className="capitalize">{acc.account_subtype || acc.account_type}</span>
                                </div>
                              </div>
                            </div>

                            <div className="text-right">
                              <div className="text-sm font-semibold text-white">
                                ₹{acc.current_balance?.toLocaleString("en-IN", { minimumFractionDigits: 2 }) ?? "—"}
                              </div>
                              <div className="text-[11px] text-slate-500">Current Balance</div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-slate-500 italic py-2">
                          No accounts discovered under this connection.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Footer sync info */}
                  {conn.last_sync_at && (
                    <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span>
                        Last synchronized on {new Date(conn.last_sync_at).toLocaleDateString()} at{" "}
                        {new Date(conn.last_sync_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}.
                        Idempotency filters active.
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Connect Bank Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                  <Building2 className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Connect Financial Institution</h3>
                  <p className="text-xs text-slate-400">Select a bank to link your transaction feed</p>
                </div>
              </div>
              <button
                onClick={() => setShowConnectModal(false)}
                className="text-slate-400 hover:text-white text-sm p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {/* Institution Selector */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-slate-300">Supported Institutions</label>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {providerStatus?.supported_institutions.map((inst: ProviderInstitution) => {
                  const isSelected = selectedInstId === inst.institution_id;
                  return (
                    <div
                      key={inst.institution_id}
                      onClick={() => setSelectedInstId(inst.institution_id)}
                      className={`flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? "bg-indigo-500/10 border-indigo-500/50 text-white"
                          : "bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-indigo-400 font-bold text-xs">
                          {inst.institution_name.charAt(0)}
                        </div>
                        <div>
                          <div className="text-sm font-medium">{inst.institution_name}</div>
                          <div className="text-[11px] text-slate-400">
                            {inst.is_mock ? "Sandbox Simulation" : "Live Provider"}
                          </div>
                        </div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Consent Notice */}
            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 text-xs text-slate-400 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <span>
                By connecting, you grant FinRisk AI read-only access to view account balances and historical transactions.
                No credentials or login passwords are ever requested or stored.
              </span>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConnectModal(false)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConnect}
                disabled={connecting || !selectedInstId}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all disabled:opacity-50 shadow-lg shadow-indigo-600/25"
              >
                {connecting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" /> Connecting...
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" /> Authorize &amp; Connect
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Disconnect Confirmation Modal */}
      {disconnectingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Disconnect Bank Connection?</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              This will revoke data synchronization consent and remove the linked account records.
              All existing ledger entries already imported into FinRisk AI will be safely preserved.
            </p>
            <div className="flex items-center justify-end gap-3 pt-3">
              <button
                onClick={() => setDisconnectingId(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDisconnect(disconnectingId)}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium shadow-lg shadow-rose-600/25"
              >
                Disconnect &amp; Revoke
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
