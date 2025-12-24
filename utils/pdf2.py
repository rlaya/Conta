# utils/pdf2.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

def exportar_asientos_a_pdf(asientos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Listado de Asientos Contables", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Datos
    data = [["ID", "Fecha", "Diario", "Concepto", "Ref.", "Creador", "Cliente", "Proveedor"]]
    for a in asientos:
        data.append([
            str(a[0]),
            a[1].strftime('%Y-%m-%d'),
            a[4],
            a[2][:50] + "..." if len(a[2]) > 50 else a[2],
            a[3] or '',
            a[5],
            a[6] or '',
            a[7] or ''
        ])

    # Tabla
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer