import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Group

from services.categorization_service import categorization_engine

def parse_transactions_csv(file_content: str) -> List[Dict[str, Any]]:
    """
    Parse transaction records from uploaded bank statements or expense CSV files.
    Supports standard CSV headers as well as bank statement formats (Debit/Credit columns, CR/DR, Narration).
    Enriches transactions with auto-categorization and confidence metrics.
    """
    transactions = []
    
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8", errors="ignore")

    # Read the file line-by-line
    reader = csv.reader(io.StringIO(file_content))
    
    # Try to read header
    header = next(reader, None)
    if not header:
        return transactions
        
    # Map header fields to columns (case-insensitive & whitespace/symbol agnostic)
    field_map = {}
    for i, col in enumerate(header):
        c_clean = col.strip().lower().replace("_", "").replace(" ", "").replace("-", "")
        if any(k in c_clean for k in ["valuedate", "txndate", "transactiondate", "date"]):
            if "date" not in field_map:
                field_map["date"] = i
        elif any(k in c_clean for k in ["category", "cat"]):
            field_map["category"] = i
        elif any(k in c_clean for k in ["type", "crdr", "drcr"]):
            field_map["type"] = i
        elif any(k in c_clean for k in ["debit", "withdrawal"]):
            field_map["debit"] = i
        elif any(k in c_clean for k in ["credit", "deposit"]):
            field_map["credit"] = i
        elif any(k in c_clean for k in ["amount", "txnsum", "amt"]):
            if "amount" not in field_map:
                field_map["amount"] = i
        elif any(k in c_clean for k in ["description", "desc", "narration", "particulars", "details", "merchant", "payee"]):
            if "description" not in field_map:
                field_map["description"] = i
        elif any(k in c_clean for k in ["paymentmethod", "paymentmode", "mode", "method", "pay"]):
            if "payment_method" not in field_map:
                field_map["payment_method"] = i
            
    # Process rows
    for row in reader:
        if not row:
            continue
            
        try:
            # 1. Parse Date
            raw_date = row[field_map["date"]].strip() if "date" in field_map and field_map["date"] < len(row) else None
            tx_date = date.today()
            if raw_date:
                for date_fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y"]:
                    try:
                        tx_date = datetime.strptime(raw_date, date_fmt).date()
                        break
                    except Exception:
                        continue

            # 2. Extract Description & Payment Method
            description = row[field_map["description"]].strip() if "description" in field_map and field_map["description"] < len(row) else ""
            pay_method = row[field_map["payment_method"]].strip() if "payment_method" in field_map and field_map["payment_method"] < len(row) else "Bank Transfer"
            if not pay_method:
                pay_method = "Bank Transfer"

            # 3. Determine Amount & Direction (Expense vs Income)
            type_val = "Expense"
            amount_val = 0.0

            # Check separate Debit / Credit columns first
            debit_raw = row[field_map["debit"]].strip().replace(",", "").replace("$", "").replace("₹", "") if "debit" in field_map and field_map["debit"] < len(row) else ""
            credit_raw = row[field_map["credit"]].strip().replace(",", "").replace("$", "").replace("₹", "") if "credit" in field_map and field_map["credit"] < len(row) else ""

            debit_amount = float(debit_raw) if debit_raw and debit_raw != "-" else 0.0
            credit_amount = float(credit_raw) if credit_raw and credit_raw != "-" else 0.0

            if debit_amount > 0:
                amount_val = debit_amount
                type_val = "Expense"
            elif credit_amount > 0:
                amount_val = credit_amount
                type_val = "Income"
            elif "amount" in field_map and field_map["amount"] < len(row):
                raw_amt = row[field_map["amount"]].strip().replace(",", "").replace("$", "").replace("₹", "")
                parsed_amt = float(raw_amt) if raw_amt and raw_amt != "-" else 0.0
                
                # Check for explicit type column
                type_raw = row[field_map["type"]].strip().upper() if "type" in field_map and field_map["type"] < len(row) else ""
                if type_raw in ["INCOME", "CR", "CREDIT"]:
                    type_val = "Income"
                    amount_val = abs(parsed_amt)
                elif type_raw in ["EXPENSE", "DR", "DEBIT"]:
                    type_val = "Expense"
                    amount_val = abs(parsed_amt)
                elif parsed_amt < 0:
                    type_val = "Expense"
                    amount_val = abs(parsed_amt)
                else:
                    type_val = "Income" if type_raw == "INCOME" else "Expense"
                    amount_val = parsed_amt

            if amount_val <= 0:
                continue

            # 4. Auto-Categorize
            raw_category = row[field_map["category"]].strip() if "category" in field_map and field_map["category"] < len(row) else ""
            cat_result = categorization_engine.categorize(
                description=description,
                tx_type=type_val,
                amount=amount_val,
                current_category=raw_category,
            )

            transactions.append({
                "type": type_val,
                "category": cat_result["suggested_category"],
                "suggested_category": cat_result["suggested_category"],
                "category_confidence": cat_result["confidence"],
                "explanation": cat_result["explanation"],
                "is_reviewed": cat_result["is_reviewed"],
                "amount": round(amount_val, 2),
                "description": description,
                "transaction_date": tx_date,
                "payment_method": pay_method
            })
        except Exception:
            # Skip invalid rows silently
            continue
            
    return transactions

