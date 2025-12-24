# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file #, jsonifyMODEL
from auth.login import authenticate_user


from models.factura import (
    listar_facturas,
    cancelar_factura_con_anulacion,
    cancelar_factura,
    crear_factura_db,
    obtener_factura_por_id,
    actualizar_factura_db,
    eliminar_factura_db,
    get_terceros
)


from models.conciliacion import get_cuentas_bancarias, crear_conciliacion, listar_conciliaciones
from models.dashboard_avanzado import DashboardAvanzado



# Exportaciones
from utils.export import exportar_facturas_a_excel
from utils.pdf import exportar_facturas_a_pdf
from utils.pdf import exportar_factura_individual_a_pdf
from utils.export2 import exportar_asientos_a_excel
from utils.pdf2 import exportar_asientos_a_pdf

import io
from io import BytesIO
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura'  # Cambia en producción

# ======================
# INICIALIZAR DASHBOARD
# ======================
dashboard = DashboardAvanzado()

# ======================
# RUTAS PÚBLICAS
# ======================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = authenticate_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['nombre'] = user['nombre']
            session['rol_id'] = user['rol_id']
            return redirect(url_for('menu'))
        else:
            flash('Credenciales inválidas', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ======================
# RUTAS PROTEGIDAS
# ======================

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html', rol_id=session['rol_id'], nombre=session['nombre'])


@app.route('/contabilidad')
def contabilidad():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    return "<h2>Módulo de Contabilidad (Contador)</h2>"

@app.route('/consultas')
def consultas():
    if session.get('rol_id') not in [1, 2, 3]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    return "<h2>Consultas Básicas (Auxiliar)</h2>"

# ======================
# FACTURAS
# ======================expor

@app.route('/facturas')
def facturas_view():
    if session.get('rol_id') not in [1, 2, 3]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    tipo = request.args.get('tipo')
    facturas = listar_facturas(fecha_inicio, fecha_fin, tipo)

    return render_template('facturas/listar.html',
                          facturas=facturas,
                          filtros={
                              'fecha_inicio': fecha_inicio,
                              'fecha_fin': fecha_fin,
                              'tipo': tipo
                          })

@app.route('/facturas/<int:id_factura>')
def ver_factura(id_factura):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    # Llama a la función corregida, que ahora devuelve un diccionario o None
    factura = obtener_factura_por_id(id_factura) 

    if not factura:
        flash('Factura no encontrada', 'error')
        return redirect(url_for('facturas_view'))
        
    # El diccionario 'factura' ya contiene 'tercero_nombre' y 'id_asiento'
    return render_template('facturas/detalle.html', factura=factura)

@app.route('/facturas/crear', methods=['GET', 'POST'])
def crear_factura():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            folio = request.form['folio']
            fecha = request.form['fecha']
            fecha_vencimiento = request.form.get('fecha_vencimiento') or None
            total = float(request.form['total'])
            id_tercero = int(request.form['id_tercero'])

            terceros = get_terceros()
            tercero = next((t for t in terceros if t['id'] == id_tercero), None)
            if not tercero:
                raise ValueError("Tercero no válido")

            id_cliente = id_tercero if tercero['tipo'] == 'cliente' else None
            id_proveedor = id_tercero if tercero['tipo'] == 'proveedor' else None

            id_factura = crear_factura_db(
                tipo=tipo,
                folio=folio,
                fecha=fecha,
                fecha_vencimiento=fecha_vencimiento,
                total=total,
                id_cliente=id_cliente,
                id_proveedor=id_proveedor
            )
            flash(f'Factura creada con ID: {id_factura}', 'success')
            return redirect(url_for('facturas_view'))
        except Exception as e:
            flash(f'Error al crear factura: {str(e)}', 'error')

    terceros = get_terceros()
    return render_template('facturas/crear.html', terceros=terceros)

@app.route('/facturas/editar/<int:id_factura>', methods=['GET', 'POST'])
def editar_factura(id_factura):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    if request.method == 'POST':
        try:
            actualizar_factura_db(
                id_factura=id_factura,
                tipo=request.form['tipo'],
                folio=request.form['folio'],
                fecha=request.form['fecha'],
                fecha_vencimiento=request.form.get('fecha_vencimiento') or None,
                total=float(request.form['total']),
                estatus=request.form['estatus']
            )
            flash('Factura actualizada correctamente', 'success')
            return redirect(url_for('facturas_view'))
        except Exception as e:
            flash(f'Error al actualizar factura: {str(e)}', 'error')

    factura = obtener_factura_por_id(id_factura)
    if not factura:
        flash('Factura no encontrada', 'error')
        return redirect(url_for('facturas_view'))

    
    return render_template('facturas/editar.html', factura=factura)
 

@app.route('/facturas/eliminar/<int:id_factura>', methods=['POST'])
def eliminar_factura(id_factura):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    try:
        eliminar_factura_db(id_factura)
        flash('Factura eliminada correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar factura: {str(e)}', 'error')
    
    return redirect(url_for('facturas_view'))

@app.route('/facturas/cancelar/<int:id_factura>', methods=['POST'])
def cancelar_factura_view(id_factura):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('facturas_view'))
    try:
        id_asiento_anul = cancelar_factura_con_anulacion(id_factura, session['user_id'])
        flash(f'Factura cancelada. Asiento de anulación: {id_asiento_anul}', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('facturas_view'))

