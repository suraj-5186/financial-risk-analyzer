import urllib.request
import urllib.parse
import json
import random
import sys
import sqlite3
from datetime import date

BASE_URL = "http://127.0.0.1:8000"

def make_request(path, method="GET", data=None, headers=None, is_form=False, is_file=False):
    url = f"{BASE_URL}{path}"
    req_headers = {}
    if not is_file:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
        
    req_data = None
    if data is not None:
        if is_form:
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            req_data = urllib.parse.urlencode(data).encode("utf-8")
        elif is_file:
            # Simple multipart/form-data generator for testing upload
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            req_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            
            parts = []
            filename, file_content = data
            parts.append(f"--{boundary}")
            parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
            parts.append("Content-Type: text/csv")
            parts.append("")
            parts.append(file_content)
            parts.append(f"--{boundary}--")
            parts.append("")
            req_data = "\r\n".join(parts).encode("utf-8")
        else:
            req_data = json.dumps(data).encode("utf-8")
            
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_headers = response.info()
            resp_body = response.read()
            
            # If PDF or CSV, return raw content with headers
            content_type = resp_headers.get("Content-Type", "")
            if "pdf" in content_type or "csv" in content_type:
                return response.status, {"headers": resp_headers, "body": resp_body}
                
            resp_text = resp_body.decode("utf-8")
            return response.status, json.loads(resp_text) if resp_text else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code} on {method} {path}: {err_body}")
        return e.code, err_body
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return 500, str(e)

