# models/comprobantes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import os

from config.db import get_connection


# Crear Blueprint
comprobantes_bp = Blueprint('comprobantes', __name__, template_folder='templates/comprobantes')

# Formulario para Comprobantes
class ComprobanteForm(FlaskForm):
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=10)])
    folio = StringField('Folio', validators=[DataRequired(), Length(max=20)])
    fecha = DateField('Fecha', validators=[DataRequired()], format='%Y-%m-%d')
    concepto = TextAreaField('Concepto', validators=[DataRequired()])
    total = DecimalField('Total', validators=[DataRequired()], places=2)
    estado = SelectField('Estado', choices=[
        ('Pendiente', 'Pendiente'),
        ('Registrado', 'Registrado'),
        ('Anulado', 'Anulado')
    ], validators=[DataRequired()])
    id_cliente = IntegerField('ID Cliente', validators=[Optional()])
    id_proveedor = IntegerField('ID Proveedor', validators=[Optional()])

# Formulario para Asientos Contables
class AsientoForm(FlaskForm):
    consecutivo = IntegerField('Consecutivo', validators=[DataRequired()])
    id_cuenta = StringField('Cuenta Contable', validators=[DataRequired(), Length(max=20)])
    fecha = DateField('Fecha', validators=[DataRequired()], format='%Y-%m-%d')
    concepto = TextAreaField('Concepto', validators=[Optional()])
    debe = DecimalField('Debe', validators=[Optional()], default=0, places=2)
    haber = DecimalField('Haber', validators=[Optional()], default=0, places=2)
    referencia = StringField('Referencia', validators=[Optional(), Length(max=100)])

# Ruta principal de comprobantes
@comprobantes_bp.route('/comprobantes')
def comprobantes():
    from config.db import get_connection
    from urllib.parse import urlencode  # Agregar este import
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Obtener valores de filtros del request
    filtros = {
        'tipo': request.args.get('tipo', ''),
        'folio': request.args.get('folio', ''),
        'estado': request.args.get('estado', ''),
        'fecha_desde': request.args.get('fecha_desde', ''),
        'fecha_hasta': request.args.get('fecha_hasta', '')
    }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Construir query base
    query_base = """
        FROM comprobantes
        WHERE 1=1
    """
    params = []
    
    # Aplicar filtros
    if filtros['tipo']:
        query_base += " AND tipo LIKE ?"
        params.append(f'%{filtros["tipo"]}%')
    
    if filtros['folio']:
        query_base += " AND folio LIKE ?"
        params.append(f'%{filtros["folio"]}%')
    
    if filtros['estado']:
        query_base += " AND estado = ?"
        params.append(filtros['estado'])
    
    if filtros['fecha_desde']:
        query_base += " AND fecha >= ?"
        params.append(filtros['fecha_desde'])
    
    if filtros['fecha_hasta']:
        query_base += " AND fecha <= ?"
        params.append(filtros['fecha_hasta'])
    
    # Primero contar el total de registros
    count_query = "SELECT COUNT(*) " + query_base
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # Calcular total de páginas
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Asegurar que page esté dentro del rango válido
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    # Consulta paginada
    query = """
        SELECT tipo, folio, fecha, concepto, total, estado, 
               id_cliente, id_proveedor, creado_en
    """ + query_base + """
        ORDER BY fecha DESC, creado_en DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    
    # Agregar parámetros de paginación
    params_paginated = params + [offset, per_page]
    
    cursor.execute(query, params_paginated)
    comprobantes = cursor.fetchall()
    
    conn.close()
    
    # Convertir a lista de diccionarios para facilitar el uso en templates
    comprobantes_list = []
    for row in comprobantes:
        comprobantes_list.append({
            'tipo': row.tipo,
            'folio': row.folio,
            'fecha': row.fecha.strftime('%Y-%m-%d') if hasattr(row.fecha, 'strftime') else str(row.fecha),
            'concepto': row.concepto,
            'total': float(row.total) if row.total else 0.0,
            'estado': row.estado,
            'id_cliente': row.id_cliente,
            'id_proveedor': row.id_proveedor,
            'creado_en': row.creado_en.strftime('%Y-%m-%d %H:%M:%S') if hasattr(row.creado_en, 'strftime') else str(row.creado_en)
        })
    
    # Crear URL base para paginación
    base_url = url_for('comprobantes.comprobantes')
    
    # Agregar filtros a la URL base si existen
    query_args = {}
    for key, value in filtros.items():
        if value:
            query_args[key] = value
    
    if query_args:
        base_url += '?' + urlencode(query_args)
    
    return render_template('comprobantes/comprobantes.html', 
                         comprobantes=comprobantes_list,
                         filtros=filtros,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         base_url=base_url)

# Ruta para nuevo comprobante
@comprobantes_bp.route('/comprobantes/nuevo', methods=['GET', 'POST'])
def nuevo_comprobante():
    form = ComprobanteForm()
    
    if form.validate_on_submit():
        from config.db import get_connection
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Verificar si el comprobante ya existe
            cursor.execute("""
                SELECT COUNT(*) FROM comprobantes 
                WHERE tipo = ? AND folio = ?
            """, (form.tipo.data, form.folio.data))
            
            if cursor.fetchone()[0] > 0:
                flash('Ya existe un comprobante con ese tipo y folio', 'danger')
            else:
                # Insertar nuevo comprobante
                cursor.execute("""
                    INSERT INTO comprobantes 
                    (tipo, folio, fecha, concepto, total, estado, id_cliente, id_proveedor, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    form.tipo.data,
                    form.folio.data,
                    form.fecha.data,
                    form.concepto.data,
                    float(form.total.data),
                    form.estado.data,
                    form.id_cliente.data if form.id_cliente.data else None,
                    form.id_proveedor.data if form.id_proveedor.data else None
                ))
                
                conn.commit()
                flash('Comprobante creado exitosamente!', 'success')
                return redirect(url_for('comprobantes.comprobantes'))
                
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            flash(f'Error al crear comprobante: {str(e)}', 'danger')
        finally:
            if 'conn' in locals():
                conn.close()
    
    return render_template('comprobantes/form_comprobante.html', form=form)

