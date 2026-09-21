# FinRisk AI - Financial Behavior & Risk Analyzer

FinRisk AI is a production-grade full-stack web application that allows users to monitor their personal transaction ledger, detect unusual duplicate payments, forecast expenses using linear regressions, and calculate an AI-driven financial risk metric utilizing scikit-learn classifiers.

---

## 🌟 Key Features

1. **Circular Financial Health Scoring**: Weights savings rate (35%), expense ratio (30%), debt ratio (20%), and consistency (15%) to score user financial wellness out of 100.
2. **Machine Learning Risk Prediction**: Compares Logistic Regression, Decision Trees, and Random Forests. Deploys the best classifier (95.5% accuracy Random Forest) to calculate risk level (Low / Medium / High) and model confidence.
3. **ReportLab PDF Statement Generator**: Generates professional, multi-page financial statements with grids, tables, and color-coded risk markers.
4. **CSV Import & Export Engine**: Bulk uploads transaction statements and parses dates/payment methods, alongside exporting CSV ledgers.
5. **Real-time Notifications Drawer**: Floating bell tray alerting users immediately on budget overruns, low savings thresholds, high risk states, and duplicate payment anomalies.
6. **User Account Manager**: Supports theme preferences (Light/Dark), currency changes (₹, $, €, £), secure password resets, and multipart file uploads for profile photos.
7. **Condition-based Budget Planner**: Set category limit targets and track spent vs remaining with overspending alerts.
8. **Goal Progression Tracker**: Track major goals (e.g. buying a laptop) via interactive percentage progress bars.
9. **Admin Dashboard**: System console providing stats on global active users, connection health, aggregate risk demographics, and top user categories.
10. **Containerized Deployments**: Clean Dockerfiles and `docker-compose` files to build and deploy locally or to Vercel/Render/Supabase.

---

## 🛠️ Technology Stack

- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS, Recharts, Lucide Icons, React Router DOM
- **Backend**: FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic, Python-Multipart
- **Database**: SQLite (local dev fallback) / PostgreSQL (production connection)
- **Machine Learning**: Pandas, NumPy, Scikit-learn, Joblib
- **Reporting**: ReportLab (PDF Generation), CSV parsing

---

## 📁 Repository Structure

```
financial-risk-analyzer/
├── frontend/             # Vite + React client
│   ├── src/
│   │   ├── components/
│   │   ├── context/      # Theme and Auth context
│   │   ├── pages/        # Settings, Admin, Dashboard
│   │   └── services/     # api, transactions services
│   ├── Dockerfile
│   └── nginx.conf
├── backend/              # FastAPI server
│   ├── database/         # Session states
│   ├── models/           # User, Profile, Transaction, Notification
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # auth, financial, notification, report
│   ├── routers/          # CRUD and export endpoints
│   ├── test_flow.py      # E2E validation script
│   └── Dockerfile
├── ml/                   # Machine learning pipeline
│   ├── dataset/          # Generator script
│   ├── risk_model.pkl    # Pickled Random Forest classifier
│   └── train.py          # Training comparison script
├── uploads/              # Local profile pictures directory
├── docker-compose.yml    # Main orchestration composer
└── README.md
```

---

## 🚀 Installation & Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- SQLite

### Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI uvicorn server:
   ```bash
   uvicorn main:app --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd ../frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Launch the Vite hot-reloading dev server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🐳 Running with Docker

Orchestrate the entire application (frontend, backend, and static file mounting) using:
```bash
docker-compose up --build
```
- Frontend will be accessible at [http://localhost](http://localhost)
- Backend docs will be accessible at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔒 Environment Configurations

Set these environment variables in your deployment environments (Vercel, Render, Supabase):
- `DATABASE_URL`: Connection string (PostgreSQL)
- `SECRET_KEY`: High-entropy key for signing JWTs
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT lifecycle (default 30)

---

## 🔌 API Endpoints Summary

### Authentication
- `POST /api/register` - Create user
- `POST /api/login` - Authenticate credentials and return JWT
- `GET /api/me` - Fetch logged-in user profile

### Transaction Ledger
- `GET /api/transactions` - List (with filters: type, category, month)
- `POST /api/transactions` - Create transaction
- `PUT /api/transactions/{id}` - Edit transaction
- `DELETE /api/transactions/{id}` - Delete transaction
- `POST /api/transactions/import-csv` - Import records
- `GET /api/transactions/export-csv` - Export CSV stream
- `GET /api/transactions/export-pdf` - Export PDF statements

### Analytics & Reports
- `GET /api/financials/summary` - Fetch dashboard metrics, alerts, and forecasts
- `POST /api/predict-risk` - Compute ML risk levels standalone
- `GET /api/reports/download-pdf` - Generate and download ReportLab PDF statement

---

## 🤖 Machine Learning Pipeline

1. **Feature Engineering**: Converts raw transactions into structured parameters:
   - **Savings Rate** = `savings / income`
   - **Expense Ratio** = `expenses / income`
   - **Debt Ratio** = `debt / income`
   - **Spending Consistency** based on frequency of payments
2. **Model Selection**: Trained on 2,000 synthetic financial entries. Random Forest Classifier won with a cross-validation score of **95.5%** and was pickled to `ml/risk_model.pkl`.
