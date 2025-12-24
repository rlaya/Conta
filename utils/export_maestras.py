# D:\Python\Conta\utils\export_maestras.py

import pandas as pd
from io import BytesIO
from fpdf import FPDF

def exportar_a_excel(datos, nombre_tabla):
    if nombre_tabla == 'clientes':
        columnas = ['ID', 'Nombre', 'Email', 'CUIT', 'Domicilio']
    elif nombre_tabla == 'proveedores':
        columnas = ['ID', 'Nombre', 'Email', 'CUIT', 'Domicilio']
    elif nombre_tabla == 'plan_cuentas':
        columnas = ['ID', 'Código', 'Nombre', 'Tipo']
    elif nombre_tabla == 'cuentas_bancarias':
        columnas = ['ID', 'Banco', 'Nro Cuenta', 'CBU', 'Alias']
    elif nombre_tabla == 'Usuarios':
        columnas = ['ID', 'Nombre', 'Email', 'Rol ID']
    elif nombre_tabla == 'Tasa_iva':
        columnas = ['ID', 'Descripción', 'Porcentaje (%)']
    else:
        columnas = [f'Col_{i}' for i in range(len(datos[0]) if datos else 5)]

    df = pd.DataFrame(datos, columns=columnas)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_tabla)
    output.seek(0)
    return output

def exportar_a_pdf(datos, nombre_tabla):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, f'Listado de {nombre_tabla}', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=9)

    if nombre_tabla == 'clientes':
        columnas = ['ID', 'Nombre', 'Email', 'CUIT', 'Domicilio']
    elif nombre_tabla == 'proveedores':
        columnas = ['ID', 'Nombre', 'Email', 'CUIT', 'Domicilio']
    elif nombre_tabla == 'plan_cuentas':
        columnas = ['ID', 'Código', 'Nombre', 'Tipo']
    elif nombre_tabla == 'cuentas_bancarias':
        columnas = ['ID', 'Banco', 'Nro Cuenta', 'CBU', 'Alias']
    elif nombre_tabla == 'Usuarios':
        columnas = ['ID', 'Nombre', 'Email', 'Rol']
    elif nombre_tabla == 'Tasa_iva':
        columnas = ['ID', 'Descripción', 'Porcentaje']
    else:
        columnas = [f'Col_{i}' for i in range(len(datos[0]) if datos else 5)]

    col_width = 190 / len(columnas)
    row_height = 8

    # Encabezados
    for col in columnas:
        pdf.cell(col_width, row_height, col, border=1, align='C')
    pdf.ln()

    # Filas
    for row in datos:
        for item in row:
            pdf.cell(col_width, row_height, str(item) if item is not None else "", border=1)
        pdf.ln()

    return BytesIO(pdf.output(dest='S').encode('latin1'))