# Ruta para ver comprobante
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>')
def ver_comprobante(tipo, folio):
    from config.db import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT tipo, folio, fecha, concepto, total, estado, 
                   id_cliente, id_proveedor, creado_en
            FROM comprobantes
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        row = cursor.fetchone()
        
        if not row:
            flash('Comprobante no encontrado', 'danger')
            return redirect(url_for('comprobantes.comprobantes'))
        
        comprobante = {
            'tipo': row.tipo,
            'folio': row.folio,
            'fecha': row.fecha.strftime('%Y-%m-%d') if hasattr(row.fecha, 'strftime') else str(row.fecha),
            'concepto': row.concepto,
            'total': float(row.total) if row.total else 0.0,
            'estado': row.estado,
            'id_cliente': row.id_cliente,
            'id_proveedor': row.id_proveedor,
            'creado_en': row.creado_en.strftime('%Y-%m-%d %H:%M:%S') if hasattr(row.creado_en, 'strftime') else str(row.creado_en)
        }
        
        return render_template('comprobantes/ver_comprobante.html', comprobante=comprobante)
    finally:
        conn.close()

# Ruta para editar comprobante
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/editar', methods=['GET', 'POST'])
def editar_comprobante(tipo, folio):
    from config.db import get_connection
    from utils.validaciones_contables import validar_comprobante_contable

    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Obtener el estado actual en la DB antes de cualquier cambio
    cursor.execute("SELECT estado FROM comprobantes WHERE tipo = ? AND folio = ?", (tipo, folio))
    res = cursor.fetchone()
    if not res:
        flash('Comprobante no encontrado', 'danger')
        return redirect(url_for('comprobantes.comprobantes'))
    
    estado_actual_db = res.estado

    if request.method == 'POST':
        form = ComprobanteForm(request.form)
        if form.validate():
            # BLOQUEO: Si ya estaba registrado, no permitir cambios (opcional según tu regla de negocio)
            if estado_actual_db == 'Registrado' and form.estado.data == 'Registrado':
                 flash('No se puede editar un comprobante que ya está Registrado.', 'warning')
                 return redirect(url_for('comprobantes.comprobantes'))

            # VALIDACIÓN: Si intenta registrarlo ahora
            if form.estado.data == 'Registrado':
                valido, mensaje = validar_comprobante_contable(tipo, folio)
                if not valido:
                    flash(f'Error de cuadre: {mensaje}', 'danger')
                    return render_template('comprobantes/form_comprobante.html', form=form, comprobante={'tipo': tipo, 'folio': folio})

            try:
                cursor.execute("""
                    UPDATE comprobantes 
                    SET fecha = ?, concepto = ?, total = ?, estado = ?, id_cliente = ?, id_proveedor = ?
                    WHERE tipo = ? AND folio = ?
                """, (form.fecha.data, form.concepto.data, float(form.total.data), 
                    form.estado.data, form.id_cliente.data or None, 
                    form.id_proveedor.data or None, tipo, folio))
                conn.commit()
                flash('Actualizado correctamente', 'success')
                return redirect(url_for('comprobantes.comprobantes'))
            except Exception as e:
                conn.rollback()
                flash(f'Error: {str(e)}', 'danger')
            finally:
                conn.close()
    
    else: # GET: Cargar datos para el formulario
        cursor.execute("SELECT * FROM comprobantes WHERE tipo = ? AND folio = ?", (tipo, folio))
        row = cursor.fetchone()
        form = ComprobanteForm(data=row)
        conn.close()

    return render_template('comprobantes/form_comprobante.html', form=form, comprobante={'tipo': tipo, 'folio': folio})