def generate_transactions_csv(transactions: List[Any]) -> str:
    """Generate CSV string of transaction records."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Date", "Category", "Type", "Amount", "Description", "Payment Method"])
    
    for tx in transactions:
        writer.writerow([
            tx.transaction_date.isoformat(),
            tx.category,
            tx.type,
            tx.amount,
            tx.description or "",
            tx.payment_method
        ])
        
    return output.getvalue()

def generate_pdf_report(
    buffer: io.BytesIO,
    user_name: str,
    user_email: str,
    income: float,
    expenses: float,
    savings: float,
    risk_level: str,
    health_score: int,
    health_grade: str,
    insights: List[str],
    recommendations: List[str],
    transactions: List[Any],
    currency_symbol: str = "₹"
):
    """Generate a clean, beautiful PDF report using ReportLab."""
    
    # Setup document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    # Theme colors
    PRIMARY = colors.HexColor("#10b981") # Emerald Green
    SECONDARY = colors.HexColor("#3b82f6") # Blue
    DARK_BG = colors.HexColor("#0f172a") # Slate 900
    TEXT_DARK = colors.HexColor("#1e293b") # Slate 800
    TEXT_LIGHT = colors.HexColor("#64748b") # Slate 500
    LIGHT_BG = colors.HexColor("#f8fafc") # Slate 50
    BORDER_COLOR = colors.HexColor("#e2e8f0") # Slate 200
    
    # Color-coded colors for risk
    if risk_level == "Low":
        RISK_COLOR = colors.HexColor("#10b981") # Emerald
    elif risk_level == "Medium":
        RISK_COLOR = colors.HexColor("#f59e0b") # Amber
    else:
        RISK_COLOR = colors.HexColor("#ef4444") # Red
        
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_title = ParagraphStyle(
        name="DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=15
    )
    
    style_subtitle = ParagraphStyle(
        name="DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=TEXT_LIGHT,
        spaceAfter=20
    )
    
    style_h2 = ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=DARK_BG,
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK
    )
    
    style_bullet = ParagraphStyle(
        name="BulletCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5
    )
    
    style_card_label = ParagraphStyle(
        name="CardLabel",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=TEXT_LIGHT
    )
    
    style_card_val = ParagraphStyle(
        name="CardValue",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=DARK_BG
    )
    
    elements = []
    
    # --- Header ---
    elements.append(Paragraph("Financial Behavior & Risk Analysis Report", style_title))
    elements.append(Paragraph(
        f"<b>Generated For:</b> {user_name} ({user_email}) &nbsp;|&nbsp; <b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}",
        style_subtitle
    ))
    
    # --- Health Score and Risk Section ---
    elements.append(Paragraph("Health Score & ML Risk Profile", style_h2))
    
    # Score Drawing Block
    health_draw = Drawing(520, 80)
    # Draw Background
    health_draw.add(Rect(0, 0, 520, 80, fillColor=LIGHT_BG, strokeColor=BORDER_COLOR, strokeWidth=1, rx=8, ry=8))
    # Draw score bar background
    health_draw.add(Rect(20, 40, 220, 15, fillColor=colors.HexColor("#e2e8f0"), strokeColor=None, rx=4, ry=4))
    # Draw score fill
    score_fill_width = 220 * (health_score / 100.0)
    health_draw.add(Rect(20, 40, score_fill_width, 15, fillColor=PRIMARY, strokeColor=None, rx=4, ry=4))
    # Labels
    health_draw.add(String(20, 60, "Financial Health Score", fontName="Helvetica-Bold", fontSize=10, fillColor=TEXT_DARK))
    health_draw.add(String(20, 20, f"Score: {health_score}/100 ({health_grade})", fontName="Helvetica", fontSize=9, fillColor=TEXT_LIGHT))
    
    # Risk Level Box
    health_draw.add(Rect(320, 20, 180, 40, fillColor=RISK_COLOR, strokeColor=None, rx=6, ry=6))
    health_draw.add(String(330, 45, "ML Predicted Risk Level", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.white))
    health_draw.add(String(330, 28, risk_level.upper(), fontName="Helvetica-Bold", fontSize=14, fillColor=colors.white))
    
    elements.append(health_draw)
    elements.append(Spacer(1, 15))
    
    # --- Summary Metrics Cards ---
    elements.append(Paragraph("Key Financial Metrics", style_h2))
    
    # Build a card grid table
    metrics_data = [
        [
            Paragraph("Monthly Income", style_card_label),
            Paragraph("Monthly Expenses", style_card_label),
            Paragraph("Net Savings", style_card_label)
        ],
        [
            Paragraph(f"{currency_symbol}{income:,.2f}", style_card_val),
            Paragraph(f"{currency_symbol}{expenses:,.2f}", style_card_val),
            Paragraph(f"{currency_symbol}{savings:,.2f}", style_card_val)
        ]
    ]
    
    metrics_table = Table(metrics_data, colWidths=[173, 173, 174])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 2),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 10),
        ('LINEBELOW', (0,0), (-1,0), 0.5, colors.white),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 15))
    
    # --- AI Insights & Recommendations ---
    diag_data = []
    
    # Add Insights
    diag_data.append(Paragraph("AI Spending Insights", style_h2))
    if insights:
        for ins in insights:
            diag_data.append(Paragraph(f"• &nbsp;{ins}", style_bullet))
    else:
        diag_data.append(Paragraph("No critical spending deviations detected.", style_body))
        
    diag_data.append(Spacer(1, 10))
    
    # Add Recommendations
    diag_data.append(Paragraph("Actionable Recommendations", style_h2))
    if recommendations:
        for rec in recommendations:
            diag_data.append(Paragraph(f"• &nbsp;<b>{rec.split(':')[0]}:</b>{rec.split(':')[1] if len(rec.split(':')) > 1 else ''}", style_bullet))
    else:
        diag_data.append(Paragraph("Maintain current financial behavior. Review subscription leakage periodically.", style_body))
        
    elements.append(KeepTogether(diag_data))
    elements.append(Spacer(1, 15))
    
    # --- Recent Transactions Ledger ---
    elements.append(Paragraph("Recent Transactions Record", style_h2))
    
    tx_headers = ["Date", "Category", "Type", "Amount", "Method", "Description"]
    tx_rows = [tx_headers]
    
    # Add up to 10 transactions to keep it neat
    for tx in transactions[:10]:
        tx_rows.append([
            tx.transaction_date.strftime("%Y-%m-%d"),
            tx.category,
            tx.type,
            f"{currency_symbol}{tx.amount:,.2f}",
            tx.payment_method,
            tx.description or ""
        ])
        
    # If no transactions
    if len(tx_rows) == 1:
        tx_rows.append(["No records", "", "", "", "", ""])
        
    tx_table = Table(tx_rows, colWidths=[70, 80, 50, 80, 80, 160])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK_BG),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
    ]))
    
    elements.append(tx_table)
    
    # Build Document
    doc.build(elements)
