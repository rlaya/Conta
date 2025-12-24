# cuentas_contables_saldos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# Crear Blueprint
cuentas_bp = Blueprint('cuentas', __name__, template_folder='templates/cuentas_contables')

# Formulario para Cuentas Contables
class CuentaContableForm(FlaskForm):
    codigo = StringField('Código', validators=[DataRequired(), Length(max=20)])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    tipo = SelectField('Tipo', choices=[
        ('Activo', 'Activo'),
        ('Pasivo', 'Pasivo'),
        ('Patrimonio', 'Patrimonio'),
        ('Ingreso', 'Ingreso'),
        ('Gasto', 'Gasto')
    ], validators=[DataRequired()])
    nivel = SelectField('Nivel', choices=[
        (1, '1 - Grupo'),
        (2, '2 - Subgrupo'),
        (3, '3 - Mayor'),
        (4, '4 - Submayor'),
        (5, '5 - Auxiliar')
    ], coerce=int, validators=[DataRequired()])
    id_cuenta_padre = SelectField('Cuenta Padre', validators=[Optional()], choices=[])
    naturaleza = SelectField('Naturaleza', choices=[
        ('Débito', 'Débito'),
        ('Crédito', 'Crédito')
    ], validators=[DataRequired()])

# Formulario para Saldos de Cuentas
class SaldoCuentaForm(FlaskForm):
    id_cuenta = SelectField('Cuenta Contable', validators=[DataRequired()], choices=[])
    periodo = IntegerField('Período', validators=[
        DataRequired(),
        NumberRange(min=2000, max=2100, message='El período debe ser un año válido')
    ])
    saldo_inicial = DecimalField('Saldo Inicial', validators=[DataRequired()], places=2)
    saldo_final = DecimalField('Saldo Final', validators=[DataRequired()], places=2)

# Ruta principal de cuentas contables
@cuentas_bp.route('/cuentas-contables')
def cuentas_contables():
    from app import db
    from models import CuentaContable
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Construir query con filtros
    query = CuentaContable.query
    
    # Aplicar filtros
    codigo = request.args.get('codigo')
    if codigo:
        query = query.filter(CuentaContable.codigo.ilike(f'%{codigo}%'))
    
    nombre = request.args.get('nombre')
    if nombre:
        query = query.filter(CuentaContable.nombre.ilike(f'%{nombre}%'))
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    nivel = request.args.get('nivel')
    if nivel:
        query = query.filter(CuentaContable.nivel == nivel)
    
    naturaleza = request.args.get('naturaleza')
    if naturaleza:
        query = query.filter(CuentaContable.naturaleza == naturaleza)
    
    id_cuenta_padre = request.args.get('id_cuenta_padre')
    if id_cuenta_padre:
        query = query.filter(CuentaContable.id_cuenta_padre == id_cuenta_padre)
    elif request.args.get('solo_padres'):
        query = query.filter(CuentaContable.id_cuenta_padre == None)
    
    # Ordenar por código
    query = query.order_by(CuentaContable.codigo)
    
    # Obtener cuentas padre para el filtro
    cuentas_padre = CuentaContable.query.filter(
        (CuentaContable.nivel == 1) | (CuentaContable.nivel == 2)
    ).order_by(CuentaContable.codigo).all()
    
    # Estadísticas
    total_cuentas = CuentaContable.query.count()
    cuenta_padre_count = CuentaContable.query.filter_by(id_cuenta_padre=None).count()
    nivel_1_count = CuentaContable.query.filter_by(nivel=1).count()
    nivel_2_count = CuentaContable.query.filter_by(nivel=2).count()
    nivel_3_count = CuentaContable.query.filter_by(nivel=3).count()
    nivel_4_count = CuentaContable.query.filter_by(nivel=4).count() + CuentaContable.query.filter_by(nivel=5).count()
    
    # Paginación
    cuentas_paginadas = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Contar cuentas hijas para cada cuenta
    for cuenta in cuentas_paginadas.items:
        cuenta.cuentas_hijas_count = CuentaContable.query.filter_by(id_cuenta_padre=cuenta.codigo).count()
        if cuenta.id_cuenta_padre:
            cuenta.cuenta_padre = CuentaContable.query.get(cuenta.id_cuenta_padre)
    
    return render_template('cuentas_contables/cuentas_contables.html',
                         cuentas=cuentas_paginadas,
                         cuentas_padre=cuentas_padre,
                         total_cuentas=total_cuentas,
                         cuenta_padre_count=cuenta_padre_count,
                         nivel_1_count=nivel_1_count,
                         nivel_2_count=nivel_2_count,
                         nivel_3_count=nivel_3_count,
                         nivel_4_count=nivel_4_count)