# Ruta para eliminar comprobante
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/eliminar', methods=['POST'])
def eliminar_comprobante(tipo, folio):
    from config.db import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Primero eliminar los asientos relacionados (si existe la tabla asientos_contables)
        try:
            cursor.execute("""
                DELETE FROM asientos_contables 
                WHERE id_comprobante_tipo = ? AND id_comprobante_folio = ?
            """, (tipo, folio))
        except:
            pass  # La tabla puede no existir
        
        # Luego eliminar el comprobante
        cursor.execute("""
            DELETE FROM comprobantes 
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        conn.commit()
        flash('Comprobante eliminado exitosamente!', 'success')
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        flash(f'Error al eliminar comprobante: {str(e)}', 'danger')
    finally:
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('comprobantes.comprobantes'))

# Ruta para exportar a Excel
@comprobantes_bp.route('/comprobantes/exportar/excel')
def comprobantes_excel():
    from config.db import get_connection
    from io import BytesIO
    
    # Obtener filtros
    tipo = request.args.get('tipo', '')
    folio = request.args.get('folio', '')
    estado = request.args.get('estado', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    id_cliente = request.args.get('id_cliente', '')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Construir query con filtros
    where_clauses = []
    params = []
    
    if tipo:
        where_clauses.append("tipo LIKE ?")
        params.append(f'%{tipo}%')
    
    if folio:
        where_clauses.append("folio LIKE ?")
        params.append(f'%{folio}%')
    
    if estado:
        where_clauses.append("estado = ?")
        params.append(estado)
    
    if fecha_desde:
        where_clauses.append("fecha >= ?")
        params.append(fecha_desde)
    
    if fecha_hasta:
        where_clauses.append("fecha <= ?")
        params.append(fecha_hasta)
    
    if id_cliente:
        where_clauses.append("id_cliente = ?")
        params.append(int(id_cliente))
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
        SELECT tipo, folio, fecha, concepto, total, estado, 
               id_cliente, id_proveedor, creado_en
        FROM comprobantes
        WHERE {where_sql}
        ORDER BY fecha DESC, creado_en DESC
    """
    
    cursor.execute(query, params)
    comprobantes = cursor.fetchall()
    conn.close()
    
    # Crear DataFrame
    data = []
    for row in comprobantes:
        data.append({
            'Tipo': row.tipo,
            'Folio': row.folio,
            'Fecha': row.fecha.strftime('%d/%m/%Y') if hasattr(row.fecha, 'strftime') else str(row.fecha),
            'Concepto': row.concepto,
            'Total': float(row.total) if row.total else 0.0,
            'Estado': row.estado,
            'Cliente': row.id_cliente,
            'Proveedor': row.id_proveedor,
            'Creado': row.creado_en.strftime('%d/%m/%Y %H:%M') if hasattr(row.creado_en, 'strftime') else str(row.creado_en)
        })
    
    df = pd.DataFrame(data)
    
    # Crear respuesta Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Comprobantes', index=False)
        
        # Ajustar anchos de columna
        worksheet = writer.sheets['Comprobantes']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    
    # Crear respuesta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=comprobantes.xlsx'
    
    return response

# Ruta para exportar a PDF
@comprobantes_bp.route('/comprobantes/exportar/pdf')
def comprobantes_pdf():
    from config.db import get_connection
    
    # Obtener filtros
    tipo = request.args.get('tipo', '')
    folio = request.args.get('folio', '')
    estado = request.args.get('estado', '')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Construir query con filtros
    where_clauses = []
    params = []
    
    if tipo:
        where_clauses.append("tipo LIKE ?")
        params.append(f'%{tipo}%')
    
    if folio:
        where_clauses.append("folio LIKE ?")
        params.append(f'%{folio}%')
    
    if estado:
        where_clauses.append("estado = ?")
        params.append(estado)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
        SELECT tipo, folio, fecha, concepto, total, estado, 
               id_cliente, id_proveedor, creado_en
        FROM comprobantes
        WHERE {where_sql}
        ORDER BY fecha DESC, creado_en DESC
    """
    
    cursor.execute(query, params)
    comprobantes = cursor.fetchall()
    conn.close()
    
    # Crear PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    # Título
    elements.append(Paragraph("Reporte de Comprobantes", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Información de filtros
    filtros_text = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if tipo:
        filtros_text += f" | Tipo: {tipo}"
    if folio:
        filtros_text += f" | Folio: {folio}"
    if estado:
        filtros_text += f" | Estado: {estado}"
    
    elements.append(Paragraph(filtros_text, normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Crear tabla
    data = [['Tipo', 'Folio', 'Fecha', 'Concepto', 'Total', 'Estado']]
    
    total_general = 0
    for row in comprobantes:
        fecha_str = row.fecha.strftime('%d/%m/%Y') if hasattr(row.fecha, 'strftime') else str(row.fecha)
        concepto = row.concepto[:30] + '...' if len(row.concepto) > 30 else row.concepto
        total_val = float(row.total) if row.total else 0.0
        
        data.append([
            row.tipo,
            row.folio,
            fecha_str,
            concepto,
            f"${total_val:,.2f}",
            row.estado
        ])
        total_general += total_val
    
    # Agregar total
    data.append(['', '', '', 'TOTAL GENERAL:', f"${total_general:,.2f}", ''])
    
    # Crear tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('ALIGN', (3, -1), (4, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('GRID', (3, -1), (4, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Crear respuesta
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=comprobantes.pdf'
    
    return response

@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/reversar', methods=['GET', 'POST'])
def reversar_comprobante(tipo, folio):
    from config.db import get_connection
    from utils.validaciones_contables import crear_comprobante_reverso
    
    if request.method == 'POST':
        nuevo_tipo = request.form.get('nuevo_tipo')
        nuevo_folio = request.form.get('nuevo_folio')
        
        if not nuevo_tipo or not nuevo_folio:
            flash('Debe especificar tipo y folio para el comprobante de reversión', 'danger')
            return redirect(url_for('comprobantes.ver_comprobante', tipo=tipo, folio=folio))
        
        # Crear comprobante reverso
        exito, mensaje = crear_comprobante_reverso(tipo, folio, nuevo_tipo, nuevo_folio)
        
        if exito:
            flash(mensaje, 'success')
            return redirect(url_for('comprobantes.ver_comprobante', tipo=nuevo_tipo, folio=nuevo_folio))
        else:
            flash(mensaje, 'danger')
            return redirect(url_for('comprobantes.ver_comprobante', tipo=tipo, folio=folio))
    
    # Mostrar formulario para reversión
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tipo, folio, fecha, concepto, total, estado 
        FROM comprobantes 
        WHERE tipo = ? AND folio = ?
    """, (tipo, folio))
    
    comprobante = cursor.fetchone()
    conn.close()
    
    if not comprobante or comprobante.estado != 'Registrado':
        flash('Solo se pueden reversar comprobantes en estado "Registrado"', 'danger')
        return redirect(url_for('comprobantes.comprobantes'))
    
    return render_template('comprobantes/reversar.html', 
                         comprobante=comprobante)    

