import pandas as pd
from io import BytesIO
import xlsxwriter
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def exportar_balance_general_excel(datos, fecha):
    """Exportar Balance General a Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        subheader_format = workbook.add_format({
            'bold': True,
            'bg_color': '#C5D9F1',
            'border': 1,
            'font_size': 11
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        money_bold_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bold': True,
            'border': 1,
            'bg_color': '#E6E6E6'
        })
        
        # Hoja de Balance General
        worksheet = workbook.add_worksheet('Balance General')
        worksheet.set_landscape()
        
        # Título
        worksheet.merge_range('A1:H1', f'BALANCE GENERAL AL {fecha}', title_format)
        worksheet.merge_range('A2:H2', 'SISTEMA CONTAB - CONTABILIDAD INTEGRAL', header_format)
        
        # Encabezados Activo
        worksheet.write('A4', 'CÓDIGO', header_format)
        worksheet.write('B4', 'CUENTA', header_format)
        worksheet.write('C4', 'SALDO', header_format)
        worksheet.write('E4', 'CÓDIGO', header_format)
        worksheet.write('F4', 'CUENTA', header_format)
        worksheet.write('G4', 'SALDO', header_format)
        
        # Activo
        row = 5
        total_activo = Decimal('0')
        
        for cuenta in datos['cuentas']:
            if cuenta[0].startswith('1'):  # Activo
                nivel = cuenta[3]
                indent = '  ' * (nivel - 1)
                
                worksheet.write(row, 0, cuenta[0])
                worksheet.write(row, 1, indent + cuenta[1])
                if cuenta[7]:  # saldo_final
                    worksheet.write_number(row, 2, float(cuenta[7]), money_format)
                    total_activo += Decimal(str(cuenta[7]))
                row += 1
        
        # Total Activo
        worksheet.write(row, 1, 'TOTAL ACTIVO', subheader_format)
        worksheet.write_number(row, 2, float(total_activo), money_bold_format)
        
        # Pasivo y Capital (columna derecha)
        row_right = 5
        total_pasivo = Decimal('0')
        total_capital = Decimal('0')
        
        for cuenta in datos['cuentas']:
            if cuenta[0].startswith('2') or cuenta[0].startswith('3'):
                nivel = cuenta[3]
                indent = '  ' * (nivel - 1)
                
                worksheet.write(row_right, 4, cuenta[0])
                worksheet.write(row_right, 5, indent + cuenta[1])
                if cuenta[7]:  # saldo_final
                    saldo = Decimal(str(cuenta[7]))
                    worksheet.write_number(row_right, 6, float(saldo), money_format)
                    
                    if cuenta[0].startswith('2'):
                        total_pasivo += saldo
                    else:
                        total_capital += saldo
                row_right += 1
        
        # Totales Pasivo y Capital
        max_row = max(row, row_right)
        
        worksheet.write(max_row, 5, 'TOTAL PASIVO', subheader_format)
        worksheet.write_number(max_row, 6, float(total_pasivo), money_bold_format)
        
        worksheet.write(max_row + 1, 5, 'TOTAL CAPITAL', subheader_format)
        worksheet.write_number(max_row + 1, 6, float(total_capital), money_bold_format)
        
        worksheet.write(max_row + 2, 5, 'TOTAL PASIVO + CAPITAL', subheader_format)
        worksheet.write_number(max_row + 2, 6, float(total_pasivo + total_capital), money_bold_format)
        
        # Validación
        diferencia = total_activo - (total_pasivo + total_capital)
        validacion = "CUADRADO" if diferencia == 0 else f"DESCUADRADO: ${diferencia:,.2f}"
        
        worksheet.write(max_row + 4, 0, 'VALIDACIÓN:', subheader_format)
        worksheet.merge_range(max_row + 4, 1, max_row + 4, 2, validacion, 
                            money_bold_format)
        
        # Ajustar anchos de columna
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 40)
        worksheet.set_column('G:G', 15)
        
        # Congelar paneles
        worksheet.freeze_panes(4, 0)
        
        # Hoja de Resumen
        worksheet2 = workbook.add_worksheet('Resumen')
        
        # Datos para gráfico
        data = [
            ['ACTIVO', float(total_activo)],
            ['PASIVO', float(total_pasivo)],
            ['CAPITAL', float(total_capital)]
        ]
        
        df = pd.DataFrame(data, columns=['Concepto', 'Monto'])
        df.to_excel(writer, sheet_name='Resumen', startrow=0, index=False)
        
        # Crear gráfico
        chart = workbook.add_chart({'type': 'pie'})
        chart.add_series({
            'name': 'Composición',
            'categories': '=Resumen!$A$2:$A$4',
            'values': '=Resumen!$B$2:$B$4',
        })
        chart.set_title({'name': 'Composición del Balance'})
        worksheet2.insert_chart('D2', chart)
    
    output.seek(0)
    return output

def exportar_estado_resultados_excel(datos, fecha_inicio, fecha_fin):
    """Exportar Estado de Resultados a Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        subheader_format = workbook.add_format({
            'bold': True,
            'bg_color': '#C5D9F1',
            'border': 1,
            'font_size': 12
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        money_bold_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bold': True,
            'border': 1,
            'bg_color': '#F2F2F2'
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.0%',
            'border': 1
        })
        
        # Hoja principal
        worksheet = workbook.add_worksheet('Estado Resultados')
        
        # Título
        worksheet.merge_range('A1:E1', 'ESTADO DE RESULTADOS', title_format)
        worksheet.merge_range('A2:E2', f'PERÍODO: {fecha_inicio} AL {fecha_fin}', header_format)
        
        # Encabezados
        headers = ['CÓDIGO', 'CONCEPTO', 'MONTO', '% INGRESOS', 'ACUMULADO']
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)
        
        # Datos
        row = 4
        
        # Ingresos
        worksheet.write(row, 1, 'INGRESOS', subheader_format)
        row += 1
        
        for ingreso in datos['ingresos']:
            worksheet.write(row, 0, ingreso[0])
            worksheet.write(row, 1, ingreso[1])
            worksheet.write_number(row, 2, float(ingreso[2]), money_format)
            
            if datos['total_ingresos'] > 0:
                porcentaje = float(ingreso[2]) / float(datos['total_ingresos'])
                worksheet.write_number(row, 3, porcentaje, percent_format)
            
            row += 1
        
        worksheet.write(row, 1, 'TOTAL INGRESOS', money_bold_format)
        worksheet.write_number(row, 2, float(datos['total_ingresos']), money_bold_format)
        worksheet.write_number(row, 3, 1.0, percent_format)
        row += 2
        
        # Costos
        worksheet.write(row, 1, 'COSTOS DE VENTA', subheader_format)
        row += 1
        
        for costo in datos['costos']:
            worksheet.write(row, 0, costo[0])
            worksheet.write(row, 1, costo[1])
            worksheet.write_number(row, 2, float(costo[2]), money_format)
            
            if datos['total_ingresos'] > 0:
                porcentaje = float(costo[2]) / float(datos['total_ingresos'])
                worksheet.write_number(row, 3, porcentaje, percent_format)
            
            row += 1
        
        worksheet.write(row, 1, 'TOTAL COSTOS', money_bold_format)
        worksheet.write_number(row, 2, float(datos['total_costos']), money_bold_format)
        
        if datos['total_ingresos'] > 0:
            porcentaje_costos = float(datos['total_costos']) / float(datos['total_ingresos'])
            worksheet.write_number(row, 3, porcentaje_costos, percent_format)
        
        row += 1
        
        # Utilidad Bruta
        utilidad_bruta = datos['utilidad_bruta']
        worksheet.write(row, 1, 'UTILIDAD BRUTA', money_bold_format)
        worksheet.write_number(row, 2, float(utilidad_bruta), money_bold_format)
        
        if datos['total_ingresos'] > 0:
            porcentaje_ub = float(utilidad_bruta) / float(datos['total_ingresos'])
            worksheet.write_number(row, 3, porcentaje_ub, percent_format)
        
        row += 2
        
        # Ajustar anchos
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 15)
        
        # Hoja de Análisis
        worksheet2 = workbook.add_worksheet('Análisis')
        
        # Datos para análisis
        analisis_data = [
            ['MARGEN BRUTO', float(datos['utilidad_bruta']), float(datos['total_ingresos'])],
            ['MARGEN OPERATIVO', float(datos['utilidad_operativa']), float(datos['total_ingresos'])],
            ['MARGEN NETO', float(datos['utilidad_neta']), float(datos['total_ingresos'])]
        ]
        
        df_analisis = pd.DataFrame(analisis_data, columns=['Concepto', 'Utilidad', 'Ingresos'])
        df_analisis.to_excel(writer, sheet_name='Análisis', startrow=0, index=False)
        
        # Gráfico de márgenes
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Margen %',
            'categories': '=Análisis!$A$2:$A$4',
            'values': '=Análisis!$D$2:$D$4',
            'data_labels': {'value': True, 'percentage': True}
        })
        chart.set_title({'name': 'Análisis de Márgenes'})
        worksheet2.insert_chart('F2', chart)
    
    output.seek(0)
    return output

