export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export const getAvatarUrl = (url?: string | null): string => {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${API_BASE_URL}${url}`;
};

// Helper to get headers with Auth
const getHeaders = (withAuth = true) => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (withAuth) {
    const token = localStorage.getItem("access_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
};

// Generic fetch wrapper with auto refresh
export async function request(url: string, options: RequestInit = {}, withAuth = true): Promise<any> {
  const fullUrl = `${API_BASE_URL}${url}`;
  const headers = { ...getHeaders(withAuth), ...(options.headers || {}) };
  
  let response = await fetch(fullUrl, { ...options, headers });
  
  // If unauthorized, attempt token refresh
  if (response.status === 401 && withAuth) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/api/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        
        if (refreshResponse.ok) {
          const tokenData = await refreshResponse.json();
          localStorage.setItem("access_token", tokenData.access_token);
          localStorage.setItem("refresh_token", tokenData.refresh_token);
          
          // Retry initial request with new token
          const retriedHeaders = {
            ...getHeaders(true),
            ...(options.headers || {}),
          };
          response = await fetch(fullUrl, { ...options, headers: retriedHeaders });
        } else {
          // Refresh failed - clean up
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      } catch (err) {
        console.error("Token refresh failed:", err);
      }
    }
  }
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }
  
  return response.status === 204 ? null : response.json();
}

export const api = {
  // Auth APIs
  register: (data: any) => request("/api/register", {
    method: "POST",
    body: JSON.stringify(data),
  }, false),
  
  login: (data: any) => request("/api/login", {
    method: "POST",
    body: JSON.stringify(data),
  }, false),
  
  getMe: () => request("/api/me", { method: "GET" }),
  
  logout: () => request("/api/logout", { method: "POST" }),
  
  forgotPassword: (data: { email: string }) => request("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(data),
  }, false),

  verifyResetToken: (token: string) => request(`/api/auth/verify-reset-token?token=${encodeURIComponent(token)}`, {
    method: "GET",
  }, false),

  resetPassword: (data: { token: string; new_password: string }) => request("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(data),
  }, false),
  
  // Financial profile/summary APIs
  getSummary: () => request("/api/financials/summary", { method: "GET" }),
  getSafeToSpend: () => request("/api/financials/safe-to-spend", { method: "GET" }),
  getGoalProtection: () => request("/api/financials/goal-protection", { method: "GET" }),
  
  updateProfile: (data: any) => request("/api/users/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }),

  changePassword: (data: any) => request("/api/users/change-password", {
    method: "PUT",
    body: JSON.stringify(data),
  }),

  uploadProfilePhoto: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/api/users/profile-photo`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      },
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Failed to upload profile picture");
    }
    return data;
  },

  deleteProfilePhoto: () => request("/api/users/profile-photo", { method: "DELETE" }),


  // Notifications
  getNotifications: () => request("/api/notifications", { method: "GET" }),
  markNotificationRead: (id: number) => request(`/api/notifications/${id}/read`, { method: "PUT" }),
  clearNotifications: () => request("/api/notifications/clear", { method: "POST" }),

  // Admin
  getAdminStats: () => request("/api/admin/dashboard", { method: "GET" }),
  
  // Budgets
  getBudgets: (month?: string) => request(`/api/budgets${month ? `?month=${encodeURIComponent(month)}` : ""}`, { method: "GET" }),
  
  createBudget: (data: any) => request("/api/budgets", {
    method: "POST",
    body: JSON.stringify(data),
  }),
  
  updateBudget: (id: number, data: any) => request(`/api/budgets/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  }),

  deleteBudget: (id: number) => request(`/api/budgets/${id}`, {
    method: "DELETE",
  }),
  
  // Goals
  getGoals: () => request("/api/goals", { method: "GET" }),
  
  createGoal: (data: any) => request("/api/goals", {
    method: "POST",
    body: JSON.stringify(data),
  }),
  
  updateGoal: (id: number, data: any) => request(`/api/goals/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  }),
  
  // Chat
  sendChatMessage: (data: any) => request("/api/chat", {
    method: "POST",
    body: JSON.stringify(data),
  }),
  getChatHistory: (sessionId?: string) => request(`/api/chat/history?session_id=${sessionId || "default"}`, {
    method: "GET",
  }),
  
  // Forecast
  getProjections: () => request("/api/forecast/projections", { method: "GET" }),
  
  // Settings
  getSettings: () => request("/api/settings", { method: "GET" }),
  updateSettings: (data: any) => request("/api/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  }),
  
  // Audit Logs
  getAuditLogs: () => request("/api/admin/audit-logs", { method: "GET" }),

  // Income Sources
  getIncomeSources: () => request("/api/income-sources", { method: "GET" }),
  createIncomeSource: (data: any) => request("/api/income-sources", {
    method: "POST",
    body: JSON.stringify(data),
  }),
  updateIncomeSource: (id: number, data: any) => request(`/api/income-sources/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  }),
  deleteIncomeSource: (id: number) => request(`/api/income-sources/${id}`, {
    method: "DELETE",
  }),
  allocateIncomeSource: (id: number, data: { allocations: { goal_id: number; amount: number; notes?: string }[]; free_cash_amount: number }) =>
    request(`/api/income-sources/${id}/allocate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Recommendations & Actions
  applyRecommendation: (id: string, payload?: any) => request(`/api/recommendations/${id}/apply`, {
    method: "POST",
    body: JSON.stringify(payload || {}),
  }),
  dismissRecommendation: (id: string) => request(`/api/recommendations/${id}/dismiss`, {
    method: "POST",
  }),
};