# --- Exportaciones de facturas ---
@app.route('/facturas/exportar')
def exportar_facturas():
    facturas = listar_facturas()
    output = exportar_facturas_a_excel(facturas)
    return send_file(
        io.BytesIO(output.getvalue()),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='facturas.xlsx'
    )

@app.route('/facturas/exportar-pdf')
def exportar_facturas_pdf():
    facturas = listar_facturas()
    pdf_buffer = exportar_facturas_a_pdf(facturas)
    return send_file(
        pdf_buffer,
        mimetype='utils.pdf2',
        as_attachment=True,
        download_name='facturas.pdf'
    )

@app.route('/facturas/exportar-pdf/<int:id_factura>')
def exportar_factura_pdf_individual(id_factura):
    # Usar la función corregida para obtener el diccionario completo
    factura = obtener_factura_por_id(id_factura) 
    
    if not factura:
        flash('Factura no encontrada', 'error')
        return redirect(url_for('facturas_view'))

    # Llama a la nueva función del modelo en utils/pdf.py
    pdf_buffer = exportar_factura_individual_a_pdf(factura) 
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'factura_{factura["folio"]}.pdf'
    )   

# ======================
# ASIENTOS
# ======================

@app.route('/asientos')
def asientos_listar():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    id_cliente = request.args.get('id_cliente', type=int)
    id_proveedor = request.args.get('id_proveedor', type=int)
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    concepto = request.args.get('concepto', '').strip()

    clientes = get_clientes()
    proveedores = get_proveedores()
    asientos, total = listar_asientos_con_filtros(
        id_cliente=id_cliente,
        id_proveedor=id_proveedor,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        concepto=concepto,
        page=page,
        per_page=per_page
    )

    total_pages = (total + per_page - 1) // per_page
    query_args = {k: v for k, v in request.args.items() if k != 'page'}
    base_url = url_for('asientos_listar') + '?' + urlencode(query_args) if query_args else url_for('asientos_listar')

    return render_template(
        'asientos/listar.html',
        asientos=asientos,
        clientes=clientes,
        proveedores=proveedores,
        total=total,
        page=page,
        total_pages=total_pages,
        base_url=base_url,
        concepto=concepto,
        filtros={
            'id_cliente': id_cliente,
            'id_proveedor': id_proveedor,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'concepto': concepto
        }
    )

@app.route('/asientos/<int:id_asiento>')
def ver_asiento(id_asiento):
    asiento, partidas = obtener_asiento_con_partidas(id_asiento)
    if not asiento:
        flash('Asiento no encontrado', 'error')
        return redirect(url_for('menu'))
    return render_template('asientos/detalle.html', asiento=asiento, partidas=partidas)

