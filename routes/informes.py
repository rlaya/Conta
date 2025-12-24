# routes/informes.py
from flask import Blueprint, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
#from database import get_db_connection
from config.db import get_connection
from decimal import Decimal
import logging

informes_bp = Blueprint('informes', __name__, url_prefix='/informes')
logger = logging.getLogger(__name__)

@informes_bp.route('/')
def menu_informes():
    """Menú principal de informes"""
    return render_template('informes/menu.html')

@informes_bp.route('/balance-general')
def balance_general():
    """Balance General"""
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    nivel_detalle = request.args.get('nivel', '3')  # 1, 2, 3 niveles

    ahora = datetime.now()
    hoy_str = ahora.strftime('%Y-%m-%d')
    
    # Obtener datos del balance
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Consulta para balance general
        query = """
        WITH saldos_actualizados AS (
            SELECT 
                cc.id,
                cc.codigo,
                cc.nombre,
                cc.tipo,
                cc.nivel,
                cc.naturaleza,
                COALESCE(sc.saldo_inicial, 0) as saldo_inicial,
                COALESCE(SUM(CASE 
                    WHEN ac.debe > 0 THEN ac.debe 
                    WHEN ac.haber > 0 THEN -ac.haber 
                    ELSE 0 
                END), 0) as movimiento
            FROM cuentas_contables cc
            LEFT JOIN saldos_cuentas sc ON cc.id = sc.cuenta_id 
                AND sc.periodo = EXTRACT(YEAR FROM %s::date) || '-' || LPAD(EXTRACT(MONTH FROM %s::date)::text, 2, '0')
            LEFT JOIN asientos_contables ac ON cc.id = ac.cuenta_id 
                AND ac.fecha <= %s
            WHERE cc.tipo IN ('B', 'D')
            GROUP BY cc.id, cc.codigo, cc.nombre, cc.tipo, cc.nivel, cc.naturaleza, sc.saldo_inicial
        ),
        saldos_finales AS (
            SELECT *,
                saldo_inicial + movimiento as saldo_final,
                CASE 
                    WHEN naturaleza = 'D' THEN 
                        CASE 
                            WHEN saldo_inicial + movimiento >= 0 THEN saldo_inicial + movimiento
                            ELSE 0
                        END
                    ELSE 
                        CASE 
                            WHEN saldo_inicial + movimiento < 0 THEN ABS(saldo_inicial + movimiento)
                            ELSE 0
                        END
                END as saldo_mostrar
            FROM saldos_actualizados
        )
        SELECT 
            codigo,
            nombre,
            tipo,
            nivel,
            naturaleza,
            saldo_inicial,
            movimiento,
            saldo_final,
            saldo_mostrar
        FROM saldos_finales
        WHERE nivel <= %s
        ORDER BY codigo;
        """
        
        cursor.execute(query, (fecha, fecha, fecha, nivel_detalle))
        cuentas = cursor.fetchall()
        
        # Calcular totales
        total_activo = Decimal('0')
        total_pasivo = Decimal('0')
        total_capital = Decimal('0')
        
        for cuenta in cuentas:
            if cuenta[0].startswith('1'):  # Activo
                total_activo += Decimal(str(cuenta[7] or 0))
            elif cuenta[0].startswith('2'):  # Pasivo
                total_pasivo += Decimal(str(cuenta[7] or 0))
            elif cuenta[0].startswith('3'):  # Capital
                total_capital += Decimal(str(cuenta[7] or 0))
        
        # Preparar datos para la vista
        datos = {
            'hoy': hoy_str,
            'fecha': fecha,
            'nivel_detalle': nivel_detalle,
            'cuentas': cuentas,
            'total_activo': total_activo,
            'total_pasivo': total_pasivo,
            'total_capital': total_capital,
            'total_pasivo_capital': total_pasivo + total_capital
        }
        
    except Exception as e:
        logger.error(f"Error en balance general: {str(e)}")
        datos = {
            'hoy': hoy_str,
            'fecha': fecha,
            'nivel_detalle': nivel_detalle,
            'cuentas': [],
            'total_activo': Decimal('0'),
            'total_pasivo': Decimal('0'),
            'total_capital': Decimal('0'),
            'total_pasivo_capital': Decimal('0'),
            'error': str(e)
        }
    finally:
        cursor.close()
        conn.close()
    
    return render_template('informes/balance_general.html', **datos)

