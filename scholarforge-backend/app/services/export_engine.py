import os
import uuid
from datetime import datetime
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pptx import Presentation

from app.core.config import settings

def get_export_dir():
    export_dir = os.path.join(settings.UPLOAD_DIR, "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir

def export_to_pdf(content: str, filename: str) -> str:
    filepath = os.path.join(get_export_dir(), f"{filename}.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Very basic PDF generation
    textobject = c.beginText()
    textobject.setTextOrigin(40, height - 40)
    textobject.setFont("Helvetica", 10)
    
    lines = content.split('\n')
    for line in lines:
        # Simple wrapping
        while len(line) > 100:
            textobject.textLine(line[:100])
            line = line[100:]
        textobject.textLine(line)
        
    c.drawText(textobject)
    c.save()
    return filepath

def export_to_docx(content: str, filename: str) -> str:
    filepath = os.path.join(get_export_dir(), f"{filename}.docx")
    document = Document()
    document.add_heading('ScholarForge AI Report', 0)
    
    for line in content.split('\n'):
        if line.strip():
            document.add_paragraph(line)
            
    document.save(filepath)
    return filepath

def export_to_pptx(content: str, filename: str) -> str:
    filepath = os.path.join(get_export_dir(), f"{filename}.pptx")
    prs = Presentation()
    
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "ScholarForge AI Report"
    subtitle.text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
    
    bullet_slide_layout = prs.slide_layouts[1]
    
    # Group lines by ~5 per slide
    lines = [l for l in content.split('\n') if l.strip()]
    
    for i in range(0, len(lines), 5):
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        
        title_shape.text = "Report Content"
        tf = body_shape.text_frame
        
        for j, line in enumerate(lines[i:i+5]):
            if j == 0:
                tf.text = line
            else:
                p = tf.add_paragraph()
                p.text = line
                
    prs.save(filepath)
    return filepath