@app.route('/asientos/crear', methods=['GET', 'POST'])
def crear_asiento_view():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))

    diarios = get_diarios()
    cuentas = get_plan_cuentas()
    clientes = get_clientes()
    proveedores = get_proveedores()

    if request.method == 'POST':
        try:
            fecha = request.form['fecha']
            concepto = request.form['concepto'].strip()
            referencia = request.form['referencia'].strip()
            id_diario = int(request.form['id_diario'])
            id_usuario = session['user_id']

            cuenta_ids = request.form.getlist('id_cuenta[]')
            debe_vals = request.form.getlist('debe[]')
            haber_vals = request.form.getlist('haber[]')
            concepto_detallado_vals = request.form.getlist('concepto_detallado[]')
            cliente_ids = request.form.getlist('id_cliente[]')
            proveedor_ids = request.form.getlist('id_proveedor[]')            

            if not cuenta_ids or len(cuenta_ids) == 0:
                raise ValueError("Debe agregar al menos una partida.")

            partidas = []
            total_debe = Decimal('0.00')
            total_haber = Decimal('0.00')

            for i in range(len(cuenta_ids)):
                id_cuenta = cuenta_ids[i]
                if not id_cuenta:
                    continue

                id_cliente = cliente_ids[i] if cliente_ids[i] else None
                id_proveedor = proveedor_ids[i] if proveedor_ids[i] else None

                if id_cliente and id_proveedor:
                    raise ValueError("Una partida no puede tener cliente y proveedor al mismo tiempo.")

                debe_str = (debe_vals[i] or '').strip()
                haber_str = (haber_vals[i] or '').strip()
                concepto_det = (concepto_detallado_vals[i] or '').strip()

                debe = Decimal(debe_str) if debe_str else Decimal('0.00')
                haber = Decimal(haber_str) if haber_str else Decimal('0.00')

                if debe == 0 and haber == 0:
                    continue

                partidas.append({
                    'id_cuenta': int(id_cuenta),
                    'debe': float(debe),
                    'haber': float(haber),
                    'concepto_detallado': concepto_det,
                    'id_cliente': int(id_cliente) if id_cliente else None,
                    'id_proveedor': int(id_proveedor) if id_proveedor else None
                })

                total_debe += debe
                total_haber += haber

            if len(partidas) == 0:
                raise ValueError("No se agregaron partidas válidas.")

            if abs(total_debe - total_haber) > Decimal('0.01'):
                raise ValueError(f"El asiento no está balanceado. Debe: {total_debe}, Haber: {total_haber}")

            id_asiento = crear_asiento(fecha, concepto, referencia, id_diario, id_usuario, partidas)
            flash(f'Asiento creado exitosamente con ID: {id_asiento}', 'success')
            return redirect(url_for('asientos_listar'))

        except InvalidOperation:
            flash('Formato de número inválido en debe o haber.', 'error')
        except ValueError as e:
            flash(f'Error de validación: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error al crear el asiento: {str(e)}', 'error')

    return render_template('asientos/crear.html',
        diarios=diarios,
        cuentas=cuentas,
        clientes=clientes,
        proveedores=proveedores
    )

@app.route('/asientos/<int:id_asiento>/anular', methods=['POST'])
def anular_asiento_view(id_asiento):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    try:
        id_anul = anular_asiento(id_asiento, session['user_id'])
        flash(f'Asiento anulado. Nuevo asiento de anulación: {id_anul}', 'success')
    except Exception as e:
        flash(f'Error al anular asiento: {str(e)}', 'error')
    
    return redirect(url_for('ver_asiento', id_asiento=id_asiento))

# --- Exportaciones de asientos ---
@app.route('/asientos/exportar-excel')
def exportar_asientos_excel():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))

    id_cliente = request.args.get('id_cliente', type=int)
    id_proveedor = request.args.get('id_proveedor', type=int)
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    concepto = request.args.get('concepto', '').strip()

    from config.db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            a.id_asiento, a.fecha, a.concepto, a.referencia,
            d.nombre AS diario, u.nombre AS creador,
            c.nombre AS cliente, pr.nombre AS proveedor
        FROM asientos a
        JOIN diarios d ON a.id_diario = d.id_diario
        JOIN usuarios u ON a.id_usuario_creador = u.id_usuario
        LEFT JOIN partidas p ON a.id_asiento = p.id_asiento
        LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
        LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor
        WHERE 1=1
    """
    params = []
    if id_cliente:
        query += " AND p.id_cliente = ?"
        params.append(id_cliente)
    if id_proveedor:
        query += " AND p.id_proveedor = ?"
        params.append(id_proveedor)
    if fecha_inicio:
        query += " AND a.fecha >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND a.fecha <= ?"
        params.append(fecha_fin)
    if concepto:
        query += " AND a.concepto LIKE ?"
        params.append(f"%{concepto}%")

    query += """
        GROUP BY a.id_asiento, a.fecha, a.concepto, a.referencia, d.nombre, u.nombre, c.nombre, pr.nombre
        ORDER BY a.fecha DESC, a.id_asiento DESC
    """

    cursor.execute(query, params)
    asientos = cursor.fetchall()
    conn.close()

    output = exportar_asientos_a_excel(asientos)
    return send_file(
        BytesIO(output.getvalue()),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='asientos.xlsx'
    )

@app.route('/asientos/exportar-pdf')
def exportar_asientos_pdf():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))

    id_cliente = request.args.get('id_cliente', type=int)
    id_proveedor = request.args.get('id_proveedor', type=int)
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    concepto = request.args.get('concepto', '').strip()

    from config.db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            a.id_asiento, a.fecha, a.concepto, a.referencia,
            d.nombre AS diario, u.nombre AS creador,
            c.nombre AS cliente, pr.nombre AS proveedor
        FROM asientos a
        JOIN diarios d ON a.id_diario = d.id_diario
        JOIN usuarios u ON a.id_usuario_creador = u.id_usuario
        LEFT JOIN partidas p ON a.id_asiento = p.id_asiento
        LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
        LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor
        WHERE 1=1
    """
    params = []
    if id_cliente:
        query += " AND p.id_cliente = ?"
        params.append(id_cliente)
    if id_proveedor:
        query += " AND p.id_proveedor = ?"
        params.append(id_proveedor)
    if fecha_inicio:
        query += " AND a.fecha >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND a.fecha <= ?"
        params.append(fecha_fin)
    if concepto:
        query += " AND a.concepto LIKE ?"
        params.append(f"%{concepto}%")

    query += """
        GROUP BY a.id_asiento, a.fecha, a.concepto, a.referencia, d.nombre, u.nombre, c.nombre, pr.nombre
        ORDER BY a.fecha DESC, a.id_asiento DESC
    """

    cursor.execute(query, params)
    asientos = cursor.fetchall()
    conn.close()

    pdf_buffer = exportar_asientos_a_pdf(asientos)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='asientos.pdf'
    )

