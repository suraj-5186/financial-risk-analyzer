import pandas as pd

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer financial features for training and prediction models."""
    df = df.copy()
    
    # Avoid zero-division exceptions
    income_safe = df['income'].replace(0, 1)
    trans_safe = df['transaction_count'].replace(0, 1)
    
    # Core Ratios
    df['savings_rate'] = df['savings'] / income_safe
    df['expense_ratio'] = df['expenses'] / income_safe
    df['debt_ratio'] = df['debt'] / income_safe
    df['avg_transaction'] = df['expenses'] / trans_safe
    
    # Ensure no NaN/Inf remains
    df = df.fillna(0)
    
    return df
