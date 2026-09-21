import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# Import generator to support automatic data bootstrapping
from dataset.generator import generate_synthetic_data
from utils import engineer_features

def train_model():
    dataset_path = "ml/dataset/financial_risk_data.csv"
    
    # Bootstrap dataset if missing
    if not os.path.exists(dataset_path):
        generate_synthetic_data(dataset_path)
        
    # Load dataset
    df = pd.read_csv(dataset_path)
    
    # Feature Engineering
    df = engineer_features(df)
    
    # Define features and target label
    feature_cols = [
        "income", "expenses", "savings", "debt", "transaction_count",
        "savings_rate", "expense_ratio", "debt_ratio", "avg_transaction"
    ]
    
    X = df[feature_cols]
    y = df["risk_level"]
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Compare Models
    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=500, random_state=42))
        ]),
        "Decision Tree": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", DecisionTreeClassifier(max_iter=None, random_state=42) if hasattr(DecisionTreeClassifier(), "max_iter") else DecisionTreeClassifier(random_state=42))
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", RandomForestClassifier(n_estimators=100, random_state=42))
        ])
    }
    
    best_name = None
    best_acc = 0.0
    best_pipeline = None
    
    print("\n--- Model Training & Comparison ---")
    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"{name} accuracy: {acc:.4f}")
        
        if acc > best_acc:
            best_acc = acc
            best_name = name
            best_pipeline = pipeline
            
    print(f"Selected Best Model: {best_name} with Accuracy: {best_acc:.4f}")
    
    # In case Random Forest is selected, save it. Save the best pipeline directly
    os.makedirs("ml", exist_ok=True)
    joblib.dump(best_pipeline, "ml/risk_model.pkl")
    print("Best performing ML pipeline saved to: ml/risk_model.pkl")

if __name__ == "__main__":
    train_model()