def run_test():
    print("--- Starting End-to-End API Verification ---")
    
    # 1. Register User
    email = f"agent_tester_{random.randint(1000, 9999)}@test.com"
    register_payload = {
        "email": email,
        "full_name": "E2E Test Agent",
        "password": "TestPassword123!"
    }
    
    print(f"1. Registering user with email: {email}")
    status, res = make_request("/api/register", "POST", register_payload)
    if status != 200:
        print(f"Failed to register: {res}")
        sys.exit(1)
    print("Registration successful.")
    
    # 2. Login User
    login_payload = {
        "email": email,
        "password": "TestPassword123!"
    }
    print("2. Logging in...")
    status, res = make_request("/api/login", "POST", login_payload, is_form=False)
    if status != 200:
        print(f"Failed to login: {res}")
        sys.exit(1)
    token = res["access_token"]
    print("Login successful, JWT token obtained.")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 3. Update Profile details (currency, budget, goals)
    print("3. Updating profile settings...")
    profile_payload = {
        "full_name": "E2E Verified Agent",
        "currency": "USD",
        "theme": "dark",
        "monthly_income": 80000.0,
        "monthly_budget": 40000.0,
        "savings_goal_title": "Tesla Fund",
        "savings_goal_target": 120000.0,
        "savings_goal_current": 45000.0
    }
    status, res = make_request("/api/users/profile", "PUT", profile_payload, headers=headers)
    if status != 200:
        print(f"Failed to update user profile: {res}")
        sys.exit(1)
    print("Profile settings successfully updated.")
    
    # 4. Import Transactions via CSV
    print("4. Testing CSV Transactions Import...")
    csv_data = (
        "Date,Category,Type,Amount,Description,Payment Method\n"
        "2026-06-25,Freelance,Income,15000.0,Consulting gig,Direct Deposit\n"
        "2026-06-25,Rent,Expense,1200.0,Apartment rent,Bank Transfer\n"
        "2026-06-25,Food,Expense,150.0,Dinner,Credit Card\n"
        "2026-06-25,Food,Expense,150.0,Dinner,Credit Card\n"  # Duplicate
        "2026-06-25,Shopping,Expense,8500.0,MacBook accessory,Credit Card" # Large Spike
    )
    status, res = make_request("/api/transactions/import-csv", "POST", ("bank.csv", csv_data), headers=headers, is_file=True)
    if status != 200:
        print(f"Failed to import CSV: {res}")
        sys.exit(1)
    print(f"CSV Import result: {res}")
    
    # 5. Fetch Notifications
    print("5. Retrieving system notifications...")
    status, notis = make_request("/api/notifications", "GET", headers=headers)
    if status != 200:
        print(f"Failed to get notifications: {notis}")
        sys.exit(1)
    print(f"Active Notifications count: {len(notis)}")
    for n in notis:
        print(f"- [{n['type'].upper()}] {n['title']}: {n['message']}")
        
    # Mark first notification as read
    if notis:
        print(f"Marking notification ID {notis[0]['id']} as read...")
        status, read_res = make_request(f"/api/notifications/{notis[0]['id']}/read", "PUT", headers=headers)
        if status == 200:
            print("Notification marked read successfully.")
            
    # 6. Export Transactions CSV
    print("6. Requesting CSV export stream...")
    status, res = make_request("/api/transactions/export-csv", "GET", headers=headers)
    if status != 200:
        print(f"Failed to export CSV: {res}")
        sys.exit(1)
    csv_body = res["body"].decode("utf-8")
    print(f"Export CSV headers check: {csv_body.splitlines()[0] if csv_body.splitlines() else 'Empty'}")
    
    # 7. Export Transactions PDF Statement
    print("7. Requesting PDF transactions export...")
    status, res = make_request("/api/transactions/export-pdf", "GET", headers=headers)
    if status != 200:
        print(f"Failed to export transactions PDF: {res}")
        sys.exit(1)
    pdf_body = res["body"]
    print(f"PDF Transactions size: {len(pdf_body)} bytes. Starts with: {pdf_body[:5]}")
    
    # 8. Download AI Financial Report PDF
    print("8. Requesting full ReportLab PDF report...")
    status, res = make_request("/api/reports/download-pdf", "GET", headers=headers)
    if status != 200:
        print(f"Failed to download PDF report: {res}")
        sys.exit(1)
    report_body = res["body"]
    print(f"Report PDF size: {len(report_body)} bytes. Starts with: {report_body[:5]}")
    
    # 9. Verify Admin Dashboard (Grant admin role first)
    print("9. Granting admin role to test account in database...")
    try:
        conn = sqlite3.connect("financial_risk.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        print("Admin permissions granted.")
    except Exception as e:
        print(f"Database error: {str(e)}")
        sys.exit(1)
        
    print("Requesting Admin Dashboard stats...")
    status, admin_data = make_request("/api/admin/dashboard", "GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch admin stats: {admin_data}")
        sys.exit(1)
    print("\n--- Admin Dashboard Summary ---")
    print(f"Total Active Users: {admin_data['total_users']}")
    print(f"Total Transactions: {admin_data['total_transactions']}")
    print(f"Average Health Score: {admin_data['average_health_score']}")
    print(f"Risk Levels: {admin_data['risk_level_distribution']}")
    print(f"System State: {admin_data['system']}")

    # 10. Test Forecast Projections
    print("\n10. Testing Forecast Projections endpoint...")
    status, forecast_data = make_request("/api/forecast/projections", "GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch forecast: {forecast_data}")
        sys.exit(1)
    print(f"Forecast Projections response: {forecast_data}")

    # 11. Test Settings endpoints
    print("\n11. Testing Settings endpoints...")
    status, current_settings = make_request("/api/settings", "GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch settings: {current_settings}")
        sys.exit(1)
    print(f"Fetched User Settings: {current_settings}")

    status, updated_settings = make_request("/api/settings", "PUT", {
        "monthly_budget": 60000.0,
        "savings_goal": 150000.0,
        "currency": "USD",
        "theme": "light"
    }, headers=headers)
    if status != 200:
        print(f"Failed to update settings: {updated_settings}")
        sys.exit(1)
    print(f"Updated User Settings: {updated_settings}")

    # 12. Test Chat chatbot endpoints
    print("\n12. Testing Chat AI Advisor endpoints...")
    status, chat_response = make_request("/api/chat", "POST", {
        "message": "Why is my financial risk level high? What options do I have?"
    }, headers=headers)
    if status != 200:
        print(f"Failed to query AI chat: {chat_response}")
        sys.exit(1)
    print(f"AI Advisor Reply: {chat_response['message']}")

    status, chat_history = make_request("/api/chat/history", "GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch chat history: {chat_history}")
        sys.exit(1)
    print(f"Chat History Messages count: {len(chat_history)}")

    # 13. Test Admin Audit Logs endpoint
    print("\n13. Testing Admin Audit Logs endpoints...")
    status, audit_logs = make_request("/api/admin/audit-logs", "GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch audit logs: {audit_logs}")
        sys.exit(1)
    print(f"Audit Logs fetched count: {len(audit_logs)}")
    print(f"Latest Action Log: [{audit_logs[0]['action']}] - {audit_logs[0]['details']}")

    print("\n--- ALL BACKEND CHECKS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_test()