# ======================
# CONCILIACIONES
# ======================

@app.route('/conciliaciones')
def conciliaciones_listar():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    conciliaciones = listar_conciliaciones()
    return render_template('conciliaciones/listar.html', conciliaciones=conciliaciones)

@app.route('/conciliaciones/crear', methods=['GET', 'POST'])
def conciliaciones_crear():
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    cuentas = get_cuentas_bancarias()
    
    if request.method == 'POST':
        try:
            id_cuenta = int(request.form['id_cuenta'])
            fecha_inicio = request.form['fecha_inicio']
            fecha_fin = request.form['fecha_fin']
            saldo_banco = float(request.form['saldo_banco'])
            
            id_conc = crear_conciliacion(id_cuenta, fecha_inicio, fecha_fin, saldo_banco)
            flash(f'Conciliación creada con ID: {id_conc}', 'success')
            return redirect(url_for('conciliaciones_listar'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('conciliaciones/crear.html', cuentas=cuentas)


@app.route('/conciliaciones/<int:id_conc>/conciliar', methods=['GET', 'POST'])
def conciliar_conciliacion_view(id_conc):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('conciliaciones_listar'))
    
    from models.conciliacion import conciliar_conciliacion, listar_conciliaciones
    
    if request.method == 'POST':
        try:
            saldo_sistema = float(request.form['saldo_sistema'])
            observaciones = request.form.get('observaciones', '')
            conciliar_conciliacion(id_conc, session['user_id'], saldo_sistema, observaciones)
            flash('Conciliación marcada como conciliada exitosamente.', 'success')
            return redirect(url_for('conciliaciones_listar'))
        except Exception as e:
            flash(f'Error al conciliar: {str(e)}', 'error')
    
    # Cargar datos de la conciliación para el formulario
    conciliaciones = listar_conciliaciones()
    conciliacion = None
    for c in conciliaciones:
        if c[0] == id_conc:
            conciliacion = {
                'id_conciliacion': c[0],
                'nombre_banco': c[1],
                'fecha_inicio': c[2],
                'fecha_fin': c[3],
                'saldo_banco': c[4],
                'saldo_sistema': c[5],
                'diferencia': c[6],
                'estatus': c[7]
            }
            break
    
    if not conciliacion:
        flash('Conciliación no encontrada.', 'error')
        return redirect(url_for('conciliaciones_listar'))
    
    return render_template('conciliaciones/conciliar.html', conciliacion=conciliacion) 

@app.route('/conciliaciones/<int:id_conc>')
def ver_conciliacion(id_conc):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                c.id_conciliacion,
                cb.nombre_banco,
                cb.numero_cuenta,
                c.fecha_inicio,
                c.fecha_fin,
                c.saldo_banco,
                c.saldo_sistema,
                c.diferencia,
                c.estatus,
                c.fecha_conciliacion,
                u.nombre AS usuario_concilia,
                c.observaciones
            FROM conciliaciones c
            JOIN cuentas_bancarias cb ON c.id_cuenta_bancaria = cb.id_cuenta_bancaria
            LEFT JOIN usuarios u ON c.id_usuario_concilia = u.id_usuario
            WHERE c.id_conciliacion = ?
        """, (id_conc,))
        row = cursor.fetchone()
        if not row:
            flash('Conciliación no encontrada.', 'error')
            return redirect(url_for('conciliaciones_listar'))
        
        conciliacion = {
            'id_conciliacion': row[0],
            'nombre_banco': row[1],
            'numero_cuenta': row[2],
            'fecha_inicio': row[3],
            'fecha_fin': row[4],
            'saldo_banco': row[5],
            'saldo_sistema': row[6],
            'diferencia': row[7],
            'estatus': row[8],
            'fecha_conciliacion': row[9],
            'usuario_concilia': row[10],
            'observaciones': row[11]
        }
        return render_template('conciliaciones/ver.html', conciliacion=conciliacion)
    finally:
        conn.close()      

from utils.pdf_conciliacion import generar_pdf_conciliacion

@app.route('/conciliaciones/<int:id_conc>/pdf')
def pdf_conciliacion(id_conc):
    if session.get('rol_id') not in [1, 2]:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                c.id_conciliacion,
                cb.nombre_banco,
                cb.numero_cuenta,
                c.fecha_inicio,
                c.fecha_fin,
                c.saldo_banco,
                c.saldo_sistema,
                c.diferencia,
                c.estatus,
                c.fecha_conciliacion,
                u.nombre AS usuario_concilia,
                c.observaciones
            FROM conciliaciones c
            JOIN cuentas_bancarias cb ON c.id_cuenta_bancaria = cb.id_cuenta_bancaria
            LEFT JOIN usuarios u ON c.id_usuario_concilia = u.id_usuario
            WHERE c.id_conciliacion = ?
        """, (id_conc,))
        row = cursor.fetchone()
        if not row:
            flash('Conciliación no encontrada.', 'error')
            return redirect(url_for('conciliaciones_listar'))
        
        conciliacion = {
            'id_conciliacion': row[0],
            'nombre_banco': row[1],
            'numero_cuenta': row[2],
            'fecha_inicio': row[3],
            'fecha_fin': row[4],
            'saldo_banco': row[5],
            'saldo_sistema': row[6],
            'diferencia': row[7],
            'estatus': row[8],
            'fecha_conciliacion': row[9],
            'usuario_concilia': row[10],
            'observaciones': row[11]
        }
        
        pdf_buffer = generar_pdf_conciliacion(conciliacion)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'conciliacion_{id_conc}.pdf'
        )
    finally:
        conn.close()
        
