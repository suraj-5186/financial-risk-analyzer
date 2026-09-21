import { request } from "./api";

export interface BankAccount {
  id: string;
  connection_id: string;
  external_account_id: string;
  account_name: string;
  account_type: string;
  account_subtype?: string;
  mask?: string;
  currency: string;
  current_balance?: number;
  available_balance?: number;
  is_active: boolean;
  created_at: string;
}

export interface BankConnection {
  id: string;
  provider: string;
  institution_id: string;
  institution_name: string;
  status: "connected" | "syncing" | "error" | "disconnected";
  last_sync_at?: string;
  sync_status: "idle" | "syncing" | "success" | "failed";
  sync_error_message?: string;
  created_at: string;
  accounts: BankAccount[];
}

export interface BankConnectRequest {
  provider?: string;
  institution_id?: string;
  auth_code?: string;
  state?: string;
}

export interface BankSyncResult {
  connection_id: string;
  status: string;
  imported_count: number;
  duplicates_skipped: number;
  accounts_synced: number;
  synced_at: string;
  message: string;
}

export interface ProviderInstitution {
  institution_id: string;
  institution_name: string;
  logo_url?: string;
  supported_features: string[];
  is_mock?: boolean;
}

export interface ProviderStatus {
  provider: string;
  is_mock: boolean;
  is_configured: boolean;
  supported_institutions: ProviderInstitution[];
}

export const bankSyncApi = {
  getConnections: (): Promise<BankConnection[]> => {
    return request("/api/bank-connections");
  },

  getProviderStatus: (): Promise<ProviderStatus> => {
    return request("/api/bank-connections/providers");
  },

  connectBank: (data: BankConnectRequest): Promise<BankConnection> => {
    return request("/api/bank-connections/connect", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getAccounts: (connectionId: string): Promise<BankAccount[]> => {
    return request(`/api/bank-connections/${connectionId}/accounts`);
  },

  triggerSync: (connectionId: string): Promise<BankSyncResult> => {
    return request(`/api/bank-connections/${connectionId}/sync`, {
      method: "POST",
    });
  },

  disconnectBank: (connectionId: string): Promise<void> => {
    return request(`/api/bank-connections/${connectionId}`, {
      method: "DELETE",
    });
  },
};