def exportar_libro_diario_excel(datos, fecha_inicio, fecha_fin):
    """Exportar Libro Diario a Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        total_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bold': True,
            'border': 1,
            'bg_color': '#E6E6E6'
        })
        
        # Hoja principal
        worksheet = workbook.add_worksheet('Libro Diario')
        worksheet.set_landscape()
        
        # Título
        worksheet.merge_range('A1:H1', 'LIBRO DIARIO', title_format)
        worksheet.merge_range('A2:H2', f'PERÍODO: {fecha_inicio} AL {fecha_fin}', header_format)
        
        # Encabezados
        headers = ['FECHA', 'COMPROBANTE', 'CÓDIGO', 'CUENTA', 'CONCEPTO', 'DEBE', 'HABER', 'REFERENCIA']
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)
        
        # Datos
        row = 4
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        
        for asiento in datos['asientos']:
            worksheet.write_datetime(row, 0, asiento[0], date_format)
            worksheet.write(row, 1, asiento[1])
            worksheet.write(row, 2, asiento[3])
            worksheet.write(row, 3, asiento[4])
            worksheet.write(row, 4, asiento[2])
            
            if asiento[5]:  # Debe
                worksheet.write_number(row, 5, float(asiento[5]), money_format)
                total_debe += Decimal(str(asiento[5]))
            
            if asiento[6]:  # Haber
                worksheet.write_number(row, 6, float(asiento[6]), money_format)
                total_haber += Decimal(str(asiento[6]))
            
            worksheet.write(row, 7, asiento[7] or '')
            row += 1
        
        # Totales
        worksheet.write(row, 4, 'TOTALES:', total_format)
        worksheet.write_number(row, 5, float(total_debe), total_format)
        worksheet.write_number(row, 6, float(total_haber), total_format)
        
        # Validación
        diferencia = total_debe - total_haber
        validacion = "CUADRADO" if diferencia == 0 else f"DESCUADRADO: ${diferencia:,.2f}"
        
        worksheet.write(row + 1, 4, 'VALIDACIÓN:', total_format)
        worksheet.write(row + 1, 5, validacion, total_format)
        
        # Ajustar anchos
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 40)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 12)
        
        # Congelar paneles
        worksheet.freeze_panes(4, 0)
        
        # Hoja de Resumen por Día
        worksheet2 = workbook.add_worksheet('Resumen Diario')
        
        # Aquí iría el resumen por día calculado
        # Por ahora dejamos un placeholder
        worksheet2.write('A1', 'Resumen por día se generará con datos completos')
    
    output.seek(0)
    return output

def exportar_mayor_general_excel(datos, fecha_inicio, fecha_fin):
    """Exportar Mayor General a Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cuenta_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#C5D9F1',
            'border': 1,
            'font_size': 12
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        saldo_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bold': True,
            'border': 1
        })
        
        # Para cada cuenta, crear una hoja
        cuentas_unicas = set(mov[0] for mov in datos['movimientos'])
        
        for cuenta_codigo in cuentas_unicas:
            # Filtrar movimientos de esta cuenta
            movimientos_cuenta = [m for m in datos['movimientos'] if m[0] == cuenta_codigo]
            
            # Nombre de la hoja (limitado a 31 caracteres)
            nombre_cuenta = next((m[1] for m in movimientos_cuenta), 'Cuenta')
            nombre_hoja = f"{cuenta_codigo} {nombre_cuenta}"[:31]
            
            worksheet = workbook.add_worksheet(nombre_hoja)
            
            # Título
            worksheet.merge_range('A1:G1', f'MAYOR DE CUENTA: {cuenta_codigo} - {nombre_cuenta}', header_format)
            worksheet.merge_range('A2:G2', f'PERÍODO: {fecha_inicio} AL {fecha_fin}', header_format)
            
            # Encabezados
            headers = ['FECHA', 'COMPROBANTE', 'CONCEPTO', 'DEBE', 'HABER', 'SALDO', 'REF.']
            for col, header in enumerate(headers):
                worksheet.write(3, col, header, header_format)
            
            # Encontrar saldo inicial
            saldo_inicial = Decimal('0')
            for saldo in datos['saldos_iniciales']:
                if saldo[0] == cuenta_codigo:
                    saldo_inicial = Decimal(str(saldo[2]))
                    break
            
            # Saldo inicial
            row = 4
            worksheet.write(row, 2, 'SALDO INICIAL', cuenta_header_format)
            worksheet.write_number(row, 5, float(saldo_inicial), saldo_format)
            row += 1
            
            # Movimientos
            saldo_acumulado = saldo_inicial
            
            for mov in movimientos_cuenta:
                worksheet.write_datetime(row, 0, mov[2])
                worksheet.write(row, 1, mov[3])
                worksheet.write(row, 2, mov[4])
                
                if mov[5]:  # Debe
                    worksheet.write_number(row, 3, float(mov[5]), money_format)
                    saldo_acumulado += Decimal(str(mov[5]))
                
                if mov[6]:  # Haber
                    worksheet.write_number(row, 4, float(mov[6]), money_format)
                    saldo_acumulado -= Decimal(str(mov[6]))
                
                worksheet.write_number(row, 5, float(saldo_acumulado), money_format)
                worksheet.write(row, 6, mov[7] or '')
                row += 1
            
            # Totales
            total_debe = sum(Decimal(str(m[5] or 0)) for m in movimientos_cuenta)
            total_haber = sum(Decimal(str(m[6] or 0)) for m in movimientos_cuenta)
            
            worksheet.write(row, 2, 'TOTALES:', cuenta_header_format)
            worksheet.write_number(row, 3, float(total_debe), money_format)
            worksheet.write_number(row, 4, float(total_haber), money_format)
            worksheet.write_number(row, 5, float(saldo_acumulado), saldo_format)
            
            # Ajustar anchos
            worksheet.set_column('A:A', 12)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 40)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:E', 15)
            worksheet.set_column('F:F', 15)
            worksheet.set_column('G:G', 10)
            
            # Congelar paneles
            worksheet.freeze_panes(4, 0)
        
        # Hoja de Resumen
        worksheet_resumen = workbook.add_worksheet('Resumen General')
        
        # Resumen de todas las cuentas
        resumen_data = []
        for cuenta_codigo in cuentas_unicas:
            movimientos_cuenta = [m for m in datos['movimientos'] if m[0] == cuenta_codigo]
            nombre_cuenta = next((m[1] for m in movimientos_cuenta), '')
            
            # Encontrar saldo inicial
            saldo_inicial = Decimal('0')
            for saldo in datos['saldos_iniciales']:
                if saldo[0] == cuenta_codigo:
                    saldo_inicial = Decimal(str(saldo[2]))
                    break
            
            total_debe = sum(Decimal(str(m[5] or 0)) for m in movimientos_cuenta)
            total_haber = sum(Decimal(str(m[6] or 0)) for m in movimientos_cuenta)
            saldo_final = saldo_inicial + total_debe - total_haber
            
            resumen_data.append([
                cuenta_codigo,
                nombre_cuenta,
                float(saldo_inicial),
                float(total_debe),
                float(total_haber),
                float(saldo_final)
            ])
        
        # Escribir resumen
        headers_resumen = ['CÓDIGO', 'CUENTA', 'SALDO INICIAL', 'TOTAL DÉBITO', 'TOTAL CRÉDITO', 'SALDO FINAL']
        for col, header in enumerate(headers_resumen):
            worksheet_resumen.write(0, col, header, header_format)
        
        for row, data in enumerate(resumen_data, start=1):
            for col, value in enumerate(data):
                if col >= 2:  # Valores monetarios
                    worksheet_resumen.write_number(row, col, value, money_format)
                else:
                    worksheet_resumen.write(row, col, value)
        
        # Ajustar anchos
        worksheet_resumen.set_column('A:A', 12)
        worksheet_resumen.set_column('B:B', 40)
        worksheet_resumen.set_column('C:C', 15)
        worksheet_resumen.set_column('D:D', 15)
        worksheet_resumen.set_column('E:E', 15)
        worksheet_resumen.set_column('F:F', 15)
    
    output.seek(0)
    return output

