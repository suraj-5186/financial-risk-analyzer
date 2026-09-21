import { request } from "./api";

export interface CategorySpendItem {
  category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
}

export interface CashFlowTrendPoint {
  month_key: string;
  month_label: string;
  income: number;
  expenses: number;
  net_cash_flow: number;
}

export interface CashFlowComparison {
  previous_income: number;
  previous_expenses: number;
  previous_net_cash_flow: number;
  income_change_pct?: number | null;
  expense_change_pct?: number | null;
  net_flow_change_pct?: number | null;
}

export interface CashFlowSummary {
  timeframe: string;
  period_start: string;
  period_end: string;
  previous_period_start: string;
  previous_period_end: string;
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  savings_rate?: number | null;
  transaction_count: number;
  categories: CategorySpendItem[];
  trends: CashFlowTrendPoint[];
  comparison: CashFlowComparison;
}

export interface RecurringCommitmentDue {
  merchant_name: string;
  amount: number;
  due_date: string;
  frequency: string;
}

export interface MonthEndForecast {
  month_label: string;
  days_remaining: number;
  actual_income_to_date: number;
  actual_expense_to_date: number;
  projected_additional_discretionary: number;
  projected_additional_recurring: number;
  projected_total_expenses: number;
  projected_total_income: number;
  projected_net_cash_flow: number;
  upcoming_recurring_commitments: RecurringCommitmentDue[];
}

export interface Next30DaysForecast {
  projected_income: number;
  projected_discretionary_expense: number;
  projected_recurring_expense: number;
  projected_total_expense: number;
  projected_net_cash_flow: number;
  upcoming_recurring_count: number;
}

export interface ForecastMethodology {
  daily_discretionary_burn: number;
  total_monthly_recurring_commitments: number;
  explanations: string[];
  disclaimer: string;
}

export interface CashFlowForecast {
  as_of_date: string;
  data_quality: "insufficient" | "low" | "medium" | "high";
  confidence_score: number;
  confidence_label: string;
  is_estimate: boolean;
  month_end_forecast: MonthEndForecast;
  next_30_days_forecast: Next30DaysForecast;
  methodology: ForecastMethodology;
}

export interface FinancialInsightItem {
  id: string;
  type: "risk" | "warning" | "opportunity" | "achievement" | "info";
  title: string;
  description: string;
  period: string;
  metric_impact: string;
  explanation: string;
  recommended_action: string;
}

export interface FinancialHealthData {
  as_of_date: string;
  timeframe: string;
  overall_health: string;
  health_tone: "risk" | "warning" | "healthy" | "info";
  total_insights_count: number;
  insights: FinancialInsightItem[];
}

export const insightsApi = {
  getCashFlow: (timeframe: string = "30d", startDate?: string, endDate?: string): Promise<CashFlowSummary> => {
    const params = new URLSearchParams();
    if (timeframe) params.append("timeframe", timeframe);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    return request(`/api/insights/cash-flow?${params.toString()}`);
  },

  getForecast: (): Promise<CashFlowForecast> => {
    return request("/api/insights/forecast");
  },

  getFinancialHealth: (timeframe: string = "30d"): Promise<FinancialHealthData> => {
    return request(`/api/insights/financial-health?timeframe=${encodeURIComponent(timeframe)}`);
  },
};