# ======================
# DASHBOARD - RUTAS MODIFICADAS
# ======================

@app.route('/dashboard')
def dashboard_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener datos del dashboard
        summary = dashboard.get_executive_summary(session['user_id'])
        saldos = dashboard.get_saldos_por_cuenta()
        facturas = dashboard.get_facturas_recientes()
        conciliaciones = dashboard.get_conciliaciones_pendientes()
        top_clientes = dashboard.get_top_clientes()
        movimientos = dashboard.get_movimientos_bancarios_recientes()
        alertas = dashboard.get_alertas_sistema()
        
        # Gráficos
        ventas_chart = dashboard.get_ventas_mensuales()
        saldos_chart = dashboard.get_saldos_por_tipo_cuenta()
        
        return render_template('dashboard.html',
                             nombre=session['nombre'],
                             rol_id=session['rol_id'],
                             summary=summary,
                             saldos=saldos,
                             facturas=facturas,
                             conciliaciones=conciliaciones,
                             top_clientes=top_clientes,
                             movimientos=movimientos,
                             alertas=alertas,
                             ventas_chart=ventas_chart,
                             saldos_chart=saldos_chart)
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
                             nombre=session['nombre'],
                             rol_id=session['rol_id'],
                             summary={},
                             saldos=[],
                             facturas=[],
                             conciliaciones=[],
                             top_clientes=[],
                             movimientos=[],
                             alertas=[],
                             ventas_chart=None,
                             saldos_chart=None)

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API para datos del dashboard (usada por AJAX)"""
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        summary = dashboard.get_executive_summary(session['user_id'])
        estado_resultados = dashboard.get_estado_resultados_mensual()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'estado_resultados': estado_resultados.to_dict('records') if not estado_resultados.empty else [],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/saldos', methods=['GET'])
def api_saldos():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    saldos = dashboard.get_saldos_por_cuenta()
    result = []
    for s in saldos:
        result.append({
            "codigo": s['codigo'],
            "nombre": s['nombre'],
            "tipo": s['tipo'],
            "debe": float(s['total_debe']),
            "haber": float(s['total_haber']),
            "saldo": float(s['saldo'])
        })
    return jsonify(result)

@app.route('/api/facturas', methods=['GET'])
def api_facturas():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
            
        facturas = dashboard.get_facturas_recientes()
        result = []
        for f in facturas:
            result.append({
                "id": f['id_factura'],
                "tipo": f['tipo'],
                "folio": f['folio'],
                "fecha": str(f['fecha']),
                "fecha_vencimiento": str(f['fecha_vencimiento']) if f['fecha_vencimiento'] else None,
                "total": float(f['total']),
                "nombre_cliente_proveedor": f['nombre_cliente_proveedor'],
                "estatus": f['estatus']
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Endpoint para verificar salud del sistema"""
    try:
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500