def generar_pdf_balance_general(datos, fecha):
    """Generar PDF del Balance General"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=1,
        spaceAfter=30
    )
    
    story.append(Paragraph(f'BALANCE GENERAL', title_style))
    story.append(Paragraph(f'Al {fecha}', styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Crear tabla
    data = [['CÓDIGO', 'CUENTA', 'SALDO', '', 'CÓDIGO', 'CUENTA', 'SALDO']]
    
    # Separar cuentas de Activo y Pasivo/Capital
    cuentas_activo = [c for c in datos['cuentas'] if c[0].startswith('1')]
    cuentas_pasivo_capital = [c for c in datos['cuentas'] if c[0].startswith('2') or c[0].startswith('3')]
    
    max_rows = max(len(cuentas_activo), len(cuentas_pasivo_capital))
    
    for i in range(max_rows):
        row = ['', '', '', '', '', '', '']
        
        if i < len(cuentas_activo):
            cuenta = cuentas_activo[i]
            row[0] = cuenta[0]
            row[1] = '  ' * (cuenta[3] - 1) + cuenta[1]
            row[2] = f"${float(cuenta[7] or 0):,.2f}"
        
        if i < len(cuentas_pasivo_capital):
            cuenta = cuentas_pasivo_capital[i]
            row[4] = cuenta[0]
            row[5] = '  ' * (cuenta[3] - 1) + cuenta[1]
            row[6] = f"${float(cuenta[7] or 0):,.2f}"
        
        data.append(row)
    
    # Agregar totales
    data.append(['', 'TOTAL ACTIVO', f"${float(datos['total_activo']):,.2f}", 
                '', 'TOTAL PASIVO + CAPITAL', '', f"${float(datos['total_pasivo_capital']):,.2f}"])
    
    # Crear tabla
    table = Table(data, colWidths=[60, 200, 80, 20, 60, 200, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (6, 0), colors.HexColor('#366092')),
        ('TEXTCOLOR', (0, 0), (6, 0), colors.white),
        ('ALIGN', (0, 0), (6, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (6, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (6, 0), 10),
        ('BOTTOMPADDING', (0, 0), (6, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (2, 1), (2, -2), 'RIGHT'),
        ('ALIGN', (6, 1), (6, -2), 'RIGHT'),
        ('FONTNAME', (0, -1), (6, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (6, -1), colors.HexColor('#E6E6E6')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (3, 0), (3, -1)),  # Columna vacía para separación
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Validación
    diferencia = datos['total_activo'] - datos['total_pasivo_capital']
    if diferencia == 0:
        validacion = "✓ BALANCE CUADRADO CORRECTAMENTE"
        color = colors.green
    else:
        validacion = f"✗ BALANCE DESCUADRADO: ${float(diferencia):,.2f}"
        color = colors.red
    
    story.append(Paragraph(validacion, 
                          ParagraphStyle('Validacion',
                                        parent=styles['Normal'],
                                        textColor=color,
                                        fontSize=12,
                                        alignment=1,
                                        spaceBefore=20)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer