import os
import numpy as np
import pandas as pd

def generate_synthetic_data(output_path: str, num_samples: int = 2000):
    np.random.seed(42)
    
    # Generate random baseline variables
    income = np.random.randint(25000, 200000, size=num_samples)
    
    # Expenses usually scale with income (with some random variance)
    expense_ratio_base = np.random.uniform(0.3, 0.95, size=num_samples)
    expenses = (income * expense_ratio_base).astype(int)
    
    # Savings = Income - Expenses
    savings = income - expenses
    
    # Debt generation (some have no debt, some have high debt)
    has_debt = np.random.choice([0, 1], size=num_samples, p=[0.3, 0.7])
    debt_ratio_base = np.random.uniform(0.0, 0.8, size=num_samples)
    debt = (income * debt_ratio_base * has_debt).astype(int)
    
    transaction_count = np.random.randint(10, 100, size=num_samples)
    
    # Categories breakdown
    food_pct = np.random.uniform(0.15, 0.35, size=num_samples)
    shopping_pct = np.random.uniform(0.10, 0.30, size=num_samples)
    ent_pct = np.random.uniform(0.05, 0.20, size=num_samples)
    
    food_expense = (expenses * food_pct).astype(int)
    shopping_expense = (expenses * shopping_pct).astype(int)
    entertainment_expense = (expenses * ent_pct).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "debt": debt,
        "transaction_count": transaction_count,
        "food_expense": food_expense,
        "shopping_expense": shopping_expense,
        "entertainment_expense": entertainment_expense
    })
    
    # Classify Target: Risk Level (Low, Medium, High)
    # Rules + random noise
    risk_labels = []
    for i in range(num_samples):
        inc = income[i]
        sav_rate = savings[i] / inc
        debt_rate = debt[i] / inc
        exp_rate = expenses[i] / inc
        
        # High Risk Conditions
        if debt_rate > 0.5 or sav_rate < 0.05 or exp_rate > 0.9:
            score = "High"
        # Medium Risk Conditions
        elif debt_rate > 0.25 or sav_rate < 0.15 or exp_rate > 0.75:
            score = "Medium"
        else:
            score = "Low"
            
        # Add 5% noise to make ML training meaningful
        if np.random.uniform() < 0.05:
            score = np.random.choice(["Low", "Medium", "High"])
            
        risk_labels.append(score)
        
    df["risk_level"] = risk_labels
    
    # Create parent folder if not exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated synthetic dataset with {num_samples} records at: {output_path}")

if __name__ == "__main__":
    generate_synthetic_data("ml/dataset/financial_risk_data.csv")