@informes_bp.route('/estado-resultados')
def estado_resultados():
    """Estado de Resultados corregido"""
    # 1. Inicialización de variables (Evita el NameError)
    ingresos = costos = gastos = gastos_financieros = []
    total_ingresos = total_costos = total_gastos = total_gastos_financieros = Decimal('0')
    utilidad_bruta = utilidad_operativa = utilidad_neta = Decimal('0')
    
    # 2. Gestión de fechas
    ahora = datetime.now()
    hoy_str = ahora.strftime('%Y-%m-%d')
    primer_dia_mes_str = ahora.replace(day=1).strftime('%Y-%m-%d')
    
    fecha_inicio = request.args.get('fecha_inicio', primer_dia_mes_str)
    fecha_fin = request.args.get('fecha_fin', hoy_str)

    # Variables para botones rápidos
    hace_30_dias = (ahora - timedelta(days=30)).strftime('%Y-%m-%d')
    primer_dia_anio = ahora.replace(month=1, day=1).strftime('%Y-%m-%d')
    u_dia_mes_ant = ahora.replace(day=1) - timedelta(days=1)
    p_dia_mes_ant = u_dia_mes_ant.replace(day=1).strftime('%Y-%m-%d')
    u_dia_mes_ant_str = u_dia_mes_ant.strftime('%Y-%m-%d')

    # Calcular días del periodo
    try:
        fi_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        ff_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        dias_periodo = (ff_dt - fi_dt).days + 1
    except:
        dias_periodo = 1

    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # --- CONSULTA INGRESOS ---
        cursor.execute("SELECT cc.codigo, cc.nombre, COALESCE(SUM(ac.haber - ac.debe), 0) FROM ...", (fecha_inicio, fecha_fin))
        ingresos = cursor.fetchall()
        total_ingresos = sum(Decimal(str(row[2] or 0)) for row in ingresos)

        # --- CONSULTA COSTOS ---
        # ... (Tu lógica de SQL para costos)
        # total_costos = ...

        # --- CÁLCULOS FINALES ---
        utilidad_bruta = total_ingresos - total_costos
        utilidad_operativa = utilidad_bruta - total_gastos
        utilidad_neta = utilidad_operativa - total_gastos_financieros
        
        error = None
    except Exception as e:
        print(f"Error en DB: {e}")
        error = str(e)
    finally:
        if conn:
            cursor.close()
            conn.close()

    # 3. Retorno unificado
    return render_template('informes/estado_resultados.html', 
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        hoy=hoy_str,
        hace_30_dias=hace_30_dias,
        primer_dia_mes=primer_dia_mes_str,
        primer_dia_anio=primer_dia_anio,
        primer_dia_mes_ant=p_dia_mes_ant,
        ultimo_dia_mes_ant=u_dia_mes_ant_str,
        dias_periodo=dias_periodo,
        ingresos=ingresos,
        costos=costos,
        gastos=gastos,
        gastos_financieros=gastos_financieros,
        total_ingresos=total_ingresos,
        total_costos=total_costos,
        total_gastos=total_gastos,
        total_gastos_financieros=total_gastos_financieros,
        utilidad_bruta=utilidad_bruta,
        utilidad_operativa=utilidad_operativa,
        utilidad_neta=utilidad_neta,
        error=error
    )


@informes_bp.route('/libro-diario')
def libro_diario():
    # 1. Inicialización de variables (Evita NameError)
    asientos = []
    total_debe = total_haber = Decimal('0')
    total = 0
    total_paginas = 1
    error = None

    # 2. Captura de parámetros y fechas
    hoy_dt = datetime.now()
    fecha_fin = request.args.get('fecha_fin', hoy_dt.strftime('%Y-%m-%d'))
    fecha_inicio = request.args.get('fecha_inicio', 
                                   (hoy_dt - timedelta(days=30)).strftime('%Y-%m-%d'))
    pagina = int(request.args.get('pagina', 1))
    por_pagina = int(request.args.get('por_pagina', 20))

    # 3. CÁLCULO DE DÍAS (Hazlo aquí, no en el HTML)
    try:
        f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
        dias_periodo = (f_fin - f_ini).days + 1
    except:
        dias_periodo = 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # --- Lógica de Base de Datos (Count, Asientos, Totales) ---
        # (Mantén tus queries aquí...)
        
        # Ejemplo de asignación segura de totales
        cursor.execute(query_totales, (fecha_inicio, fecha_fin))
        res_totales = cursor.fetchone()
        total_debe = Decimal(str(res_totales[0] or 0))
        total_haber = Decimal(str(res_totales[1] or 0))
        
        # ... (resto de tus queries)
        
    except Exception as e:
        error = str(e)
    finally:
        if conn:
            cursor.close()
            conn.close()

    # 4. Enviar todo procesado al template
    return render_template('informes/libro_diario.html',
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        asientos=asientos,
        total_debe=total_debe,
        total_haber=total_haber,
        pagina_actual=pagina,
        total_paginas=total_paginas,
        total=total,
        por_pagina=por_pagina,
        dias_periodo=dias_periodo, # Variable nueva
        error=error,
        today=hoy_dt.strftime('%Y-%m-%d')
    )


