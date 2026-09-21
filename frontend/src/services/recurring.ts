import { request } from "./api";

export interface RecurringPayment {
  id: string;
  user_id: string;
  merchant_name: string;
  normalized_name: string;
  category: string;
  frequency: "weekly" | "biweekly" | "monthly" | "quarterly" | "annual";
  average_amount: number;
  last_amount: number;
  estimated_monthly_cost: number;
  estimated_annual_cost: number;
  confidence: number;
  status: "detected" | "confirmed" | "dismissed";
  last_payment_date: string;
  next_estimated_date: string | null;
  transaction_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecurringPaymentSummary {
  total_monthly_commitment: number;
  total_annual_commitment: number;
  active_subscriptions_count: number;
  confirmed_count: number;
  detected_count: number;
  dismissed_count: number;
  upcoming_payments_next_30_days: RecurringPayment[];
}

export interface ScanResponse {
  scanned_transactions_count: number;
  new_detected_count: number;
  updated_count: number;
  total_active_count: number;
  items: RecurringPayment[];
  message: string;
}

export const recurringApi = {
  list: (status?: string): Promise<RecurringPayment[]> => {
    const url = status ? `/api/recurring-payments?status=${encodeURIComponent(status)}` : "/api/recurring-payments";
    return request(url);
  },

  scan: (): Promise<ScanResponse> => {
    return request("/api/recurring-payments/scan", {
      method: "POST",
    });
  },

  summary: (): Promise<RecurringPaymentSummary> => {
    return request("/api/recurring-payments/summary");
  },

  update: (id: string, data: { status?: string; notes?: string; frequency?: string; average_amount?: number }): Promise<RecurringPayment> => {
    return request(`/api/recurring-payments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  delete: (id: string): Promise<void> => {
    return request(`/api/recurring-payments/${id}`, {
      method: "DELETE",
    });
  },
};
