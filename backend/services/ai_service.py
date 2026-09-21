import json
import logging
from abc import ABC, abstractmethod
import requests
from config import settings

logger = logging.getLogger("ai_service")

class GeminiModelWrapper:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    def generate_content(self, prompt: str):
        resp = requests.post(
            self.url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        class Response:
            def __init__(self, t):
                self.text = t
        return Response(text)

class BaseAIService(ABC):
    @abstractmethod
    def generate_chat_response(self, user_financial_data: dict, history: list, user_message: str) -> str:
        """
        Generate a conversational chatbot response based on user financial summary and chat history.
        """
        pass

    @abstractmethod
    def generate_recommendations(self, user_financial_data: dict) -> list:
        """
        Generate a list of structured financial recommendations.
        """
        pass

    @abstractmethod
    def generate_monthly_analysis(self, user_financial_data: dict) -> str:
        """
        Generate a monthly report summary analysis.
        """
        pass

    @abstractmethod
    def generate_financial_coaching(self, user_financial_data: dict) -> str:
        """
        Generate personalized coaching goals and actionable tips.
        """
        pass


class GeminiAIService(BaseAIService):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client_enabled = bool(self.api_key)
        if self.client_enabled:
            try:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self.model = genai.GenerativeModel("gemini-1.5-flash")
                except ImportError:
                    self.model = GeminiModelWrapper(api_key=self.api_key)
                logger.info("Gemini AI Service initialized successfully.")
            except Exception as e:
                logger.error(f"Error configuring Gemini: {e}. Falling back to rule-based engine.")
                self.client_enabled = False
        else:
            logger.warning("No GEMINI_API_KEY configured. Falling back to rule-based FinTech advisor.")

    def _get_fallback_chat(self, user_financial_data: dict, user_message: str) -> str:
        msg = user_message.lower()
        income = user_financial_data.get("income", 50000.0)
        expenses = user_financial_data.get("expenses", 30000.0)
        savings = user_financial_data.get("savings", 20000.0)
        risk_level = user_financial_data.get("risk_level", "Medium")
        health_score = user_financial_data.get("health_score", 65)
        savings_goal = user_financial_data.get("savings_goal_target", 100000.0)
        
        if "risk" in msg:
            return (
                f"Based on your profile, your financial risk is currently evaluated as **{risk_level}** by our Machine Learning engine. "
                f"This takes into account your monthly income of {income} and expenses of {expenses}. "
                f"To lower your risk, we recommend decreasing your expense ratio, reducing any outstanding debt, "
                f"and keeping at least 3 to 6 months of expenses in an emergency fund."
            )
        elif "save" in msg or "saving" in msg:
            return (
                f"You currently have savings of **{savings}** (savings rate: {user_financial_data.get('savings_rate', 20)}%). "
                f"Your target savings goal is {savings_goal}. "
                f"Generally, it is wise to adhere to the 50/30/20 budget rule: allocate 50% of your income to needs, "
                f"30% to wants, and save the remaining 20%. Try automated savings transfers right after you receive your salary."
            )
        elif "health" in msg or "score" in msg:
            return (
                f"Your Financial Health Score is **{health_score}/100**. This score evaluates your saving rates, debt ratio, and budget discipline. "
                f"An excellent score is 80+. You can improve your score by keeping spending strictly within your category budgets, "
                f"and ensuring your debt ratio remains below 30% of your monthly income."
            )
        elif "expense" in msg or "spend" in msg:
            return (
                f"Your monthly expenses are **{expenses}**, representing an expense ratio of "
                f"{round((expenses/income)*100, 1) if income else 0}%. "
                f"Take a look at your top spending categories to find quick areas to cut back, "
                f"and ensure you have budget limits configured for utility and shopping expenses."
            )
        else:
            return (
                f"Hello! As your AI Personal Finance Advisor, I can help analyze your financial logs. "
                f"Currently, your Health Score is {health_score}/100 and your risk is {risk_level}. "
                f"How can I assist you with your budgets, savings, or investment strategies today?"
            )

    def generate_chat_response(self, user_financial_data: dict, history: list, user_message: str) -> str:
        if not self.client_enabled:
            return self._get_fallback_chat(user_financial_data, user_message)

        # Build comprehensive prompt
        system_prompt = (
            "You are an expert AI Personal Finance Advisor. Below is the user's financial profile. "
            "Use this as the source of truth for their financial details. Never make up transactions or numbers. "
            "Never predict risk level or health score yourself; always use the provided parameters. "
            "Respond professionally, clearly, and concisely in markdown. Limit responses to 2-3 paragraphs. "
            "If the user asks questions unrelated to personal finance, guide them back politely.\n\n"
            f"User Financial Profile:\n"
            f"- Monthly Income: {user_financial_data.get('income')}\n"
            f"- Monthly Expenses: {user_financial_data.get('expenses')}\n"
            f"- Current Savings: {user_financial_data.get('savings')}\n"
            f"- Savings Rate: {user_financial_data.get('savings_rate')}%\n"
            f"- Debt Ratio: {user_financial_data.get('debt_ratio')}%\n"
            f"- ML Risk Level: {user_financial_data.get('risk_level')}\n"
            f"- Financial Health Score: {user_financial_data.get('health_score')}/100\n"
            f"- Active Budgets: {user_financial_data.get('budgets')}\n"
            f"- Savings Goals: {user_financial_data.get('goals')}\n"
            f"- Detected Anomalies: {user_financial_data.get('anomalies')}\n\n"
        )

        # Add history
        history_context = ""
        for h in history[-8:]: # last 8 exchanges
            role = "User" if h.get("sender") == "user" else "Advisor"
            history_context += f"{role}: {h.get('message')}\n"

        prompt = system_prompt + "Conversation History:\n" + history_context + f"User: {user_message}\nAdvisor:"

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}. Falling back to rule-based response.")
            return self._get_fallback_chat(user_financial_data, user_message)

    def generate_recommendations(self, user_financial_data: dict) -> list:
        # Default fallback recommendations
        income = user_financial_data.get("income", 50000.0)
        expenses = user_financial_data.get("expenses", 30000.0)
        savings = user_financial_data.get("savings", 20000.0)
        risk_level = user_financial_data.get("risk_level", "Medium")
        health_score = user_financial_data.get("health_score", 65)
        
        fallback_recs = [
            {
                "title": "Establish an Emergency Fund",
                "description": f"Allocate at least 3-6 months of expenses (~{expenses * 3}) in a liquid high-yield savings account.",
                "category": "Savings",
                "priority": "High" if savings < (expenses * 3) else "Medium"
            },
            {
                "title": "Optimize Discretionary Spending",
                "description": "Evaluate non-essential shopping and utility subscriptions to lower your monthly expenses.",
                "category": "Budget",
                "priority": "High" if expenses / income > 0.6 else "Low"
            },
            {
                "title": "Reduce Debt Exposure",
                "description": "Repay high-interest debts or EMIs first to improve your debt ratio and boost health score.",
                "category": "Debt",
                "priority": "High" if risk_level == "High" else "Medium"
            },
            {
                "title": "Set Up Systematic Investment Plans",
                "description": "Start allocating 10-15% of your income into mutual funds or stable investment portfolios.",
                "category": "Investment",
                "priority": "Medium"
            }
        ]

        if not self.client_enabled:
            return fallback_recs

        prompt = (
            "You are an expert AI Personal Finance Advisor. Generate a JSON list containing 4 personalized financial recommendations. "
            "Each item in the list must be a JSON object with exactly the keys: 'title', 'description', 'category' (choose from: Savings, Budget, Debt, Investment), and 'priority' (choose from: High, Medium, Low). "
            "Do not include any extra text, markdown formatting, or triple backticks. Return ONLY a valid JSON array.\n\n"
            f"User Financial Profile:\n"
            f"- Monthly Income: {income}\n"
            f"- Monthly Expenses: {expenses}\n"
            f"- Current Savings: {savings}\n"
            f"- ML Risk Level: {risk_level}\n"
            f"- Health Score: {health_score}\n"
        )

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # Clean possible markdown block markers
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    text = "\n".join(lines[1:-1])
            recs = json.loads(text)
            if isinstance(recs, list) and len(recs) > 0:
                return recs
            return fallback_recs
        except Exception as e:
            logger.error(f"Gemini recommendations generation failed: {e}. Using fallback.")
            return fallback_recs

    def generate_monthly_analysis(self, user_financial_data: dict) -> str:
        income = user_financial_data.get("income", 50000.0)
        expenses = user_financial_data.get("expenses", 30000.0)
        savings = user_financial_data.get("savings", 20000.0)
        risk_level = user_financial_data.get("risk_level", "Medium")
        health_score = user_financial_data.get("health_score", 65)

        fallback_summary = (
            f"Your financial behaviors for this month show steady performance with a health score of {health_score}/100. "
            f"You spent {expenses} out of {income} in earnings, leaving a net savings of {savings}. "
            f"Your overall risk is {risk_level} based on your savings-to-income and debt profiles."
        )

        if not self.client_enabled:
            return fallback_summary

        prompt = (
            "You are an expert AI Personal Finance Advisor. Generate a concise monthly financial summary for the user's PDF report. "
            "Summarize their behavior, highlights of the month, any risk warnings, and a final motivational sentence. "
            "Write exactly 3-4 sentences in a professional tone.\n\n"
            f"User Financial Profile:\n"
            f"- Monthly Income: {income}\n"
            f"- Monthly Expenses: {expenses}\n"
            f"- Current Savings: {savings}\n"
            f"- Risk Level: {risk_level}\n"
            f"- Health Score: {health_score}\n"
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini monthly summary failed: {e}. Using fallback.")
            return fallback_summary

    def generate_financial_coaching(self, user_financial_data: dict) -> str:
        income = user_financial_data.get("income", 50000.0)
        expenses = user_financial_data.get("expenses", 30000.0)
        savings = user_financial_data.get("savings", 20000.0)
        risk_level = user_financial_data.get("risk_level", "Medium")
        health_score = user_financial_data.get("health_score", 65)

        fallback_coaching = (
            "### Actionable Financial Coaching Plan\n"
            "1. **Rule of 20%**: Immediately transfer 20% of your earnings to your savings at the start of the month.\n"
            "2. **Category Cap**: Apply strict budgets to discretionary spending (Food, Shopping) and review them weekly.\n"
            "3. **Emergency Cushion**: Target a savings fund equal to 6 months of expenses to buffer economic changes.\n"
            "4. **Financial Health Booster**: Lowering debt ratios is the fastest path to improve your health score."
        )

        if not self.client_enabled:
            return fallback_coaching

        prompt = (
            "You are an expert AI Personal Finance Advisor. Create a personalized, actionable financial coaching plan. "
            "Include 3-4 bullet points focusing on budgeting, debt management, and savings growth. "
            "Use markdown formatting with bolding. Limit to 150 words total.\n\n"
            f"User Profile:\n"
            f"- Income: {income}\n"
            f"- Expense: {expenses}\n"
            f"- Savings: {savings}\n"
            f"- Risk Level: {risk_level}\n"
            f"- Health Score: {health_score}\n"
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini coaching failed: {e}. Using fallback.")
            return fallback_coaching


# Global AI Service instance
ai_service = GeminiAIService()