# ======================
# ADMINISTRACIÓN - TABLAS MAESTRAS
# ======================

from models.tablas_maestras import (
    get_clientes, get_cliente_por_id, crear_cliente, actualizar_cliente, eliminar_cliente,
    get_proveedores, get_proveedor_por_id, crear_proveedor, actualizar_proveedor, eliminar_proveedor,
    get_plan_cuentas, get_cuenta_por_id, crear_cuenta, actualizar_cuenta, eliminar_cuenta,
    get_cuentas_bancarias_full, get_cuenta_bancaria_por_id, crear_cuenta_bancaria, actualizar_cuenta_bancaria, eliminar_cuenta_bancaria,
    get_usuarios, get_usuario_por_id, crear_usuario, actualizar_usuario, eliminar_usuario,
    get_tasas_iva, get_tasa_iva_por_id, crear_tasa_iva, actualizar_tasa_iva, eliminar_tasa_iva
)

@app.route('/admin')
def admin_panel():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    return render_template('admin/index.html')


# --- CLIENTES ---
@app.route('/admin/clientes')
def admin_clientes():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    # Parámetros de paginación
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    
    # Filtro opcional
    filtro = request.args.get('filtro', '')
    
    # Obtener clientes con paginación
    resultado = get_clientes(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/clientes.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='clientes')

@app.route('/admin/clientes/nuevo', methods=['GET', 'POST'])
def admin_crear_cliente():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        crear_cliente(
            request.form['nombre'],
            request.form['email'],
            request.form['rfc'],
            request.form['telefono'],
            request.form['direccion']
        )
        flash('Cliente creado', 'success')
        return redirect(url_for('admin_clientes'))
    return render_template('admin/form_cliente.html', action='crear')

@app.route('/admin/clientes/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_cliente(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_cliente(
            id,
            request.form['nombre'],
            request.form['email'],
            request.form['rfc'],
            request.form['telefono'],
            request.form['direccion']
        )
        flash('Cliente actualizado', 'success')
        return redirect(url_for('admin_clientes'))
    cliente = get_cliente_por_id(id)
    return render_template('admin/form_cliente.html', action='editar', registro=cliente)