# Ruta para asientos de un comprobante
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos')
def asientos(tipo, folio):
    from config.db import get_connection
    from urllib.parse import urlencode
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Filtros para asientos
    id_cuenta = request.args.get('id_cuenta', '')
    concepto = request.args.get('concepto', '')
    referencia = request.args.get('referencia', '')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Primero verificar si el comprobante existe
        cursor.execute("""
            SELECT tipo, folio, fecha, concepto, total, estado,
                   id_cliente, id_proveedor, creado_en
            FROM comprobantes
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        comprobante_row = cursor.fetchone()
        
        if not comprobante_row:
            flash('Comprobante no encontrado', 'danger')
            return redirect(url_for('comprobantes.comprobantes'))
        
        # Obtener comprobante como diccionario
        comprobante = {
            'tipo': comprobante_row.tipo,
            'folio': comprobante_row.folio,
            'fecha': comprobante_row.fecha.strftime('%Y-%m-%d') if hasattr(comprobante_row.fecha, 'strftime') else str(comprobante_row.fecha),
            'concepto': comprobante_row.concepto,
            'total': float(comprobante_row.total) if comprobante_row.total else 0.0,
            'estado': comprobante_row.estado,
            'id_cliente': comprobante_row.id_cliente,
            'id_proveedor': comprobante_row.id_proveedor,
            'creado_en': comprobante_row.creado_en.strftime('%Y-%m-%d %H:%M:%S') if hasattr(comprobante_row.creado_en, 'strftime') else str(comprobante_row.creado_en)
        }
        
        # Construir WHERE clause para asientos
        where_clauses = ["id_comprobante_tipo = ?", "id_comprobante_folio = ?"]
        params = [tipo, folio]
        
        if id_cuenta:
            where_clauses.append("id_cuenta LIKE ?")
            params.append(f'%{id_cuenta}%')
        
        if concepto:
            where_clauses.append("concepto LIKE ?")
            params.append(f'%{concepto}%')
        
        if referencia:
            where_clauses.append("referencia LIKE ?")
            params.append(f'%{referencia}%')
        
        where_sql = " AND ".join(where_clauses)
        
        # Contar total de asientos
        count_query = f"SELECT COUNT(*) FROM asientos_contables WHERE {where_sql}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Obtener asientos paginados
        query = f"""
            SELECT consecutivo, id_cuenta, fecha, concepto, 
                   debe, haber, referencia, creado_en,
                   id_comprobante_tipo, id_comprobante_folio
            FROM asientos_contables
            WHERE {where_sql}
            ORDER BY consecutivo
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        params_paginated = params + [offset, per_page]
        cursor.execute(query, params_paginated)
        asientos_data = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        asientos_list = []
        total_debe = 0
        total_haber = 0
        
        for row in asientos_data:
            debe_val = float(row.debe) if row.debe else 0.0
            haber_val = float(row.haber) if row.haber else 0.0
            
            asientos_list.append({
                'consecutivo': row.consecutivo,
                'id_cuenta': row.id_cuenta,
                'fecha': row.fecha.strftime('%Y-%m-%d') if hasattr(row.fecha, 'strftime') else str(row.fecha),
                'concepto': row.concepto,
                'debe': debe_val,
                'haber': haber_val,
                'referencia': row.referencia,
                'creado_en': row.creado_en.strftime('%Y-%m-%d %H:%M:%S') if hasattr(row.creado_en, 'strftime') else str(row.creado_en),
                'id_comprobante_tipo': row.id_comprobante_tipo,
                'id_comprobante_folio': row.id_comprobante_folio
            })
            
            total_debe += debe_val
            total_haber += haber_val
        
        # Calcular total de páginas
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # Crear un objeto de paginación simulado
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = total_pages
                self.has_prev = page > 1
                self.has_next = page < total_pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
                
            def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if (num <= left_edge or 
                        (num > self.page - left_current - 1 and num < self.page + right_current) or 
                        num > self.pages - right_edge):
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = Pagination(asientos_list, page, per_page, total)
        
        # Preparar query string para paginación
        query_args = {}
        if id_cuenta:
            query_args['id_cuenta'] = id_cuenta
        if concepto:
            query_args['concepto'] = concepto
        if referencia:
            query_args['referencia'] = referencia
        
        base_url = url_for('comprobantes.asientos', tipo=tipo, folio=folio)
        if query_args:
            base_url += '?' + urlencode(query_args)
        
        return render_template('comprobantes/asientos.html', 
                             comprobante=comprobante,
                             asientos=pagination,  # Ahora es un objeto de paginación
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             base_url=base_url,
                             total_debe=total_debe,
                             total_haber=total_haber,
                             filtros={
                                 'id_cuenta': id_cuenta,
                                 'concepto': concepto,
                                 'referencia': referencia
                             })
        
    except Exception as e:
        flash(f'Error al cargar asientos: {str(e)}', 'danger')
        return redirect(url_for('comprobantes.comprobantes'))
    finally:
        conn.close()

# Ruta para nuevo asiento
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos/nuevo', methods=['GET', 'POST'])
def nuevo_asiento(tipo, folio):
    from config.db import get_connection
    
    # Primero obtener datos del comprobante
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tipo, folio, concepto 
        FROM comprobantes 
        WHERE tipo = ? AND folio = ?
    """, (tipo, folio))
    
    comprobante_row = cursor.fetchone()
    conn.close()
    
    if not comprobante_row:
        flash('Comprobante no encontrado', 'danger')
        return redirect(url_for('comprobantes.comprobantes'))
    
    comprobante = {
        'tipo': comprobante_row.tipo,
        'folio': comprobante_row.folio,
        'concepto': comprobante_row.concepto
    }
    
    form = AsientoForm()
    
    # Establecer fecha por defecto como hoy
    if not form.fecha.data:
        form.fecha.data = datetime.now().date()
    
    if form.validate_on_submit():
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si el comprobante existe
            cursor.execute("""
                SELECT COUNT(*) FROM comprobantes 
                WHERE tipo = ? AND folio = ?
            """, (tipo, folio))
            
            if cursor.fetchone()[0] == 0:
                flash('Comprobante no existe', 'danger')
                return redirect(url_for('comprobantes.comprobantes'))
            
            # Verificar si el consecutivo ya existe
            cursor.execute("""
                SELECT COUNT(*) FROM asientos_contables 
                WHERE id_comprobante_tipo = ? 
                AND id_comprobante_folio = ? 
                AND consecutivo = ?
            """, (tipo, folio, form.consecutivo.data))
            
            if cursor.fetchone()[0] > 0:
                flash('El número de consecutivo ya existe para este comprobante', 'danger')
            else:
                # Insertar nuevo asiento
                cursor.execute("""
                    INSERT INTO asientos_contables 
                    (id_comprobante_tipo, id_comprobante_folio, consecutivo, 
                     id_cuenta, fecha, concepto, debe, haber, referencia, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    tipo,
                    folio,
                    form.consecutivo.data,
                    form.id_cuenta.data,
                    form.fecha.data,
                    form.concepto.data,
                    float(form.debe.data) if form.debe.data else 0.0,
                    float(form.haber.data) if form.haber.data else 0.0,
                    form.referencia.data or ''
                ))
                
                conn.commit()
                flash('Asiento creado exitosamente!', 'success')
                return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
                
        except Exception as e:
            conn.rollback()
            flash(f'Error al crear asiento: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('comprobantes/form_asiento.html', 
                         form=form, 
                         comprobante=comprobante,
                         action='crear')

