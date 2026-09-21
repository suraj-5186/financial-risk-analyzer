import { request, API_BASE_URL } from "./api";

export interface Transaction {
  id: string;
  user_id: string;
  type: "Income" | "Expense";
  category: string;
  category_confidence?: number;
  auto_category?: string;
  is_reviewed?: boolean;
  amount: number;
  description?: string;
  transaction_date: string;
  payment_method: string;
  external_id?: string;
  bank_account_id?: string;
  source?: string;
  created_at: string;
  updated_at: string;
}

export interface ParseCsvItem {
  temp_id: string;
  transaction_date: string;
  type: "Income" | "Expense";
  amount: number;
  description: string;
  category: string;
  suggested_category: string;
  category_confidence: number;
  explanation: string;
  is_reviewed: boolean;
  payment_method: string;
  is_duplicate: boolean;
  duplicate_reason?: string | null;
}

export interface ParseCsvResponse {
  items: ParseCsvItem[];
  total_parsed: number;
  duplicates_count: number;
  needs_review_count: number;
}

export const transactionsApi = {
  list: (params?: { month?: string; category?: string; type?: string }): Promise<Transaction[]> => {
    const queryParts: string[] = [];
    if (params?.month) queryParts.push(`month=${encodeURIComponent(params.month)}`);
    if (params?.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
    if (params?.type) queryParts.push(`type=${encodeURIComponent(params.type)}`);
    
    const queryString = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
    return request(`/api/transactions${queryString}`, { method: "GET" });
  },

  search: (q: string): Promise<Transaction[]> => {
    return request(`/api/transactions/search?q=${encodeURIComponent(q)}`, { method: "GET" });
  },

  get: (id: string): Promise<Transaction> => {
    return request(`/api/transactions/${id}`, { method: "GET" });
  },

  create: (data: {
    type: "Income" | "Expense";
    category: string;
    amount: number;
    description?: string;
    transaction_date: string;
    payment_method: string;
    category_confidence?: number;
    is_reviewed?: boolean;
  }): Promise<Transaction> => {
    return request("/api/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update: (id: string, data: {
    type?: "Income" | "Expense";
    category?: string;
    amount?: number;
    description?: string;
    transaction_date?: string;
    payment_method?: string;
    category_confidence?: number;
    is_reviewed?: boolean;
  }): Promise<Transaction> => {
    return request(`/api/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete: (id: string): Promise<{ status: string; message: string }> => {
    return request(`/api/transactions/${id}`, {
      method: "DELETE",
    });
  },

  parseCsv: async (file: File): Promise<ParseCsvResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/api/transactions/parse-csv`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      },
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Failed to parse bank statement CSV");
    }
    return data;
  },

  confirmImport: (transactions: any[], skipDuplicates: boolean = true) => {
    return request("/api/transactions/confirm-import", {
      method: "POST",
      body: JSON.stringify({
        transactions,
        skip_duplicates: skipDuplicates
      })
    });
  },

  autoCategorize: (description: string, type: "Income" | "Expense" = "Expense", amount: number = 0.0) => {
    return request("/api/transactions/auto-categorize", {
      method: "POST",
      body: JSON.stringify({
        description,
        type,
        amount
      })
    });
  },

  importCsv: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/api/transactions/import-csv`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      },
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Import failed");
    }
    return data;
  },
};