# Ruta para nueva cuenta contable
@cuentas_bp.route('/cuentas-contables/nueva', methods=['GET', 'POST'])
def nueva_cuenta_contable():
    from app import db
    from models import CuentaContable
    
    form = CuentaContableForm()
    
    # Obtener cuentas padre para el select
    cuentas_padre = CuentaContable.query.filter(
        CuentaContable.nivel.in_([1, 2, 3])
    ).order_by(CuentaContable.codigo).all()
    
    form.id_cuenta_padre.choices = [('', 'Seleccione...')] + [(c.codigo, f"{c.codigo} - {c.nombre}") for c in cuentas_padre]
    
    if form.validate_on_submit():
        try:
            # Verificar si el código ya existe
            cuenta_existente = CuentaContable.query.get(form.codigo.data)
            if cuenta_existente:
                flash('El código de cuenta ya existe!', 'danger')
            else:
                cuenta = CuentaContable(
                    codigo=form.codigo.data,
                    nombre=form.nombre.data,
                    tipo=form.tipo.data,
                    nivel=form.nivel.data,
                    id_cuenta_padre=form.id_cuenta_padre.data if form.id_cuenta_padre.data else None,
                    naturaleza=form.naturaleza.data
                )
                
                db.session.add(cuenta)
                db.session.commit()
                
                flash('Cuenta contable creada exitosamente!', 'success')
                return redirect(url_for('cuentas.cuentas_contables'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear cuenta: {str(e)}', 'danger')
    
    return render_template('cuentas_contables/form_cuentas_contables.html', form=form)

# Ruta para ver cuenta contable
@cuentas_bp.route('/cuentas-contables/<codigo>')
def ver_cuenta_contable(codigo):
    from models import CuentaContable, SaldoCuenta, AsientoContable
    
    cuenta = CuentaContable.query.get_or_404(codigo)
    
    # Obtener saldos recientes
    saldos = SaldoCuenta.query.filter_by(id_cuenta=codigo)\
        .order_by(SaldoCuenta.periodo.desc())\
        .limit(5).all()
    
    # Obtener asientos recientes
    asientos = AsientoContable.query.filter_by(id_cuenta=codigo)\
        .order_by(AsientoContable.fecha.desc())\
        .limit(10).all()
    
    # Obtener cuentas hijas
    cuentas_hijas = CuentaContable.query.filter_by(id_cuenta_padre=codigo)\
        .order_by(CuentaContable.codigo).all()
    
    return render_template('cuentas_contables/ver_cuenta.html',
                         cuenta=cuenta,
                         saldos=saldos,
                         asientos=asientos,
                         cuentas_hijas=cuentas_hijas)

# Ruta para editar cuenta contable
@cuentas_bp.route('/cuentas-contables/<codigo>/editar', methods=['GET', 'POST'])
def editar_cuenta_contable(codigo):
    from app import db
    from models import CuentaContable
    
    cuenta = CuentaContable.query.get_or_404(codigo)
    form = CuentaContableForm(obj=cuenta)
    
    # Obtener cuentas padre para el select (excluyendo la cuenta actual y sus hijas)
    cuentas_padre = CuentaContable.query.filter(
        CuentaContable.nivel.in_([1, 2, 3]),
        CuentaContable.codigo != codigo
    ).order_by(CuentaContable.codigo).all()
    
    # Filtrar para evitar referencias circulares
    cuentas_padre_filtradas = []
    for cp in cuentas_padre:
        # Verificar que no sea descendiente de la cuenta actual
        if not es_descendiente(cp.codigo, codigo):
            cuentas_padre_filtradas.append(cp)
    
    form.id_cuenta_padre.choices = [('', 'Seleccione...')] + [(c.codigo, f"{c.codigo} - {c.nombre}") for c in cuentas_padre_filtradas]
    
    if form.validate_on_submit():
        try:
            cuenta.nombre = form.nombre.data
            cuenta.tipo = form.tipo.data
            cuenta.nivel = form.nivel.data
            cuenta.id_cuenta_padre = form.id_cuenta_padre.data if form.id_cuenta_padre.data else None
            cuenta.naturaleza = form.naturaleza.data
            
            db.session.commit()
            flash('Cuenta contable actualizada exitosamente!', 'success')
            return redirect(url_for('cuentas.cuentas_contables'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cuenta: {str(e)}', 'danger')
    
    return render_template('cuentas_contables/form_cuentas_contables.html', form=form, cuenta=cuenta)

# Función auxiliar para verificar descendencia
def es_descendiente(cuenta_actual, posible_ancestro):
    from models import CuentaContable
    
    cuenta = CuentaContable.query.get(cuenta_actual)
    while cuenta and cuenta.id_cuenta_padre:
        if cuenta.id_cuenta_padre == posible_ancestro:
            return True
        cuenta = CuentaContable.query.get(cuenta.id_cuenta_padre)
    return False

# Ruta para eliminar cuenta contable
@cuentas_bp.route('/cuentas-contables/<codigo>/eliminar', methods=['POST'])
def eliminar_cuenta_contable(codigo):
    from app import db
    from models import CuentaContable, SaldoCuenta, AsientoContable
    
    try:
        cuenta = CuentaContable.query.get_or_404(codigo)
        
        # Eliminar cuentas hijas primero (en cascada)
        cuentas_hijas = CuentaContable.query.filter_by(id_cuenta_padre=codigo).all()
        for cuenta_hija in cuentas_hijas:
            eliminar_cuenta_recursiva(cuenta_hija.codigo)
        
        # Eliminar saldos relacionados
        SaldoCuenta.query.filter_by(id_cuenta=codigo).delete()
        
        # Eliminar la cuenta
        db.session.delete(cuenta)
        db.session.commit()
        
        flash('Cuenta contable eliminada exitosamente!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cuenta: {str(e)}', 'danger')
    
    return redirect(url_for('cuentas.cuentas_contables'))

# Función recursiva para eliminar cuentas hijas
def eliminar_cuenta_recursiva(codigo):
    from app import db
    from models import CuentaContable, SaldoCuenta
    
    cuenta = CuentaContable.query.get(codigo)
    if cuenta:
        # Eliminar cuentas hijas primero
        cuentas_hijas = CuentaContable.query.filter_by(id_cuenta_padre=codigo).all()
        for cuenta_hija in cuentas_hijas:
            eliminar_cuenta_recursiva(cuenta_hija.codigo)
        
        # Eliminar saldos
        SaldoCuenta.query.filter_by(id_cuenta=codigo).delete()
        
        # Eliminar la cuenta
        db.session.delete(cuenta)

# Ruta para exportar cuentas a Excel
@cuentas_bp.route('/cuentas-contables/exportar/excel')
def cuentas_contables_excel():
    from models import CuentaContable
    
    # Aplicar filtros
    query = CuentaContable.query
    
    codigo = request.args.get('codigo')
    if codigo:
        query = query.filter(CuentaContable.codigo.ilike(f'%{codigo}%'))
    
    nombre = request.args.get('nombre')
    if nombre:
        query = query.filter(CuentaContable.nombre.ilike(f'%{nombre}%'))
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    cuentas = query.order_by(CuentaContable.codigo).all()
    
    # Crear DataFrame
    data = []
    for c in cuentas:
        data.append({
            'Código': c.codigo,
            'Nombre': c.nombre,
            'Tipo': c.tipo,
            'Nivel': c.nivel,
            'Naturaleza': c.naturaleza,
            'Cuenta Padre': c.id_cuenta_padre or '',
            'Número de Hijos': CuentaContable.query.filter_by(id_cuenta_padre=c.codigo).count()
        })
    
    df = pd.DataFrame(data)
    
    # Crear respuesta Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Cuentas Contables', index=False)
        
        # Ajustar anchos de columna
        worksheet = writer.sheets['Cuentas Contables']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 30)
    
    output.seek(0)
    
    # Crear respuesta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=cuentas_contables.xlsx'
    
    return response

# Ruta para exportar cuentas a PDF
@cuentas_bp.route('/cuentas-contables/exportar/pdf')
def cuentas_contables_pdf():
    from models import CuentaContable
    
    # Aplicar filtros
    query = CuentaContable.query
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    nivel = request.args.get('nivel')
    if nivel:
        query = query.filter(CuentaContable.nivel == nivel)
    
    cuentas = query.order_by(CuentaContable.codigo).limit(100).all()
    
    # Crear PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    # Título
    elements.append(Paragraph("Plan de Cuentas Contables", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Información de filtros
    filtros_text = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if tipo:
        filtros_text += f" | Tipo: {tipo}"
    if nivel:
        filtros_text += f" | Nivel: {nivel}"
    
    elements.append(Paragraph(filtros_text, normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Estadísticas
    total_cuentas = len(cuentas)
    elementos = []
    
    for c in cuentas:
        # Determinar indentación según nivel
        indent = ""
        if c.nivel > 1:
            indent = "  " * (c.nivel - 1) + "• "
        
        cuenta_text = f"{indent}{c.codigo} - {c.nombre} ({c.tipo}, {c.naturaleza})"
        elementos.append(Paragraph(cuenta_text, normal_style))
    
    elements.extend(elementos)
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph(f"Total de cuentas: {total_cuentas}", normal_style))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Crear respuesta
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=cuentas_contables.pdf'
    
    return response

# Ruta para saldos de cuentas
@cuentas_bp.route('/saldos-cuentas')
def saldos_cuentas():
    from app import db
    from models import SaldoCuenta, CuentaContable
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Construir query con filtros
    query = SaldoCuenta.query.join(CuentaContable, SaldoCuenta.id_cuenta == CuentaContable.codigo)
    
    # Aplicar filtros
    id_cuenta = request.args.get('id_cuenta')
    if id_cuenta:
        query = query.filter(SaldoCuenta.id_cuenta == id_cuenta)
    
    periodo = request.args.get('periodo')
    if periodo:
        query = query.filter(SaldoCuenta.periodo == periodo)
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    mostrar = request.args.get('mostrar', 'todos')
    if mostrar == 'con_saldo':
        query = query.filter(SaldoCuenta.saldo_final != 0)
    elif mostrar == 'con_movimiento':
        query = query.filter(SaldoCuenta.saldo_final != SaldoCuenta.saldo_inicial)
    
    # Ordenar
    ordenar = request.args.get('ordenar', 'periodo_desc')
    if ordenar == 'periodo_desc':
        query = query.order_by(SaldoCuenta.periodo.desc(), SaldoCuenta.id_cuenta)
    elif ordenar == 'periodo_asc':
        query = query.order_by(SaldoCuenta.periodo.asc(), SaldoCuenta.id_cuenta)
    elif ordenar == 'saldo_desc':
        query = query.order_by(SaldoCuenta.saldo_final.desc())
    elif ordenar == 'saldo_asc':
        query = query.order_by(SaldoCuenta.saldo_final.asc())
    
    # Obtener todas las cuentas para el filtro
    todas_cuentas = CuentaContable.query.order_by(CuentaContable.codigo).all()
    
    # Obtener períodos disponibles
    periodos_disponibles = db.session.query(SaldoCuenta.periodo)\
        .distinct()\
        .order_by(SaldoCuenta.periodo.desc())\
        .all()
    periodos_disponibles = [p[0] for p in periodos_disponibles]
    
    # Paginación
    saldos_paginados = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Estadísticas
    total_saldos = query.count()
    total_saldo_final = db.session.query(db.func.sum(SaldoCuenta.saldo_final)).scalar() or 0
    periodos_unicos = db.session.query(SaldoCuenta.periodo).distinct().count()
    cuentas_con_saldo = db.session.query(SaldoCuenta.id_cuenta).distinct().count()
    
    return render_template('cuentas_contables/saldos_cuentas.html',
                         saldos=saldos_paginados,
                         todas_cuentas=todas_cuentas,
                         periodos_disponibles=periodos_disponibles,
                         total_saldos=total_saldos,
                         total_saldo_final=total_saldo_final,
                         periodos_unicos=periodos_unicos,
                         cuentas_con_saldo=cuentas_con_saldo)

# Ruta para nuevo saldo de cuenta
@cuentas_bp.route('/saldos-cuentas/nuevo', methods=['GET', 'POST'])
def nuevo_saldo_cuenta():
    from app import db
    from models import SaldoCuenta, CuentaContable
    
    form = SaldoCuentaForm()
    
    # Obtener cuentas para el select
    cuentas = CuentaContable.query.order_by(CuentaContable.codigo).all()
    form.id_cuenta.choices = [('', 'Seleccione...')] + [(c.codigo, f"{c.codigo} - {c.nombre}") for c in cuentas]
    
    if form.validate_on_submit():
        try:
            # Verificar si ya existe saldo para esta cuenta y período
            saldo_existente = SaldoCuenta.query.filter_by(
                id_cuenta=form.id_cuenta.data,
                periodo=form.periodo.data
            ).first()
            
            if saldo_existente:
                flash('Ya existe un saldo para esta cuenta y período!', 'danger')
            else:
                saldo = SaldoCuenta(
                    id_cuenta=form.id_cuenta.data,
                    periodo=form.periodo.data,
                    saldo_inicial=form.saldo_inicial.data,
                    saldo_final=form.saldo_final.data
                )
                
                db.session.add(saldo)
                db.session.commit()
                
                flash('Saldo de cuenta creado exitosamente!', 'success')
                return redirect(url_for('cuentas.saldos_cuentas'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear saldo: {str(e)}', 'danger')
    
    return render_template('cuentas_contables/form_saldos_cuentas.html', form=form)

# Ruta para editar saldo de cuenta
@cuentas_bp.route('/saldos-cuentas/<id_cuenta>/<int:periodo>/editar', methods=['GET', 'POST'])
def editar_saldo_cuenta(id_cuenta, periodo):
    from app import db
    from models import SaldoCuenta, CuentaContable
    
    saldo = SaldoCuenta.query.filter_by(id_cuenta=id_cuenta, periodo=periodo).first_or_404()
    form = SaldoCuentaForm(obj=saldo)
    
    # Obtener cuenta para mostrar información
    cuenta = CuentaContable.query.get_or_404(id_cuenta)
    
    if form.validate_on_submit():
        try:
            saldo.saldo_inicial = form.saldo_inicial.data
            saldo.saldo_final = form.saldo_final.data
            
            db.session.commit()
            flash('Saldo de cuenta actualizado exitosamente!', 'success')
            return redirect(url_for('cuentas.saldos_cuentas'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar saldo: {str(e)}', 'danger')
    
    return render_template('cuentas_contables/form_saldos_cuentas.html', 
                         form=form, 
                         saldo=saldo)

# Ruta para eliminar saldo de cuenta
@cuentas_bp.route('/saldos-cuentas/<id_cuenta>/<int:periodo>/eliminar', methods=['POST'])
def eliminar_saldo_cuenta(id_cuenta, periodo):
    from app import db
    from models import SaldoCuenta
    
    try:
        saldo = SaldoCuenta.query.filter_by(id_cuenta=id_cuenta, periodo=periodo).first_or_404()
        
        db.session.delete(saldo)
        db.session.commit()
        
        flash('Saldo de cuenta eliminado exitosamente!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar saldo: {str(e)}', 'danger')
    
    return redirect(url_for('cuentas.saldos_cuentas'))

# Ruta para calcular saldo final automáticamente
@cuentas_bp.route('/saldos-cuentas/<id_cuenta>/<int:periodo>/calcular', methods=['GET'])
def calcular_saldo_final(id_cuenta, periodo):
    from app import db
    from models import SaldoCuenta, CuentaContable, AsientoContable
    
    try:
        saldo = SaldoCuenta.query.filter_by(id_cuenta=id_cuenta, periodo=periodo).first_or_404()
        cuenta = CuentaContable.query.get_or_404(id_cuenta)
        
        # Calcular movimiento del período
        # Suponemos que los asientos tienen fecha dentro del período
        movimiento_debe = db.session.query(db.func.sum(AsientoContable.debe))\
            .filter(
                AsientoContable.id_cuenta == id_cuenta,
                db.extract('year', AsientoContable.fecha) == periodo
            ).scalar() or 0
        
        movimiento_haber = db.session.query(db.func.sum(AsientoContable.haber))\
            .filter(
                AsientoContable.id_cuenta == id_cuenta,
                db.extract('year', AsientoContable.fecha) == periodo
            ).scalar() or 0
        
        # Calcular saldo final basado en la naturaleza de la cuenta
        if cuenta.naturaleza == 'Débito':
            # Para cuentas de débito: Saldo Inicial + Débitos - Créditos
            saldo_final = float(saldo.saldo_inicial) + float(movimiento_debe) - float(movimiento_haber)
        else:
            # Para cuentas de crédito: Saldo Inicial + Créditos - Débitos
            saldo_final = float(saldo.saldo_inicial) + float(movimiento_haber) - float(movimiento_debe)
        
        saldo.saldo_final = saldo_final
        db.session.commit()
        
        flash(f'Saldo final calculado: ${saldo_final:,.2f}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al calcular saldo: {str(e)}', 'danger')
    
    return redirect(url_for('cuentas.editar_saldo_cuenta', id_cuenta=id_cuenta, periodo=periodo))

# Ruta para procesar movimientos de un comprobante
@cuentas_bp.route('/procesar-movimientos/<id_cuenta>/<int:periodo>', methods=['GET'])
def procesar_movimientos(id_cuenta, periodo):
    from app import db
    from models import SaldoCuenta, CuentaContable, AsientoContable
    
    try:
        cuenta = CuentaContable.query.get_or_404(id_cuenta)
        
        # Obtener o crear saldo para el período
        saldo = SaldoCuenta.query.filter_by(id_cuenta=id_cuenta, periodo=periodo).first()
        if not saldo:
            saldo = SaldoCuenta(
                id_cuenta=id_cuenta,
                periodo=periodo,
                saldo_inicial=0,
                saldo_final=0
            )
            db.session.add(saldo)
        
        # Calcular movimiento del período
        movimiento_debe = db.session.query(db.func.sum(AsientoContable.debe))\
            .filter(
                AsientoContable.id_cuenta == id_cuenta,
                db.extract('year', AsientoContable.fecha) == periodo
            ).scalar() or 0
        
        movimiento_haber = db.session.query(db.func.sum(AsientoContable.haber))\
            .filter(
                AsientoContable.id_cuenta == id_cuenta,
                db.extract('year', AsientoContable.fecha) == periodo
            ).scalar() or 0
        
        # Calcular saldo final
        if cuenta.naturaleza == 'Débito':
            saldo_final = float(saldo.saldo_inicial) + float(movimiento_debe) - float(movimiento_haber)
        else:
            saldo_final = float(saldo.saldo_inicial) + float(movimiento_haber) - float(movimiento_debe)
        
        saldo.saldo_final = saldo_final
        db.session.commit()
        
        flash(f'Movimientos procesados. Saldo final: ${saldo_final:,.2f}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar movimientos: {str(e)}', 'danger')
    
    return redirect(url_for('cuentas.saldos_cuentas'))

# Ruta para procesar TODOS los saldos de un período
@cuentas_bp.route('/procesar-todos-saldos/<int:periodo>', methods=['GET'])
def procesar_todos_saldos(periodo):
    from app import db
    from models import CuentaContable, SaldoCuenta, AsientoContable
    
    try:
        # Obtener todas las cuentas
        cuentas = CuentaContable.query.all()
        
        procesadas = 0
        for cuenta in cuentas:
            # Obtener o crear saldo
            saldo = SaldoCuenta.query.filter_by(id_cuenta=cuenta.codigo, periodo=periodo).first()
            if not saldo:
                saldo = SaldoCuenta(
                    id_cuenta=cuenta.codigo,
                    periodo=periodo,
                    saldo_inicial=0,
                    saldo_final=0
                )
                db.session.add(saldo)
            
            # Calcular movimientos
            movimiento_debe = db.session.query(db.func.sum(AsientoContable.debe))\
                .filter(
                    AsientoContable.id_cuenta == cuenta.codigo,
                    db.extract('year', AsientoContable.fecha) == periodo
                ).scalar() or 0
            
            movimiento_haber = db.session.query(db.func.sum(AsientoContable.haber))\
                .filter(
                    AsientoContable.id_cuenta == cuenta.codigo,
                    db.extract('year', AsientoContable.fecha) == periodo
                ).scalar() or 0
            
            # Calcular saldo final
            if cuenta.naturaleza == 'Débito':
                saldo_final = float(saldo.saldo_inicial) + float(movimiento_debe) - float(movimiento_haber)
            else:
                saldo_final = float(saldo.saldo_inicial) + float(movimiento_haber) - float(movimiento_debe)
            
            saldo.saldo_final = saldo_final
            procesadas += 1
        
        db.session.commit()
        flash(f'Procesados {procesadas} saldos para el período {periodo}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar saldos: {str(e)}', 'danger')
    
    return redirect(url_for('cuentas.saldos_cuentas'))

# Ruta para exportar saldos a Excel
@cuentas_bp.route('/saldos-cuentas/exportar/excel')
def saldos_cuentas_excel():
    from models import SaldoCuenta, CuentaContable
    
    # Aplicar filtros
    query = SaldoCuenta.query.join(CuentaContable, SaldoCuenta.id_cuenta == CuentaContable.codigo)
    
    id_cuenta = request.args.get('id_cuenta')
    if id_cuenta:
        query = query.filter(SaldoCuenta.id_cuenta == id_cuenta)
    
    periodo = request.args.get('periodo')
    if periodo:
        query = query.filter(SaldoCuenta.periodo == periodo)
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    # Ordenar
    query = query.order_by(SaldoCuenta.periodo.desc(), SaldoCuenta.id_cuenta)
    
    saldos = query.all()
    
    # Crear DataFrame
    data = []
    for s in saldos:
        movimiento = float(s.saldo_final) - float(s.saldo_inicial)
        data.append({
            'Cuenta': s.id_cuenta,
            'Nombre Cuenta': s.cuenta.nombre,
            'Tipo': s.cuenta.tipo,
            'Naturaleza': s.cuenta.naturaleza,
            'Período': s.periodo,
            'Saldo Inicial': float(s.saldo_inicial),
            'Saldo Final': float(s.saldo_final),
            'Movimiento': movimiento,
            'Actualizado': s.creado_en.strftime('%d/%m/%Y %H:%M')
        })
    
    df = pd.DataFrame(data)
    
    # Crear respuesta Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Saldos de Cuentas', index=False)
        
        # Ajustar anchos de columna
        worksheet = writer.sheets['Saldos de Cuentas']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 25)
    
    output.seek(0)
    
    # Crear respuesta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=saldos_cuentas.xlsx'
    
    return response

# Ruta para exportar saldos a PDF
@cuentas_bp.route('/saldos-cuentas/exportar/pdf')
def saldos_cuentas_pdf():
    from models import SaldoCuenta, CuentaContable
    
    # Aplicar filtros
    query = SaldoCuenta.query.join(CuentaContable, SaldoCuenta.id_cuenta == CuentaContable.codigo)
    
    periodo = request.args.get('periodo')
    if periodo:
        query = query.filter(SaldoCuenta.periodo == periodo)
    
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter(CuentaContable.tipo == tipo)
    
    # Ordenar por tipo y cuenta
    query = query.order_by(CuentaContable.tipo, SaldoCuenta.id_cuenta)
    
    saldos = query.limit(100).all()
    
    # Agrupar por tipo
    saldos_por_tipo = {}
    for s in saldos:
        tipo = s.cuenta.tipo
        if tipo not in saldos_por_tipo:
            saldos_por_tipo[tipo] = []
        saldos_por_tipo[tipo].append(s)
    
    # Crear PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Título
    elements.append(Paragraph("Reporte de Saldos de Cuentas", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Información
    info_text = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if periodo:
        info_text += f" | Período: {periodo}"
    
    elements.append(Paragraph(info_text, normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Total por tipo
    total_general = 0
    for tipo, saldos_tipo in saldos_por_tipo.items():
        elements.append(Paragraph(tipo, heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Crear tabla para este tipo
        data = [['Cuenta', 'Nombre', 'Saldo Inicial', 'Saldo Final', 'Movimiento']]
        
        total_tipo = 0
        for s in saldos_tipo:
            movimiento = float(s.saldo_final) - float(s.saldo_inicial)
            data.append([
                s.id_cuenta,
                s.cuenta.nombre[:30] + ('...' if len(s.cuenta.nombre) > 30 else ''),
                f"${float(s.saldo_inicial):,.2f}",
                f"${float(s.saldo_final):,.2f}",
                f"${movimiento:,.2f}" if movimiento != 0 else "$0.00"
            ])
            total_tipo += float(s.saldo_final)
        
        # Agregar total del tipo
        data.append(['', 'TOTAL ' + tipo.upper(), '', f"${total_tipo:,.2f}", ''])
        total_general += total_tipo
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.25*inch))
    
    # Total general
    elements.append(Paragraph(f"TOTAL GENERAL: ${total_general:,.2f}", styles['Heading1']))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Crear respuesta
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=saldos_cuentas.pdf'
    
    return response

# Función para procesar un comprobante y actualizar saldos
def procesar_comprobante_contable(tipo, folio):
    """
    Procesa un comprobante y actualiza los saldos de las cuentas involucradas.
    Se ejecuta cuando un comprobante está 'cuadrado' y tiene cuentas apropiadas.
    """
    from app import db
    from models import Comprobante, AsientoContable, CuentaContable, SaldoCuenta
    
    try:
        comprobante = Comprobante.query.filter_by(tipo=tipo, folio=folio).first()
        if not comprobante:
            return False, "Comprobante no encontrado"
        
        # Verificar que el comprobante esté cuadrado
        if comprobante.estado != 'Registrado':
            return False, "El comprobante no está en estado 'Registrado'"
        
        # Obtener todos los asientos del comprobante
        asientos = AsientoContable.query.filter_by(
            id_comprobante_tipo=tipo,
            id_comprobante_folio=folio
        ).all()
        
        # Verificar que el comprobante esté cuadrado (suma de débitos = suma de créditos)
        total_debe = sum(float(a.debe) for a in asientos)
        total_haber = sum(float(a.haber) for a in asientos)
        
        if abs(total_debe - total_haber) > 0.01:  # Tolerancia de 0.01
            return False, f"Comprobante no cuadrado: Débito ${total_debe:,.2f} ≠ Crédito ${total_haber:,.2f}"
        
        # Obtener el período del comprobante (año de la fecha)
        periodo = comprobante.fecha.year
        
        # Procesar cada asiento
        for asiento in asientos:
            cuenta = CuentaContable.query.get(asiento.id_cuenta)
            if not cuenta:
                continue
            
            # Obtener o crear saldo para la cuenta y período
            saldo = SaldoCuenta.query.filter_by(id_cuenta=asiento.id_cuenta, periodo=periodo).first()
            if not saldo:
                # Buscar saldo del período anterior
                saldo_anterior = SaldoCuenta.query.filter_by(id_cuenta=asiento.id_cuenta)\
                    .filter(SaldoCuenta.periodo < periodo)\
                    .order_by(SaldoCuenta.periodo.desc())\
                    .first()
                
                saldo_inicial = saldo_anterior.saldo_final if saldo_anterior else 0
                saldo = SaldoCuenta(
                    id_cuenta=asiento.id_cuenta,
                    periodo=periodo,
                    saldo_inicial=saldo_inicial,
                    saldo_final=saldo_inicial
                )
                db.session.add(saldo)
            
            # Actualizar saldo final según la naturaleza de la cuenta
            if cuenta.naturaleza == 'Débito':
                # Débitos aumentan, créditos disminuyen
                saldo.saldo_final += float(asiento.debe) - float(asiento.haber)
            else:
                # Créditos aumentan, débitos disminuyen
                saldo.saldo_final += float(asiento.haber) - float(asiento.debe)
        
        db.session.commit()
        return True, "Comprobante procesado exitosamente"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error al procesar comprobante: {str(e)}"