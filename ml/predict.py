import os
import json
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_MODEL_PATH = os.path.join(BASE_DIR, "risk_model.json")
PKL_MODEL_PATH = os.path.join(BASE_DIR, "risk_model.pkl")

_json_model = None
_pkl_model = None

def load_json_model():
    global _json_model
    if _json_model is None and os.path.exists(JSON_MODEL_PATH):
        with open(JSON_MODEL_PATH, "r") as f:
            _json_model = json.load(f)
    return _json_model

def predict_pure_python(features: list, model_data: dict) -> tuple:
    mean = model_data["mean"]
    scale = model_data["scale"]
    classes = model_data["classes"]
    trees = model_data["trees"]

    # StandardScaler transform
    scaled = [(x - m) / s for x, m, s in zip(features, mean, scale)]

    # Evaluate decision trees
    n_trees = len(trees)
    n_classes = len(classes)
    total_probs = [0.0] * n_classes

    for tree in trees:
        node = 0
        while tree["feature"][node] != -2:
            feat = tree["feature"][node]
            th = tree["threshold"][node]
            if scaled[feat] <= th:
                node = tree["children_left"][node]
            else:
                node = tree["children_right"][node]
        val = tree["value"][node]
        for c in range(n_classes):
            total_probs[c] += val[c]

    avg_probs = [p / n_trees for p in total_probs]
    best_idx = avg_probs.index(max(avg_probs))
    return str(classes[best_idx]), round(float(avg_probs[best_idx]), 2)

def predict_financial_risk(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts customer profile details:
    {
       "income": float,
       "expenses": float,
       "savings": float,
       "debt": float,
       "transaction_count": int
    }
    Returns:
    {
       "risk_level": "Low" | "Medium" | "High",
       "confidence": float
    }
    """
    income_val = float(data.get("income", 0))
    expenses_val = float(data.get("expenses", 0))
    savings_val = float(data.get("savings", 0))
    debt_val = float(data.get("debt", 0))
    trans_count = int(data.get("transaction_count", 0))

    income_safe = income_val if income_val != 0 else 1.0
    trans_safe = trans_count if trans_count != 0 else 1.0

    features = [
        income_val,
        expenses_val,
        savings_val,
        debt_val,
        float(trans_count),
        savings_val / income_safe,
        expenses_val / income_safe,
        debt_val / income_safe,
        expenses_val / trans_safe,
    ]

    json_model = load_json_model()
    if json_model:
        risk_level, confidence = predict_pure_python(features, json_model)
        return {
            "risk_level": risk_level,
            "confidence": confidence,
        }

    # Fallback to joblib + scikit-learn if available
    try:
        import joblib
        import pandas as pd
        global _pkl_model
        if _pkl_model is None:
            _pkl_model = joblib.load(PKL_MODEL_PATH)
        row = {
            "income": income_val,
            "expenses": expenses_val,
            "savings": savings_val,
            "debt": debt_val,
            "transaction_count": trans_count,
            "savings_rate": savings_val / income_safe,
            "expense_ratio": expenses_val / income_safe,
            "debt_ratio": debt_val / income_safe,
            "avg_transaction": expenses_val / trans_safe,
        }
        df = pd.DataFrame([row])
        pred = _pkl_model.predict(df)[0]
        probs = _pkl_model.predict_proba(df)[0]
        class_idx = list(_pkl_model.classes_).index(pred)
        return {
            "risk_level": str(pred),
            "confidence": round(float(probs[class_idx]), 2),
        }
    except Exception as e:
        # Heuristic fallback if model files are missing
        if debt_val > income_safe * 0.5 or expenses_val > income_safe * 0.8:
            return {"risk_level": "High", "confidence": 0.85}
        elif expenses_val > income_safe * 0.5:
            return {"risk_level": "Medium", "confidence": 0.75}
        return {"risk_level": "Low", "confidence": 0.90}
