from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.models import Dataset, Record, User
from app.infrastructure.db import get_db

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    datasets = db.query(Dataset).all()
    items = []
    totals = {"records": 0, "duplicates": 0, "invalid": 0}
    for d in datasets:
        q = d.data_quality or {}
        recs = d.record_count or 0
        dups = q.get("duplicates") or 0
        items.append(
            {
                "id": str(d.id),
                "name": d.name,
                "records": recs,
                "status": d.processing_status,
                "classification": d.legal_classification,
                "quality": q,
            }
        )
        totals["records"] += recs
        totals["duplicates"] += dups
    dup_records = db.query(Record).filter(Record.duplicate_of.isnot(None)).count()
    totals["duplicates"] = max(totals["duplicates"], dup_records)
    return {"totals": totals, "datasets": items}
