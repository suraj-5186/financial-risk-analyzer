import calendar
import datetime
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.session import get_db
from models.user import User
from models.transaction import Transaction
from models.budget import Budget
import sys
import os
# Add parent directory to sys.path to allow importing from ml
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ml.predict import predict_financial_risk

from schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    PredictRiskRequest, PredictRiskResponse,
    CategorizeRequest, CategorizeResponse,
    ParseCsvResponse, ParseCsvItem, ConfirmImportRequest
)
from services.auth_service import get_current_user
from services.report_service import parse_transactions_csv, generate_transactions_csv
from services.categorization_service import categorization_engine, normalize_category_name
from services.notification_service import check_and_trigger_notifications
from services.audit_service import log_audit_event



router = APIRouter(prefix="/api/transactions", tags=["transactions"])
risk_router = APIRouter(prefix="/api", tags=["risk"])

@risk_router.post("/predict-risk", response_model=PredictRiskResponse)
def predict_risk(
    req: PredictRiskRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        prediction = predict_financial_risk({
            "income": req.income,
            "expenses": req.expenses,
            "savings": req.savings,
            "debt": req.debt,
            "transaction_count": req.transaction_count
        })
        
        from models.profile import FinancialProfile
        from services.financial_service import calculate_weighted_health_score
        
        mock_profile = FinancialProfile(
            savings_rate=(req.savings / req.income * 100.0) if req.income > 0 else 0.0,
            debt_ratio=(req.debt / req.income * 100.0) if req.income > 0 else 0.0,
            spending_consistency=75.0,
            emergency_fund_months=3
        )
        score_res = calculate_weighted_health_score(mock_profile)
        
        return {
            "risk_level": prediction["risk_level"],
            "confidence": prediction["confidence"],
            "financial_health_score": score_res["score"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk prediction model error: {str(e)}")

def sync_budget_spent(user_id: str, category: str, db: Session):
    """Recalculate and update the spent field in the user's budget for a specific category for the current calendar month."""
    budget = db.query(Budget).filter(Budget.user_id == user_id, Budget.category == category).first()
    if budget:
        today = datetime.date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        start_date = datetime.date(today.year, today.month, 1)
        end_date = datetime.date(today.year, today.month, last_day)

        # Sum expenses in this category strictly within the current calendar month
        total_spent = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.type == "Expense",
            Transaction.category == category,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ).with_entities(Transaction.amount).all()
        
        budget.spent = round(sum(t[0] for t in total_spent), 2) if total_spent else 0.0
        db.commit()

@router.post("", response_model=TransactionResponse)
def create_transaction(
    trans_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = (trans_in.category or "").strip()
    if not cat:
        suggestion = categorization_engine.categorize(
            description=trans_in.description or "",
            tx_type=trans_in.type,
            amount=trans_in.amount,
        )
        cat = suggestion["suggested_category"]
        conf = suggestion["confidence"]
        auto_cat = cat
        is_rev = suggestion["is_reviewed"]
    else:
        conf = trans_in.category_confidence if trans_in.category_confidence is not None else 1.0
        auto_cat = trans_in.auto_category or cat
        is_rev = trans_in.is_reviewed if trans_in.is_reviewed is not None else True

    db_trans = Transaction(
        user_id=current_user.id,
        type=trans_in.type,
        category=cat,
        category_confidence=conf,
        auto_category=auto_cat,
        is_reviewed=is_rev,
        amount=trans_in.amount,
        description=trans_in.description,
        transaction_date=trans_in.transaction_date,
        payment_method=trans_in.payment_method
    )
    db.add(db_trans)
    db.commit()
    db.refresh(db_trans)
    
    # Sync budget spent if it's an expense
    if trans_in.type == "Expense":
        sync_budget_spent(current_user.id, trans_in.category, db)
        
    check_and_trigger_notifications(db, current_user.id)
    return db_trans

@router.get("/search", response_model=List[TransactionResponse])
def search_transactions(
    q: str = Query(..., description="Search query string"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    query = query.filter(
        or_(
            Transaction.description.ilike(f"%{q}%"),
            Transaction.category.ilike(f"%{q}%")
        )
    )
    return query.order_by(Transaction.transaction_date.desc()).all()

@router.get("", response_model=List[TransactionResponse])
def get_transactions(
    month: Optional[str] = Query(None, description="Format: YYYY-MM"),
    category: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    
    if type:
        query = query.filter(Transaction.type == type)
    if category:
        query = query.filter(Transaction.category == category)
    if month:
        try:
            year_val, month_val = map(int, month.split("-"))
            _, last_day = calendar.monthrange(year_val, month_val)
            start_date = datetime.date(year_val, month_val, 1)
            end_date = datetime.date(year_val, month_val, last_day)
            query = query.filter(Transaction.transaction_date >= start_date, Transaction.transaction_date <= end_date)
        except Exception:
            pass

    return query.order_by(Transaction.transaction_date.desc()).all()

def is_transaction_duplicate(db: Session, user_id: str, tx_date, amount: float, tx_type: str, description: str) -> bool:
    """Check if an identical transaction already exists in the database for this user."""
    normalized_desc = (description or "").strip().lower()
    matches = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_date == tx_date,
        Transaction.type == tx_type,
        Transaction.amount == amount,
    ).all()
    for m in matches:
        if (m.description or "").strip().lower() == normalized_desc:
            return True
    return False

@router.post("/auto-categorize", response_model=CategorizeResponse)
def auto_categorize_single(
    req: CategorizeRequest,
    current_user: User = Depends(get_current_user)
):
    """Suggest category and confidence for an individual transaction description."""
    res = categorization_engine.categorize(
        description=req.description,
        tx_type=req.type,
        amount=req.amount or 0.0,
    )
    return CategorizeResponse(
        suggested_category=res["suggested_category"],
        confidence=res["confidence"],
        explanation=res["explanation"],
        is_reviewed=res["is_reviewed"],
    )

@router.post("/parse-csv", response_model=ParseCsvResponse)
async def parse_csv_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse bank statement or CSV file and return reviewable transactions with auto-categorization and duplicate detection."""
    try:
        content = (await file.read()).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid text file encoding")

    parsed = parse_transactions_csv(content)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="No valid transactions found in CSV. Expected headers such as Date, Description, Amount/Debit/Credit."
        )

    items = []
    seen_in_batch = set()
    duplicates_count = 0
    needs_review_count = 0

    import uuid
    for idx, item in enumerate(parsed):
        desc_norm = (item["description"] or "").strip().lower()
        batch_key = (item["transaction_date"], item["amount"], item["type"], desc_norm)

        is_dup = False
        dup_reason = None

        if batch_key in seen_in_batch:
            is_dup = True
            dup_reason = "Duplicate row within the uploaded statement."
        elif is_transaction_duplicate(db, current_user.id, item["transaction_date"], item["amount"], item["type"], item["description"]):
            is_dup = True
            dup_reason = f"Identical transaction already exists on {item['transaction_date']} ({item['amount']})."

        seen_in_batch.add(batch_key)
        if is_dup:
            duplicates_count += 1

        if item.get("category") == "Needs Review" or item.get("category_confidence", 1.0) < 0.70:
            needs_review_count += 1

        items.append(ParseCsvItem(
            temp_id=f"txn_{idx}_{uuid.uuid4().hex[:6]}",
            transaction_date=item["transaction_date"],
            type=item["type"],
            amount=item["amount"],
            description=item.get("description", ""),
            category=item["category"],
            suggested_category=item.get("suggested_category", item["category"]),
            category_confidence=item.get("category_confidence", 1.0),
            explanation=item.get("explanation", "Parsed from statement"),
            is_reviewed=item.get("is_reviewed", True),
            payment_method=item.get("payment_method", "Bank Transfer"),
            is_duplicate=is_dup,
            duplicate_reason=dup_reason,
        ))

    return ParseCsvResponse(
        items=items,
        total_parsed=len(items),
        duplicates_count=duplicates_count,
        needs_review_count=needs_review_count,
    )

@router.post("/confirm-import")
def confirm_import(
    req: ConfirmImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import reviewed transactions into the user's account."""
    if not req.transactions:
        raise HTTPException(status_code=400, detail="No transactions provided for import.")

    imported_count = 0
    skipped_duplicates = 0
    affected_expense_categories = set()
    seen_in_batch = set()

    for item in req.transactions:
        desc_norm = (item.description or "").strip().lower()
        batch_key = (item.transaction_date, item.amount, item.type, desc_norm)

        if req.skip_duplicates:
            if batch_key in seen_in_batch or is_transaction_duplicate(db, current_user.id, item.transaction_date, item.amount, item.type, item.description):
                skipped_duplicates += 1
                continue
        seen_in_batch.add(batch_key)

        category_clean = normalize_category_name(item.category)
        tx = Transaction(
            user_id=current_user.id,
            type=item.type,
            category=category_clean,
            category_confidence=item.category_confidence if item.category_confidence is not None else 1.0,
            auto_category=category_clean,
            is_reviewed=item.is_reviewed if item.is_reviewed is not None else True,
            amount=item.amount,
            description=item.description,
            transaction_date=item.transaction_date,
            payment_method=item.payment_method or "Bank Transfer",
        )
        db.add(tx)
        imported_count += 1
        if item.type == "Expense":
            affected_expense_categories.add(category_clean)

    db.commit()

    # Sync budgets for all affected expense categories
    for cat in affected_expense_categories:
        sync_budget_spent(current_user.id, cat, db)

    # Trigger notifications & audit log
    check_and_trigger_notifications(db, current_user.id)
    log_audit_event(
        db, current_user.id, "CSV_IMPORT_CONFIRMED",
        f"Imported {imported_count} reviewed transactions ({skipped_duplicates} duplicates skipped)."
    )

    return {
        "status": "success",
        "imported": imported_count,
        "imported_count": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "skipped_duplicates_count": skipped_duplicates,
        "message": f"Successfully imported {imported_count} transactions ({skipped_duplicates} duplicates skipped)."
    }

@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import transactions from a CSV or bank statement file with auto-categorization and deduplication."""
    try:
        content = (await file.read()).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid text file encoding")
        
    parsed = parse_transactions_csv(content)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="No valid transactions found in CSV. Expected headers: Date, Category, Type, Amount, Description, Payment Method"
        )
        
    imported_count = 0
    skipped_duplicates = 0
    affected_expense_categories = set()
    seen_in_batch = set()

    for item in parsed:
        desc_norm = (item["description"] or "").strip().lower()
        batch_key = (item["transaction_date"], item["amount"], item["type"], desc_norm)

        # Check for duplicates in the current statement or database
        if batch_key in seen_in_batch or is_transaction_duplicate(db, current_user.id, item["transaction_date"], item["amount"], item["type"], item["description"]):
            skipped_duplicates += 1
            continue
        seen_in_batch.add(batch_key)

        category_clean = normalize_category_name(item["category"])
        tx = Transaction(
            user_id=current_user.id,
            type=item["type"],
            category=category_clean,
            category_confidence=item.get("category_confidence", 1.0),
            auto_category=item.get("suggested_category", category_clean),
            is_reviewed=item.get("is_reviewed", True),
            amount=item["amount"],
            description=item["description"],
            transaction_date=item["transaction_date"],
            payment_method=item["payment_method"]
        )
        db.add(tx)
        imported_count += 1
        if item["type"] == "Expense":
            affected_expense_categories.add(category_clean)
        
    db.commit()
    
    # Sync budget spent for newly imported expenses
    for cat in affected_expense_categories:
        sync_budget_spent(current_user.id, cat, db)
            
    # Check trigger rules
    check_and_trigger_notifications(db, current_user.id)
    
    log_audit_event(
        db, current_user.id, "CSV_IMPORT",
        f"Successfully imported {imported_count} transactions ({skipped_duplicates} duplicates skipped)."
    )
    return {
        "status": "success",
        "imported": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "message": f"Successfully imported {imported_count} transactions ({skipped_duplicates} duplicates skipped)."
    }

@router.get("/export-csv")
def export_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export transactions to a CSV file."""
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.transaction_date.desc()).all()
    csv_str = generate_transactions_csv(transactions)
    
    output = io.BytesIO(csv_str.encode("utf-8"))
    filename = f"transactions_{current_user.full_name.lower().replace(' ', '_')}_{datetime.date.today().isoformat()}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export-pdf")
def export_transactions_pdf(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export transactions list to a PDF document."""
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.transaction_date.desc()).all()
    
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TableTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=15
    )
    
    elements = [
        Paragraph(f"Transactions Ledger Statement - {current_user.full_name}", title_style),
        Paragraph(f"Exported Date: {datetime.date.today().isoformat()} &nbsp;|&nbsp; Currency: {current_user.currency}", styles["Normal"]),
        Spacer(1, 15)
    ]
    
    tx_headers = ["Date", "Category", "Type", "Amount", "Method", "Description"]
    tx_rows = [tx_headers]
    
    symbol = "₹"
    if current_user.currency == "USD":
        symbol = "$"
    elif current_user.currency == "EUR":
        symbol = "€"
    elif current_user.currency == "GBP":
        symbol = "£"
        
    for tx in transactions:
        tx_rows.append([
            tx.transaction_date.strftime("%Y-%m-%d"),
            tx.category,
            tx.type,
            f"{symbol}{tx.amount:,.2f}",
            tx.payment_method,
            tx.description or ""
        ])
        
    # If empty
    if len(tx_rows) == 1:
        tx_rows.append(["No records found", "", "", "", "", ""])
        
    tx_table = Table(tx_rows, colWidths=[70, 90, 60, 90, 90, 150])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(tx_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"transactions_{current_user.full_name.lower().replace(' ', '_')}_{datetime.date.today().isoformat()}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{trans_id}", response_model=TransactionResponse)
def get_transaction(
    trans_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trans = db.query(Transaction).filter(Transaction.id == trans_id, Transaction.user_id == current_user.id).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return trans

@router.put("/{trans_id}", response_model=TransactionResponse)
def update_transaction(
    trans_id: str,
    trans_in: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trans = db.query(Transaction).filter(Transaction.id == trans_id, Transaction.user_id == current_user.id).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    old_category = trans.category
    old_type = trans.type
    
    update_data = trans_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trans, field, value)
        
    db.commit()
    db.refresh(trans)
    
    # Sync budget spent for both the old and new categories/types
    if old_type == "Expense":
        sync_budget_spent(current_user.id, old_category, db)
    if trans.type == "Expense":
        sync_budget_spent(current_user.id, trans.category, db)
        
    check_and_trigger_notifications(db, current_user.id)
    return trans

@router.delete("/{trans_id}")
def delete_transaction(
    trans_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trans = db.query(Transaction).filter(Transaction.id == trans_id, Transaction.user_id == current_user.id).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    category = trans.category
    type = trans.type
    
    db.delete(trans)
    db.commit()
    
    # Sync budget spent if it was an expense
    if type == "Expense":
        sync_budget_spent(current_user.id, category, db)
        
    check_and_trigger_notifications(db, current_user.id)
    return {"status": "success", "message": "Transaction deleted successfully"}
