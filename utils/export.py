# utils/export.py
from openpyxl import Workbook
from io import BytesIO

def exportar_facturas_a_excel(facturas):
    wb = Workbook()
    ws = wb.active
    ws.title = "Facturas"

    # Encabezados
    headers = ["ID", "Tipo", "Folio", "Fecha", "Tercero", "Total", "Estatus", "Asiento"]
    ws.append(headers)

    # Datos
    for f in facturas:
        ws.append([
            f[0], f[1], f[2], str(f[3]), f[4] or "", 
            f[5], f[6], f[7] or ""
        ])

    # Ajustar ancho
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width

    # Guardar en memoria
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output