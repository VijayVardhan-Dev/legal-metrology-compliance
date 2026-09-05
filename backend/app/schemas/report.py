from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    id: str
    report_id: str
    inspection_id: str
    report_number: str
    generated_at: datetime
    report_status: str
    overall_compliance_status: str
    overall_confidence: float | None = None
    compliance_run_id: str | None = None
    rule_engine_version: str | None = None
    classification_version: str | None = None
    ocr_result_id: str | None = None
    visual_analysis_id: str | None = None
    report_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, report):
        return cls.model_validate({**report.__dict__, "report_id": report.id, "generated_at": report.created_at})