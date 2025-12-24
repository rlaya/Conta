# utils/pdf.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

def exportar_facturas_a_pdf(facturas):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Reporte de Facturas - Sistema Contable", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Datos
    data = [["ID", "Tipo", "Folio", "Fecha", "Tercero", "Total", "Estatus", "Asiento"]]
    for f in facturas:
        data.append([
            str(f[0]),
            f[1],
            f[2],
            str(f[3]),
            f[4] or "",
            f"${f[5]:,.2f}",
            f[6],
            str(f[7]) if f[7] else ""
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def exportar_factura_individual_a_pdf(factura):
    """
    Genera un PDF con los detalles de una sola factura.
    Asume que 'factura' es un diccionario con las claves:
    'tipo', 'folio', 'fecha', 'fecha_vencimiento', 'tercero_nombre', 'total', 'estatus', 'id_asiento'.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            leftMargin=72, rightMargin=72, 
                            topMargin=50, bottomMargin=50)
    elements = []

    styles = getSampleStyleSheet()
    
    # --- Encabezado ---
    titulo_texto = f"FACTURA DE {factura['tipo'].upper()}"
    tipo_color = colors.green if factura['tipo'] == 'venta' else colors.red
    
    # Título y datos principales
    elements.append(Paragraph(titulo_texto, styles['h1']))
    elements.append(Spacer(1, 18))
    
    # Detalle de la factura y tercero
    data_header = [
        ['FOLIO:', factura['folio'], 'ESTATUS:', factura['estatus'].upper()],
        ['FECHA:', str(factura['fecha']), 'VENCIMIENTO:', str(factura['fecha_vencimiento']) if factura['fecha_vencimiento'] else 'N/A'],
        ['TERCERO:', factura['tercero_nombre'] or "N/A", 'ASIENTO ID:', str(factura['id_asiento']) if factura['id_asiento'] else 'N/A']
    ]

    table_header = Table(data_header, colWidths=[1.5*72, 3*72, 1.5*72, 3*72])
    table_header.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
    ]))
    elements.append(table_header)
    elements.append(Spacer(1, 24))

    # --- Total ---
    total_data = [
        ['', 'TOTAL A PAGAR/RECIBIR'],
        ['', f"${factura['total']:,.2f}"]
    ]
    
    total_table = Table(total_data, colWidths=[5.5*72, 3*72])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 10),
        ('FONTSIZE', (1, 1), (1, 1), 16),
        ('ALIGN', (1, 0), (1, 1), 'RIGHT'),
        ('TEXTCOLOR', (1, 0), (1, 1), tipo_color),
        ('GRID', (1, 0), (1, 1), 1, colors.black),
    ]))
    
    elements.append(total_table)
    elements.append(Spacer(1, 36))

    # Pie de página simple
    elements.append(Paragraph("Documento generado por el Sistema Contable.", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return buffer   