@informes_bp.route('/mayor-general')
def mayor_general():
    """Mayor General"""
    # 1. Gestión de fechas base
    ahora = datetime.now()
    hoy_str = ahora.strftime('%Y-%m-%d')
    primer_dia_str = ahora.replace(day=1).strftime('%Y-%m-%d')
    hace_30_dias_str = (ahora - timedelta(days=30)).strftime('%Y-%m-%d')

    # 2. Obtener parámetros de la URL o usar por defecto
    fecha_inicio = request.args.get('fecha_inicio', primer_dia_str)
    fecha_fin = request.args.get('fecha_fin', hoy_str)
    cuenta_id = request.args.get('cuenta_id')

    # 3. Calcular diferencia de días para el badge del HTML
    try:
        fi_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        ff_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        dias_periodo = (ff_dt - fi_dt).days + 1
    except:
        dias_periodo = 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # --- Obtener lista de cuentas para el filtro ---
        query_cuentas = """
        SELECT id, codigo, nombre 
        FROM cuentas_contables 
        WHERE tipo = 'D'
        ORDER BY codigo;
        """
        cursor.execute(query_cuentas)
        cuentas = cursor.fetchall()
        
        # --- Construir query de movimientos ---
        query_params = [fecha_inicio, fecha_fin]
        query_where = "WHERE ac.fecha BETWEEN %s AND %s"
        
        if cuenta_id:
            query_where += " AND cc.id = %s"
            query_params.append(cuenta_id)
        
        query = f"""
        SELECT 
            cc.codigo,
            cc.nombre as cuenta_nombre,
            ac.fecha,
            c.folio,
            c.concepto,
            ac.debe,
            ac.haber,
            ac.referencia,
            SUM(ac.debe - ac.haber) OVER (PARTITION BY cc.id ORDER BY ac.fecha, ac.id) as saldo_acumulado
        FROM asientos_contables ac
        JOIN comprobantes c ON ac.comprobante_id = c.id
        JOIN cuentas_contables cc ON ac.cuenta_id = cc.id
        {query_where}
        ORDER BY cc.codigo, ac.fecha, ac.id;
        """
        cursor.execute(query, tuple(query_params))
        movimientos = cursor.fetchall()
        
        # --- Calcular saldo inicial ---
        query_saldo_inicial = """
        SELECT 
            cc.codigo,
            cc.nombre,
            COALESCE(SUM(sc.saldo_inicial), 0) as saldo_inicial
        FROM cuentas_contables cc
        LEFT JOIN saldos_cuentas sc ON cc.id = sc.cuenta_id 
            AND sc.periodo = EXTRACT(YEAR FROM %s::date) || '-' || LPAD(EXTRACT(MONTH FROM %s::date)::text, 2, '0')
        WHERE cc.tipo = 'D'
        """
        if cuenta_id:
            query_saldo_inicial += " AND cc.id = %s"
            cursor.execute(query_saldo_inicial, (fecha_inicio, fecha_inicio, cuenta_id))
        else:
            query_saldo_inicial += " GROUP BY cc.id, cc.codigo, cc.nombre ORDER BY cc.codigo"
            cursor.execute(query_saldo_inicial, (fecha_inicio, fecha_inicio))
        
        saldos_iniciales = cursor.fetchall()
        
        # 4. Empaquetar datos para la plantilla
        datos = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'cuenta_id': cuenta_id,
            'cuentas': cuentas,
            'movimientos': movimientos,
            'saldos_iniciales': saldos_iniciales,
            'hoy': hoy_str,
            'primer_dia_mes': primer_dia_str,
            'hace_30_dias': hace_30_dias_str,
            'dias_periodo': dias_periodo
        }
        
    except Exception as e:
        # logger.error(f"Error en mayor general: {str(e)}") # Asegúrate de tener definido 'logger'
        datos = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'cuenta_id': cuenta_id,
            'cuentas': [],
            'movimientos': [],
            'saldos_iniciales': [],
            'hoy': hoy_str,
            'primer_dia_mes': primer_dia_str,
            'hace_30_dias': hace_30_dias_str,
            'dias_periodo': 0,
            'error': str(e)
        }
    finally:
        cursor.close()
        conn.close()
    
    return render_template('informes/mayor_general.html', **datos)

