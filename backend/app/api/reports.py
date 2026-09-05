from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/{inspection_id}/report", response_model=ReportResponse)
def generate_report(inspection_id: str, db: Session = Depends(get_db)):
    return ReportService(db).generate(inspection_id)


@router.get("/{inspection_id}/report", response_model=ReportResponse)
def get_report(inspection_id: str, db: Session = Depends(get_db)):
    return ReportService(db).latest(inspection_id)


@router.get("/{inspection_id}/report/download")
def download_report(inspection_id: str, db: Session = Depends(get_db)):
    report = ReportService(db).report_model(inspection_id)
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=f"{report.report_number}.pdf",
    )
