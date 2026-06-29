from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import CurrentUser, get_db
from app.models.export_report import ExportReport, ReportType, ExportFormat
from app.services.export_engine import export_to_pdf, export_to_docx, export_to_pptx

router = APIRouter()

class ExportRequest(BaseModel):
    report_type: ReportType
    format: ExportFormat
    content: str  # In a real app, this might be a report ID, and we fetch content from DB.

@router.post("/report")
async def export_report(
    request: ExportRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
):
    filename = f"{request.report_type.value}_{uuid.uuid4().hex[:8]}"
    
    if request.format == ExportFormat.pdf:
        filepath = export_to_pdf(request.content, filename)
    elif request.format == ExportFormat.docx:
        filepath = export_to_docx(request.content, filename)
    elif request.format == ExportFormat.pptx:
        filepath = export_to_pptx(request.content, filename)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
        
    # Save record
    er = ExportReport(
        user_id=current_user.id,
        report_type=request.report_type,
        format=request.format,
        file_path=filepath
    )
    session.add(er)
    await session.commit()
    
    return FileResponse(
        path=filepath, 
        filename=os.path.basename(filepath), 
        media_type='application/octet-stream'
    )