@app.route('/admin/clientes/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_cliente(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    eliminar_cliente(id)
    flash('Cliente eliminado', 'success')
    return redirect(url_for('admin_clientes'))


# --- PROVEEDORES (similar) ---
@app.route('/admin/proveedores')
def admin_proveedores():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    filtro = request.args.get('filtro', '')
    
    resultado = get_proveedores(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/proveedores.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='proveedores')


@app.route('/admin/proveedores/nuevo', methods=['GET', 'POST'])
def admin_crear_proveedor():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        crear_proveedor(
            request.form['nombre'],
            request.form['email'],
            request.form['cuit'],
            request.form['domicilio']
        )
        flash('Proveedor creado', 'success')
        return redirect(url_for('admin_proveedores'))
    return render_template('admin/form_proveedor.html', action='crear')

@app.route('/admin/proveedores/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_proveedor(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_proveedor(
            id,
            request.form['nombre'],
            request.form['email'],
            request.form['cuit'],
            request.form['domicilio']
        )
        flash('Proveedor actualizado', 'success')
        return redirect(url_for('admin_proveedores'))
    proveedor = get_proveedor_por_id(id)
    return render_template('admin/form_proveedor.html', action='editar', registro=proveedor)

@app.route('/admin/proveedores/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_proveedor(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    eliminar_proveedor(id)
    flash('Proveedor eliminado', 'success')
    return redirect(url_for('admin_proveedores'))

# --- PLAN DE CUENTAS ---
@app.route('/admin/plan_cuentas')
def admin_plan_cuentas():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    filtro = request.args.get('filtro', '')
    
    resultado = get_plan_cuentas(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/plan_cuentas.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='plan_cuentas')

@app.route('/admin/plan_cuentas/nuevo', methods=['GET', 'POST'])
def admin_crear_cuenta():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        crear_cuenta(
            request.form['codigo'],
            request.form['nombre'],
            request.form['tipo_cuenta']
        )
        flash('Cuenta creada', 'success')
        return redirect(url_for('admin_plan_cuentas'))
    return render_template('admin/form_plan_cuenta.html', action='crear')

@app.route('/admin/plan_cuentas/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_cuenta(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_cuenta(
            id,
            request.form['codigo'],
            request.form['nombre'],
            request.form['tipo_cuenta']
        )
        flash('Cuenta actualizada', 'success')
        return redirect(url_for('admin_plan_cuentas'))
    cuenta = get_cuenta_por_id(id)
    return render_template('admin/form_plan_cuenta.html', action='editar', registro=cuenta)

@app.route('/admin/plan_cuentas/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_cuenta(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    eliminar_cuenta(id)
    flash('Cuenta eliminada', 'success')
    return redirect(url_for('admin_plan_cuentas'))

# --- CUENTAS BANCARIAS ---
@app.route('/admin/cuentas_bancarias')
def admin_cuentas_bancarias():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    filtro = request.args.get('filtro', '')
    
    resultado = get_cuentas_bancarias_full(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/cuentas_bancarias.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='cuentas_bancarias')

@app.route('/admin/cuentas_bancarias/nuevo', methods=['GET', 'POST'])
def admin_crear_cuenta_bancaria():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        crear_cuenta_bancaria(
            request.form['nombre_banco'],
            request.form['numero_cuenta'],
            request.form['id_cuenta_contable'],
            request.form['moneda']
        )
        flash('Cuenta bancaria creada', 'success')
        return redirect(url_for('admin_cuentas_bancarias'))
    return render_template('admin/form_cuenta_bancaria.html', action='crear')

@app.route('/admin/cuentas_bancarias/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_cuenta_bancaria(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_cuenta_bancaria(
            id,
            request.form['nombre_banco'],
            request.form['numero_cuenta'],
            request.form['id_cuenta_contable'],
            request.form['moneda']
        )
        flash('Cuenta bancaria actualizada', 'success')
        return redirect(url_for('admin_cuentas_bancarias'))
    cuenta = get_cuenta_bancaria_por_id(id)
    return render_template('admin/form_cuenta_bancaria.html', action='editar', registro=cuenta)

@app.route('/admin/cuentas_bancarias/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_cuenta_bancaria(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    eliminar_cuenta_bancaria(id)
    flash('Cuenta bancaria eliminada', 'success')
    return redirect(url_for('admin_cuentas_bancarias'))

# --- USUARIOS ---
@app.route('/admin/usuarios')
def admin_usuarios():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    filtro = request.args.get('filtro', '')
    
    resultado = get_usuarios(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/usuarios.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='usuarios')
    

@app.route('/admin/Usuarios/nuevo', methods=['GET', 'POST'])
def admin_crear_usuario():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        # NOTA: Aquí deberías hashear la contraseña
        crear_usuario(
            request.form['nombre'],
            request.form['email'],
            request.form['password'],  # ¡NO seguro!
            request.form['id_rol']
        )
        flash('Usuario creado', 'success')
        return redirect(url_for('admin_usuarios'))
    return render_template('admin/form_usuario.html', action='crear')

@app.route('/admin/Usuarios/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_usuario(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_usuario(
            id,
            request.form['nombre'],
            request.form['email'],
            request.form['id_rol']
        )
        flash('Usuario actualizado', 'success')
        return redirect(url_for('admin_usuarios'))
    usuario = get_usuario_por_id(id)
    return render_template('admin/form_usuario.html', action='editar', registro=usuario)

@app.route('/admin/Usuarios/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_usuario(id):
    if session.get('rol_id') != 1:
        flash('Acceso denerol_idgado', 'error')
        return redirect(url_for('menu'))
    eliminar_usuario(id)
    flash('Usuario eliminado', 'success')
    return redirect(url_for('admin_usuarios'))

# --- TASA IVA ---
@app.route('/admin/tasas_iva')
def admin_tasas_iva():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 20
    offset = (pagina - 1) * registros_por_pagina
    filtro = request.args.get('filtro', '')
    
    resultado = get_tasas_iva(
        limit=registros_por_pagina,
        offset=offset,
        filtro=filtro if filtro else None
    )
    
    return render_template('admin/Tasa_iva.html', 
                         registros=resultado['registros'],
                         paginacion=resultado,
                         filtro_actual=filtro,
                         tabla='tasas_iva')

@app.route('/admin/Tasa_iva/nuevo', methods=['GET', 'POST'])
def admin_crear_tasa_iva():
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        crear_tasa_iva(
            request.form['nombre'],
            float(request.form['porcentaje'])
        )
        flash('Tasa de IVA creada', 'success')
        return redirect(url_for('admin_tasas_iva'))
    return render_template('admin/form_tasa_iva.html', action='crear')

@app.route('/admin/Tasa_iva/<int:id>/editar', methods=['GET', 'POST'])
def admin_editar_tasa_iva(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    if request.method == 'POST':
        actualizar_tasa_iva(
            id,
            request.form['nombre'],
            float(request.form['porcentaje'])
        )
        flash('Tasa de IVA actualizada', 'success')
        return redirect(url_for('admin_tasas_iva'))
    tasa = get_tasa_iva_por_id(id)
    return render_template('admin/form_tasa_iva.html', action='editar', registro=tasa)

@app.route('/admin/Tasa_iva/<int:id>/eliminar', methods=['POST'])
def admin_eliminar_tasa_iva(id):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    eliminar_tasa_iva(id)
    flash('Tasa de IVA eliminada', 'success')
    return redirect(url_for('admin_tasas_iva'))

# ======================
# EXPORTACIONES (GENÉRICAS)
# ======================

from utils.export_maestras import exportar_a_excel, exportar_a_pdf

@app.route('/admin/<tabla>/exportar/<formato>')
def admin_exportar(tabla, formato):
    if session.get('rol_id') != 1:
        flash('Acceso denegado', 'error')
        return redirect(url_for('menu'))
    
    # Mapeo de tablas a funciones
    funciones = {
        'clientes': get_clientes,
        'proveedores': get_proveedores,
        'plan_cuentas': get_plan_cuentas,
        'cuentas_bancarias': get_cuentas_bancarias_full,
        'Usuarios': get_usuarios,
        'Tasa_iva': get_tasas_iva
    }

    if tabla not in funciones:
        flash('Tabla no válida', 'error')
        return redirect(url_for('admin_panel'))
    
    datos = funciones[tabla]()
    
    if formato == 'excel':
        output = exportar_a_excel(datos, tabla)
        return send_file(
            io.BytesIO(output.getvalue()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{tabla}.xlsx'
        )
    elif formato == 'pdf':
        output = exportar_a_pdf(datos, tabla)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{tabla}.pdf'
        )
    else:
        flash('Formato no soportado', 'error')
        return redirect(url_for(f'admin_{tabla}'))




from routes.informes import informes_bp

app.register_blueprint(informes_bp)        



#Importar Blueprints
from models.comprobantes import comprobantes_bp
from models.cuentas_contables_saldos import cuentas_bp

#Registrar Blueprints
app.register_blueprint(comprobantes_bp)
app.register_blueprint(cuentas_bp)


#   REVISAR


"""
#Importar modelos después de inicializar db
from models import Comprobante, AsientoContable, CuentaContable, SaldoCuenta

#Importar Blueprints
from comprobantes import comprobantes_bp
from cuentas_contables_saldos import cuentas_bp

#Registrar Blueprints
app.register_blueprint(comprobantes_bp)
app.register_blueprint(cuentas_bp)



# Context processor para variables globales
@app.context_processor
def inject_global_vars():
    return {
        'current_year': datetime.now().year,
        'app_name': 'Sistema Contable',
        'current_period': datetime.now().year
    }

"""

# ======================
# INICIO DE LA APP
# ======================

if __name__ == "__main__":
    import threading
    import webbrowser

    def open_browser():
        webbrowser.open("http://localhost:5050")

    threading.Timer(1.5, open_browser).start()
    app.run(port=5050)
    