# Ruta para editar asiento
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos/<int:consecutivo>/editar', methods=['GET', 'POST'])
def editar_asiento(tipo, folio, consecutivo):
    from config.db import get_connection
    
    if request.method == 'POST':
        form = AsientoForm(request.form)
        
        if form.validate():
            conn = get_connection()
            cursor = conn.cursor()
            
            try:
                # Verificar si el asiento existe
                cursor.execute("""
                    SELECT COUNT(*) FROM asientos_contables 
                    WHERE id_comprobante_tipo = ? 
                    AND id_comprobante_folio = ? 
                    AND consecutivo = ?
                """, (tipo, folio, consecutivo))
                
                if cursor.fetchone()[0] == 0:
                    flash('Asiento no encontrado', 'danger')
                    return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
                
                # Actualizar asiento
                cursor.execute("""
                    UPDATE asientos_contables 
                    SET id_cuenta = ?, fecha = ?, concepto = ?, 
                        debe = ?, haber = ?, referencia = ?
                    WHERE id_comprobante_tipo = ? 
                    AND id_comprobante_folio = ? 
                    AND consecutivo = ?
                """, (
                    form.id_cuenta.data,
                    form.fecha.data,
                    form.concepto.data,
                    float(form.debe.data) if form.debe.data else 0.0,
                    float(form.haber.data) if form.haber.data else 0.0,
                    form.referencia.data or '',
                    tipo,
                    folio,
                    consecutivo
                ))
                
                conn.commit()
                flash('Asiento actualizado exitosamente!', 'success')
                return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
                
            except Exception as e:
                conn.rollback()
                flash(f'Error al actualizar asiento: {str(e)}', 'danger')
            finally:
                conn.close()
    else:
        # Cargar datos del asiento para editar
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id_cuenta, fecha, concepto, debe, haber, referencia
                FROM asientos_contables
                WHERE id_comprobante_tipo = ? 
                AND id_comprobante_folio = ? 
                AND consecutivo = ?
            """, (tipo, folio, consecutivo))
            
            row = cursor.fetchone()
            
            if not row:
                flash('Asiento no encontrado', 'danger')
                return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
            
            # Crear formulario con datos existentes
            asiento_data = {
                'consecutivo': consecutivo,
                'id_cuenta': row.id_cuenta,
                'fecha': row.fecha,
                'concepto': row.concepto,
                'debe': row.debe,
                'haber': row.haber,
                'referencia': row.referencia
            }
            
            form = AsientoForm(data=asiento_data)
            
            # Obtener datos del comprobante
            cursor.execute("""
                SELECT tipo, folio, concepto 
                FROM comprobantes 
                WHERE tipo = ? AND folio = ?
            """, (tipo, folio))
            
            comprobante_row = cursor.fetchone()
            comprobante = {
                'tipo': comprobante_row.tipo,
                'folio': comprobante_row.folio,
                'concepto': comprobante_row.concepto
            }
            
            return render_template('comprobantes/form_asiento.html', 
                                 form=form, 
                                 comprobante=comprobante,
                                 asiento={'consecutivo': consecutivo},
                                 action='editar')
            
        finally:
            conn.close()

# Ruta para eliminar asiento
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos/<int:consecutivo>/eliminar', methods=['POST'])
def eliminar_asiento(tipo, folio, consecutivo):
    from config.db import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si el asiento existe
        cursor.execute("""
            SELECT COUNT(*) FROM asientos_contables 
            WHERE id_comprobante_tipo = ? 
            AND id_comprobante_folio = ? 
            AND consecutivo = ?
        """, (tipo, folio, consecutivo))
        
        if cursor.fetchone()[0] == 0:
            flash('Asiento no encontrado', 'danger')
        else:
            # Eliminar asiento
            cursor.execute("""
                DELETE FROM asientos_contables 
                WHERE id_comprobante_tipo = ? 
                AND id_comprobante_folio = ? 
                AND consecutivo = ?
            """, (tipo, folio, consecutivo))
            
            conn.commit()
            flash('Asiento eliminado exitosamente!', 'success')
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        flash(f'Error al eliminar asiento: {str(e)}', 'danger')
    finally:
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))

# Ruta para exportar asientos a Excel
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos/exportar/excel')
def asientos_excel(tipo, folio):
    from config.db import get_connection
    from io import BytesIO
    
    # Obtener filtros
    id_cuenta = request.args.get('id_cuenta', '')
    concepto = request.args.get('concepto', '')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si el comprobante existe
        cursor.execute("""
            SELECT tipo, folio, concepto 
            FROM comprobantes 
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        comprobante_row = cursor.fetchone()
        
        if not comprobante_row:
            flash('Comprobante no encontrado', 'danger')
            return redirect(url_for('comprobantes.comprobantes'))
        
        # Construir query para asientos
        where_clauses = ["id_comprobante_tipo = ?", "id_comprobante_folio = ?"]
        params = [tipo, folio]
        
        if id_cuenta:
            where_clauses.append("id_cuenta LIKE ?")
            params.append(f'%{id_cuenta}%')
        
        if concepto:
            where_clauses.append("concepto LIKE ?")
            params.append(f'%{concepto}%')
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT consecutivo, id_cuenta, fecha, concepto, 
                   debe, haber, referencia, creado_en
            FROM asientos_contables
            WHERE {where_sql}
            ORDER BY consecutivo
        """
        
        cursor.execute(query, params)
        asientos_data = cursor.fetchall()
        
        # Crear DataFrame
        data = []
        total_debe = 0
        total_haber = 0
        
        for row in asientos_data:
            debe_val = float(row.debe) if row.debe else 0.0
            haber_val = float(row.haber) if row.haber else 0.0
            
            data.append({
                'Consecutivo': row.consecutivo,
                'Cuenta': row.id_cuenta,
                'Fecha': row.fecha.strftime('%d/%m/%Y') if hasattr(row.fecha, 'strftime') else str(row.fecha),
                'Concepto': row.concepto,
                'Debe': debe_val,
                'Haber': haber_val,
                'Referencia': row.referencia or '',
                'Creado': row.creado_en.strftime('%d/%m/%Y %H:%M') if hasattr(row.creado_en, 'strftime') else str(row.creado_en)
            })
            
            total_debe += debe_val
            total_haber += haber_val
        
        # Agregar totales
        data.append({
            'Consecutivo': '',
            'Cuenta': '',
            'Fecha': '',
            'Concepto': 'TOTALES',
            'Debe': total_debe,
            'Haber': total_haber,
            'Referencia': 'CUADRADO' if total_debe == total_haber else 'NO CUADRADO',
            'Creado': ''
        })
        
        df = pd.DataFrame(data)
        
        # Crear respuesta Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Asientos', index=False)
            
            # Ajustar anchos de columna
            worksheet = writer.sheets['Asientos']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 30)
        
        output.seek(0)
        
        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=asientos_{tipo}_{folio}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Error al exportar asientos: {str(e)}', 'danger')
        return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
    finally:
        conn.close()

# Ruta para exportar asientos a PDF
@comprobantes_bp.route('/comprobantes/<tipo>/<folio>/asientos/exportar/pdf')
def asientos_pdf(tipo, folio):
    from config.db import get_connection
    
    # Obtener filtros
    id_cuenta = request.args.get('id_cuenta', '')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos del comprobante
        cursor.execute("""
            SELECT tipo, folio, fecha, concepto, total, estado
            FROM comprobantes 
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        comprobante_row = cursor.fetchone()
        
        if not comprobante_row:
            flash('Comprobante no encontrado', 'danger')
            return redirect(url_for('comprobantes.comprobantes'))
        
        # Construir query para asientos
        where_clauses = ["id_comprobante_tipo = ?", "id_comprobante_folio = ?"]
        params = [tipo, folio]
        
        if id_cuenta:
            where_clauses.append("id_cuenta LIKE ?")
            params.append(f'%{id_cuenta}%')
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT consecutivo, id_cuenta, fecha, concepto, 
                   debe, haber, referencia, creado_en
            FROM asientos_contables
            WHERE {where_sql}
            ORDER BY consecutivo
        """
        
        cursor.execute(query, params)
        asientos_data = cursor.fetchall()
        
        # Crear PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        
        # Título
        elements.append(Paragraph(f"Asientos - {comprobante_row.tipo}-{comprobante_row.folio}", title_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Información del comprobante
        info_text = f"""
        <b>Comprobante:</b> {comprobante_row.tipo}-{comprobante_row.folio}<br/>
        <b>Fecha:</b> {comprobante_row.fecha.strftime('%d/%m/%Y') if hasattr(comprobante_row.fecha, 'strftime') else str(comprobante_row.fecha)}<br/>
        <b>Concepto:</b> {comprobante_row.concepto}<br/>
        <b>Total:</b> ${float(comprobante_row.total):,.2f if comprobante_row.total else 0.0}<br/>
        <b>Estado:</b> {comprobante_row.estado}<br/>
        <b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        elements.append(Paragraph(info_text, normal_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Crear tabla de asientos
        data = [['#', 'Cuenta', 'Fecha', 'Concepto', 'Debe', 'Haber', 'Ref.']]
        
        total_debe = 0
        total_haber = 0
        
        for row in asientos_data:
            fecha_str = row.fecha.strftime('%d/%m/%Y') if hasattr(row.fecha, 'strftime') else str(row.fecha)
            concepto = row.concepto[:25] + '...' if len(row.concepto) > 25 else row.concepto
            debe_val = float(row.debe) if row.debe else 0.0
            haber_val = float(row.haber) if row.haber else 0.0
            
            data.append([
                str(row.consecutivo),
                row.id_cuenta,
                fecha_str,
                concepto,
                f"${debe_val:,.2f}" if debe_val > 0 else '',
                f"${haber_val:,.2f}" if haber_val > 0 else '',
                row.referencia[:10] if row.referencia else ''
            ])
            
            total_debe += debe_val
            total_haber += haber_val
        
        # Agregar totales
        data.append(['', '', '', 'TOTALES:', f"${total_debe:,.2f}", f"${total_haber:,.2f}", 
                    'CUADRADO' if total_debe == total_haber else 'NO CUADRADO'])
        
        # Crear tabla
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 1), (5, -2), 'RIGHT'),
            ('ALIGN', (4, -1), (5, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
            ('GRID', (3, -1), (5, -1), 0.5, colors.black),
        ]))
        
        elements.append(table)
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Crear respuesta
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=asientos_{tipo}_{folio}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'danger')
        return redirect(url_for('comprobantes.asientos', tipo=tipo, folio=folio))
    finally:
        conn.close()