@informes_bp.route('/exportar/<informe>/<formato>')
def exportar_informe(informe, formato):
    """Exportar informe a Excel o PDF"""
    # Obtener parámetros
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    fecha_inicio = request.args.get('fecha_inicio', 
                                   (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.args.get('fecha_fin', datetime.now().strftime('%Y-%m-%d'))
    cuenta_id = request.args.get('cuenta_id')
    
    # Obtener datos según el informe
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        if informe == 'balance-general':
            # Obtener datos para balance general (similar a la función balance_general)
            query = """
            WITH saldos_actualizados AS (
                SELECT 
                    cc.id,
                    cc.codigo,
                    cc.nombre,
                    cc.tipo,
                    cc.nivel,
                    cc.naturaleza,
                    COALESCE(sc.saldo_inicial, 0) as saldo_inicial,
                    COALESCE(SUM(CASE 
                        WHEN ac.debe > 0 THEN ac.debe 
                        WHEN ac.haber > 0 THEN -ac.haber 
                        ELSE 0 
                    END), 0) as movimiento
                FROM cuentas_contables cc
                LEFT JOIN saldos_cuentas sc ON cc.id = sc.cuenta_id 
                    AND sc.periodo = EXTRACT(YEAR FROM %s::date) || '-' || LPAD(EXTRACT(MONTH FROM %s::date)::text, 2, '0')
                LEFT JOIN asientos_contables ac ON cc.id = ac.cuenta_id 
                    AND ac.fecha <= %s
                WHERE cc.tipo IN ('B', 'D')
                GROUP BY cc.id, cc.codigo, cc.nombre, cc.tipo, cc.nivel, cc.naturaleza, sc.saldo_inicial
            ),
            saldos_finales AS (
                SELECT *,
                    saldo_inicial + movimiento as saldo_final
                FROM saldos_actualizados
            )
            SELECT 
                codigo,
                nombre,
                tipo,
                nivel,
                naturaleza,
                saldo_inicial,
                movimiento,
                saldo_final
            FROM saldos_finales
            ORDER BY codigo;
            """
            
            cursor.execute(query, (fecha, fecha, fecha))
            cuentas = cursor.fetchall()
            
            # Calcular totales
            total_activo = Decimal('0')
            total_pasivo = Decimal('0')
            total_capital = Decimal('0')
            
            for cuenta in cuentas:
                if cuenta[0].startswith('1'):
                    total_activo += Decimal(str(cuenta[7] or 0))
                elif cuenta[0].startswith('2'):
                    total_pasivo += Decimal(str(cuenta[7] or 0))
                elif cuenta[0].startswith('3'):
                    total_capital += Decimal(str(cuenta[7] or 0))
            
            datos = {
                'cuentas': cuentas,
                'total_activo': total_activo,
                'total_pasivo': total_pasivo,
                'total_capital': total_capital,
                'total_pasivo_capital': total_pasivo + total_capital
            }
            
            if formato == 'excel':
                from helpers.export_helper import exportar_balance_general_excel
                output = exportar_balance_general_excel(datos, fecha)
                filename = f"balance_general_{fecha}.xlsx"
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                from helpers.export_helper import generar_pdf_balance_general
                output = generar_pdf_balance_general(datos, fecha)
                filename = f"balance_general_{fecha}.pdf"
                mimetype = 'application/pdf'
                
        elif informe == 'estado-resultados':
            # Similar lógica para estado de resultados
            # ... (implementar según necesidad)
            pass
            
        elif informe == 'libro-diario':
            # Similar lógica para libro diario
            # ... (implementar según necesidad)
            pass
            
        elif informe == 'mayor-general':
            # Similar lógica para mayor general
            # ... (implementar según necesidad)
            pass
            
    except Exception as e:
        logger.error(f"Error exportando {informe}: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
    
    return send_file(output, 
                    download_name=filename, 
                    as_attachment=True, 
                    mimetype=mimetype)

def exportar_excel(informe, fecha_inicio, fecha_fin):
    """Exportar a Excel"""
    # Obtener datos según el informe
    # (Implementar según cada tipo de informe)
    
    # Crear archivo Excel en memoria
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(informe)
    
    # Estilos
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#366092',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    money_format = workbook.add_format({
        'num_format': '$#,##0.00',
        'border': 1
    })
    
    # Escribir datos
    # ... (Implementar según cada informe)
    
    workbook.close()
    output.seek(0)
    
    filename = f"{informe}_{fecha_inicio}_a_{fecha_fin}.xlsx"
    return send_file(output, 
                    download_name=filename, 
                    as_attachment=True, 
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

def exportar_pdf(informe, fecha_inicio, fecha_fin):
    """Exportar a PDF"""
    # Crear PDF en memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Título
    title = Paragraph(f"{informe.replace('-', ' ').title()}", styles['Title'])
    elements.append(title)
    
    # Fechas
    fecha_text = Paragraph(f"Período: {fecha_inicio} a {fecha_fin}", styles['Normal'])
    elements.append(fecha_text)
    elements.append(Spacer(1, 20))
    
    # Obtener datos y crear tabla
    # ... (Implementar según cada informe)
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"{informe}_{fecha_inicio}_a_{fecha_fin}.pdf"
    return send_file(buffer, 
                    download_name=filename, 
                    as_attachment=True, 
                    mimetype='application/pdf')