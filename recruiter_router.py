# recruiter_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.recruiter_repo import update_recruiter_decision, update_recruiter_decision_with_jd_text

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])


# -------------------------------------------------
# REQUEST MODEL
# -------------------------------------------------
class RecruiterDecisionRequest(BaseModel):
    cache_key: str
    decision: str  # 'hired' | 'rejected'


# -------------------------------------------------
# ENDPOINT
# -------------------------------------------------
@router.post("/decision")
async def recruiter_decision(payload: RecruiterDecisionRequest):

    try:
        result = await update_recruiter_decision(
            cache_key=payload.cache_key,
            decision=payload.decision.lower()
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

class RecruiterDecisionJDTextRequest(BaseModel):
    student_id: str
    jd_text: str
    decision: str


@router.post("/decision-by-jd-text")
async def recruiter_decision_jd_text(req: RecruiterDecisionJDTextRequest):

    try:
        result = await update_recruiter_decision_with_jd_text(
            req.student_id,
            req.jd_text,
            req.decision.lower()
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))