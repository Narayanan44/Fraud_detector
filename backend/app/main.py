import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Transaction
from .risk_engine import calculate_risk

Base.metadata.create_all(bind=engine)   # create the table if it does not exist

app = FastAPI(title="Fraud / Anomaly Detection Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAMPLE_FILE = Path(__file__).parent.parent / "sample_data" / "transactions.csv"
HISTORY_DAYS = 30   # we only look at the last 30 days of a customer's payments


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- input checking ----------------
class TransactionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)   # "  U1 " becomes "U1"

    user_id: str = Field(min_length=1)
    amount: float = Field(gt=0, allow_inf_nan=False)       # 0, negative, inf, nan are rejected
    location: Optional[str] = None
    status: Literal["success", "failed"] = "success"
    time: Optional[datetime] = None                        # if missing we use the current time


# ---------------- helper: database row -> JSON for the frontend ----------------
def row_to_json(row):
    return {
        "id": row.id,
        "user_id": row.user_id,
        "amount": row.amount,
        "location": row.location,
        "status": row.status,
        "time": row.time.isoformat(),
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "reasons": json.loads(row.reasons),
    }


# ---------------- main function: history -> score -> save ----------------
def save_transaction(db: Session, data: dict, commit_now: bool = True):
    # 1. time: use now if missing, and remove the timezone so all times are comparable
    time = data["time"] or datetime.now()
    time = time.replace(tzinfo=None)
    data["time"] = time

    # 2. this customer's earlier payments (last 30 days, up to this payment's time)
    old_rows = db.query(Transaction).filter(
        Transaction.user_id == data["user_id"],
        Transaction.time >= time - timedelta(days=HISTORY_DAYS),
        Transaction.time <= time,
    ).all()
    history = [{"amount": r.amount, "time": r.time, "location": r.location, "status": r.status}
               for r in old_rows]

    # 3. ask the risk engine
    result = calculate_risk(data, history)

    # 4. save the payment together with its score and reasons
    row = Transaction(
        user_id=data["user_id"],
        amount=data["amount"],
        location=data["location"],
        status=data["status"],
        time=time,
        risk_score=result["score"],
        risk_level=result["level"],
        reasons=json.dumps(result["reasons"]),
    )
    db.add(row)
    if commit_now:
        db.commit()
        db.refresh(row)
    else:
        db.flush()   # next query can see it, but it is saved for good only when we commit
    return row


# ---------------- API ----------------
@app.get("/")
def home():
    return {"message": "Fraud detection API is running"}


@app.post("/transactions")
def add_transaction(item: TransactionIn, db: Session = Depends(get_db)):
    row = save_transaction(db, item.model_dump())
    return row_to_json(row)


@app.get("/transactions")
def list_transactions(level: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if level:
        query = query.filter(Transaction.risk_level == level.upper())
    rows = query.order_by(Transaction.time.desc(), Transaction.id.desc()).all()
    return [row_to_json(r) for r in rows]


@app.post("/load-sample")
def load_sample(db: Session = Depends(get_db)):
    """Load sample_data/transactions.csv, oldest payment first so history builds in the right order."""
    with open(SAMPLE_FILE) as f:
        lines = list(csv.DictReader(f))
    lines.sort(key=lambda line: line["time"])

    for line in lines:
        save_transaction(db, {
            "user_id": line["user_id"],
            "amount": float(line["amount"]),
            "location": line["location"],
            "status": line["status"],
            "time": datetime.fromisoformat(line["time"]),
        }, commit_now=False)
    db.commit()   # one commit at the end is much faster than one per row
    return {"loaded": len(lines)}


@app.delete("/transactions")
def delete_all(db: Session = Depends(get_db)):
    deleted = db.query(Transaction).delete()
    db.commit()
    return {"deleted": deleted}
