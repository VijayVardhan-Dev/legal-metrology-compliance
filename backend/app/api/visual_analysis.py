from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.visual_analysis import VisualAnalysisRequest, VisualAnalysisResponse
from app.services.visual_analysis_service import VisualAnalysisService

router = APIRouter()


@router.post("/{inspection_id}/visual-analysis", response_model=VisualAnalysisResponse)
def analyze_visuals(inspection_id: str, request: VisualAnalysisRequest | None = None,
                    db: Session = Depends(get_db)):
    try:
        return VisualAnalysisService(db).analyze(inspection_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{inspection_id}/visual-analysis", response_model=VisualAnalysisResponse)
def get_visual_analysis(inspection_id: str, db: Session = Depends(get_db)):
    result = VisualAnalysisService(db).get(inspection_id)
    if not result:
        raise HTTPException(status_code=404, detail="Visual analysis not found")
    return result
