import io, os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape as x
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts")
try:   # Poppins if the .ttf files exist, otherwise fall back to built-in Helvetica
    pdfmetrics.registerFont(TTFont("Poppins", os.path.join(FONT_DIR, "Poppins-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Poppins-Bold", os.path.join(FONT_DIR, "Poppins-Bold.ttf")))
    pdfmetrics.registerFontFamily("Poppins", normal="Poppins", bold="Poppins-Bold", italic="Poppins", boldItalic="Poppins-Bold")
    REG, BOLD = "Poppins", "Poppins-Bold"
except Exception:
    REG, BOLD = "Helvetica", "Helvetica-Bold"

def build_pdf(d) -> bytes:
    """PDFGenerator.buildPdf(resume): byte[] (class diagram)."""
    buf = io.BytesIO(); base = getSampleStyleSheet()["Normal"]
    S = lambda n, **k: ParagraphStyle(n, parent=base, **{"fontName": REG, **k})
    name, sub = S("n", fontSize=22, leading=26, textColor=colors.HexColor("#1e3a8a"), fontName=BOLD), S("s", fontSize=9.5, textColor=colors.grey)
    h, b = S("h", fontSize=11.5, fontName=BOLD, spaceBefore=10, textColor=colors.HexColor("#1e3a8a")), S("b", fontSize=10, leading=14)
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm, title=d["title"])
    contact = " | ".join(x(v) for v in (d["email"], d["phone"], d["address"] or "", d["linkedin"] or "") if v)
    el = [Paragraph(x(d["name"]), name), Paragraph(contact, sub)]
    def sec(t):
        el.extend([Paragraph(t.upper(), h), HRFlowable(width="100%", color=colors.HexColor("#cbd5e1"), spaceAfter=4)])
    sec("Career Objective"); el.append(Paragraph(x(d["objective"]), b))
    if d["education"]:
        sec("Education")
        for e in d["education"]:
            el.append(Paragraph(f"<b>{x(e['degree'])}</b> - {x(e['institution'])} ({e['graduation_year'] if 'graduation_year' in e else e['year']})", b))
            if e["result"]: el.append(Paragraph(x(e["result"]), sub))
    if d["experience"]:
        sec("Professional Experience")
        for e in d["experience"]:
            el.append(Paragraph(f"<b>{x(e['job_title'])}</b>, {x(e['company'])} <font color='grey'>({x(e['duration'])})</font>", b))
            if e["responsibilities"]: el.append(Paragraph(x(e["responsibilities"]), b))
            el.append(Spacer(1, 3))
    labels = {"technical": "Technical Skills", "soft": "Soft Skills", "language": "Languages", "certification": "Certifications", "other": "Other"}
    if any(d["skills"].values()):
        sec("Skills & Additional Information")
        for k, v in d["skills"].items():
            if v: el.append(Paragraph(f"<b>{labels[k]}:</b> {x(', '.join(v))}", b))
    doc.build(el); return buf.getvalue()
