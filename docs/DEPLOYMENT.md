# Production Deployment Guide: Supabase, Render, & Vercel

This guide outlines the step-by-step process to deploy your **FinRisk AI** backend to Render, database to Supabase, and connect them with your Vercel frontend.

---

## 💾 Step 1: Create a PostgreSQL Database on Supabase

Supabase provides a hosted PostgreSQL instance.

1. Go to [Supabase](https://supabase.com/) and sign up / log in.
2. Click **New Project** and select your organization.
3. Configure your project:
   - **Name**: `finrisk-db`
   - **Database Password**: Enter a secure password (write this down).
   - **Region**: Select a region close to you or your Render server (e.g., US East).
4. Wait for the database instance to provision (usually 1-2 minutes).
5. Go to **Project Settings** (gear icon) ➔ **Database**.
6. Scroll down to the **Connection string** section, select **URI**, and copy the connection string. It looks like this:
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```
7. Replace `[YOUR-PASSWORD]` with the password you created in step 3.

---

## 🐍 Step 2: Deploy the FastAPI Backend to Render

Render is a cloud platform suitable for hosting Python FastAPI applications.

### A. Push Code to GitHub
Render deploys directly from GitHub. Initialize git and push your repository:
```bash
# In the project root directory:
git init
git add .
git commit -m "feat: initial commit for deployment"
# Create a new repository on GitHub and run:
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

### B. Configure Render Web Service
1. Log in to [Render](https://render.com/).
2. Click **New +** in the top right corner and select **Web Service**.
3. Link your GitHub account and select your `financial-risk-analyzer` repository.
4. Set the following configuration parameters:
   - **Name**: `finrisk-backend`
   - **Environment**: `Python`
   - **Region**: Same region as your Supabase database.
   - **Branch**: `main`
   - **Root Directory**: `backend` *(This points Render directly to the backend sub-folder)*
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Scroll down and click **Advanced** to add **Environment Variables**:
   - **`DATABASE_URL`**: The connection URI you copied from Supabase (from Step 1).
   - **`GEMINI_API_KEY`**: Your Google Gemini API Key.
   - **`SECRET_KEY`**: A secure random string for JWT hashing (e.g., run `openssl rand -hex 32` to generate one).
6. Click **Create Web Service**. Render will build and deploy the backend. Once active, note your backend URL (e.g., `https://finrisk-backend.onrender.com`).

---

## 🌐 Step 3: Connect Vercel Frontend to Render Backend

Now update your Vercel deployment to communicate with the live Render backend instead of localhost.

1. Go to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Select your `frontend` project.
3. Navigate to **Settings** ➔ **Environment Variables**.
4. Create a new environment variable:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: Your Render live URL (e.g., `https://finrisk-backend.onrender.com`)
   - **Target**: Check `Production`, `Preview`, and `Development`.
5. Click **Save**.
6. Redeploy your frontend to apply the variable:
   - Navigate to the **Deployments** tab.
   - Click the three dots next to your latest deployment and select **Redeploy**.

---

## 🧪 Step 4: Verification

Once both services are deployed:
1. Open the Vercel live URL.
2. Sign up / login.
3. Import a CSV transaction log or chat with the AI Advisor.
4. All database queries will now read and write directly to your Supabase PostgreSQL instance in the cloud!
