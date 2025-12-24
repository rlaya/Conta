# =======================
# models/tablas_maestra.py
# =======================

from config.db import get_connection

# =======================
# CLIENTES
# =======================

def get_clientes(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de clientes con paginación y filtros opcionales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(nombre LIKE ? OR email LIKE ? OR rfc LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT id_cliente, nombre, email, rfc, telefono, direccion 
        FROM clientes 
        {where_clause}
        ORDER BY nombre
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"SELECT COUNT(*) FROM clientes {where_clause}"
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_cliente_por_id(id_cliente):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_cliente, nombre, email, rfc, telefono, direccion FROM clientes WHERE id_cliente = ?", (id_cliente,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_cliente(nombre, email, rfc, telefono, direccion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clientes (nombre, email, rfc, telefono, direccion)
        OUTPUT INSERTED.id_cliente
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, email, rfc, telefono, direccion))
    id_cliente = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_cliente

def actualizar_cliente(id_cliente, nombre, email, rfc, telefono, direccion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clientes
        SET nombre = ?, email = ?, rfc = ?, telefono = ?, direccion = ?
        WHERE id_cliente = ?
    """, (nombre, email, rfc, telefono, direccion, id_cliente))
    conn.commit()
    conn.close()

def eliminar_cliente(id_cliente):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_cliente,))
    conn.commit()
    conn.close()

# =======================
# PROVEEDORES
# =======================

def get_proveedores(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de proveedores con paginación y filtros opcionales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(nombre LIKE ? OR email LIKE ? OR rfc LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT id_proveedor, nombre, email, rfc, telefono, direccion 
        FROM proveedores 
        {where_clause}
        ORDER BY nombre
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"SELECT COUNT(*) FROM proveedores {where_clause}"
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_proveedor_por_id(id_proveedor):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_proveedor, nombre, email, rfc, telefono, direccion FROM proveedores WHERE id_proveedor = ?", (id_proveedor,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_proveedor(nombre, email, rfc, telefono, direccion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO proveedores (nombre, email, rfc, telefono, direccion)
        OUTPUT INSERTED.id_proveedor
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, email, rfc, telefono, direccion))
    id_proveedor = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_proveedor

def actualizar_proveedor(id_proveedor, nombre, email, rfc, telefono, direccion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE proveedores
        SET nombre = ?, email = ?, rfc = ?, telefono = ?, direccion = ?
        WHERE id_proveedor = ?
    """, (nombre, email, rfc, telefono, direccion, id_proveedor))
    conn.commit()
    conn.close()

def eliminar_proveedor(id_proveedor):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proveedores WHERE id_proveedor = ?", (id_proveedor,))
    conn.commit()
    conn.close()

# =======================
# PLAN DE CUENTAS
# =======================

def get_plan_cuentas(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de cuentas contables con paginación y filtros opcionales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(codigo LIKE ? OR nombre LIKE ? OR tipo_cuenta LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT id_cuenta, codigo, nombre, tipo_cuenta, padre_id, es_detalle 
        FROM plan_cuentas 
        {where_clause}
        ORDER BY codigo
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"SELECT COUNT(*) FROM plan_cuentas {where_clause}"
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_cuenta_por_id(id_cuenta):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_cuenta, codigo, nombre, tipo_cuenta FROM plan_cuentas WHERE id_cuenta = ?", (id_cuenta,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_cuenta(codigo, nombre, tipo_cuenta):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO plan_cuentas (codigo, nombre, tipo_cuenta)
        OUTPUT INSERTED.id_cuenta
        VALUES (?, ?, ?, ?, ?)
    """, (codigo, nombre, tipo_cuenta))
    id_cuenta = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_cuenta

def actualizar_cuenta(id_cuenta, codigo, nombre, tipo_cuenta):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE plan_cuentas
        SET codigo = ?, nombre = ?, tipo_cuenta = ?
        WHERE id_cuenta = ?
    """, (codigo, nombre, tipo_cuenta, id_cuenta))
    conn.commit()
    conn.close()

def eliminar_cuenta(id_cuenta):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plan_cuentas WHERE id_cuenta = ?", (id_cuenta,))
    conn.commit()
    conn.close()

# =======================
# CUENTAS BANCARIAS
# =======================

def get_cuentas_bancarias_full(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de cuentas bancarias con información completa y paginación
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(numero_cuenta LIKE ? OR nombre_banco LIKE ? OR id_cuenta_contable LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT 
            id_cuenta_bancaria,
            numero_cuenta,
            nombre_banco,
            id_cuenta_contable,
            moneda
        FROM cuentas_bancarias 
        {where_clause}
        ORDER BY numero_cuenta
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()


    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"SELECT COUNT(*) FROM cuentas_bancarias {where_clause}"
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_cuenta_bancaria_por_id(id_cuenta_bancaria):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_cuenta_bancaria, numero_cuenta, nombre_banco, id_cuenta_contable, moneda
        FROM cuentas_bancarias 
        WHERE id_cuenta_bancaria = ?
    """, (id_cuenta_bancaria,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_cuenta_bancaria(numero_cuenta, nombre_banco, id_cuenta_contable, moneda):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cuentas_bancarias (numero_cuenta, nombre_banco, id_cuenta_contable, moneda)
        OUTPUT INSERTED.id_cuenta_bancaria
        VALUES (?, ?, ?, ?)
    """, (numero_cuenta, nombre_banco, id_cuenta_contable, moneda))
    id_cuenta_bancaria = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_cuenta_bancaria

def actualizar_cuenta_bancaria(id_cuenta_bancaria, numero_cuenta, nombre_banco, id_cuenta_contable, moneda):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cuentas_bancarias
        SET numero_cuenta = ?, nombre_banco = ?, id_cuenta_contable = ?, moneda = ?
        WHERE id_cuenta_bancaria = ?
    """, numero_cuenta, nombre_banco, id_cuenta_contable, moneda, id_cuenta_bancaria)
    conn.commit()
    conn.close()

def eliminar_cuenta_bancaria(id_cuenta_bancaria):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cuentas_bancarias WHERE id_cuenta_bancaria = ?", (id_cuenta_bancaria,))
    conn.commit()
    conn.close()

# =======================
# USUARIOS
# =======================

def get_usuarios(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de usuarios con paginación y filtros opcionales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(u.username LIKE ? OR u.email LIKE ? OR r.nombre_rol LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT 
            u.id_usuario,
            u.email,
            u.nombre,
            r.nombre,
            u.activo,
            u.creado_en
        FROM usuarios u
        LEFT JOIN roles r ON u.id_rol = r.id_rol
        {where_clause}
        ORDER BY u.nombre
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"""
        SELECT COUNT(*) 
        FROM usuarios u
        LEFT JOIN roles r ON u.id_rol = r.id_rol
        {where_clause}
    """
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_usuario_por_id(id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_usuario, email, nombre, id_rol, activo, creado_en
        FROM usuarios 
        WHERE id_usuario = ?
    """, (id_usuario,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_usuario(email, nombre, id_rol, activo, creado_en):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usuarios (email, nombre, id_rol, activo, creado_en, password)
        OUTPUT INSERTED.id_usuario
        VALUES (?, ?, ?, ?, ?)
    """, (email, nombre, id_rol, activo, creado_en, password))
    id_usuario = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_usuario

def actualizar_usuario(id_usuario, email, nombre, id_rol, activo, creado_en):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET email = ?, nombre = ?, id_rol = ?, activo = ?, creado_en = ?
        WHERE id_usuario = ?
    """, (email, nombre, id_rol, activo, id_usuario))
    conn.commit()
    conn.close()

def eliminar_usuario(id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id_usuario = ?", (id_usuario,))
    conn.commit()
    conn.close()

# =======================
# TASAS DE IVA
# =======================

def get_tasas_iva(limit=None, offset=0, filtro=None):
    """
    Obtiene lista de tasas de IVA con paginación y filtros opcionales
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_conditions = []
    params = []
    
    if filtro:
        where_conditions.append("(nombre LIKE ? OR CAST(porcentaje AS VARCHAR) LIKE ?)")
        params.extend([f'%{filtro}%', f'%{filtro}%'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT id_tasa, porcentaje, nombre, activa 
        FROM tasas_iva 
        {where_clause}
        ORDER BY porcentaje
    """
    
    if limit is not None:
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    count_query = f"SELECT COUNT(*) FROM tasas_iva {where_clause}"
    cursor.execute(count_query, params[:len(params) - (2 if limit is not None else 0)])
    total_registros = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'registros': rows,
        'total': total_registros,
        'pagina_actual': offset // limit + 1 if limit and limit > 0 else 1,
        'total_paginas': (total_registros + limit - 1) // limit if limit and limit > 0 else 1
    }

def get_tasa_iva_por_id(id_tasa):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_tasa, porcentaje, nombre, activa FROM tasas_iva WHERE id_tasa = ?", (id_tasa,))
    row = cursor.fetchone()
    conn.close()
    return row

def crear_tasa_iva(nombre, porcentaje, descripcion, estado):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasas_iva (porcentaje, nombre, activa)
        OUTPUT INSERTED.id_tasa
        VALUES (?, ?, ?)
    """, (porcentaje, nombre, activa))
    id_tasa = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id_tasa

def actualizar_tasa_iva(id_tasa, porcentaje, nombre, activa):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasas_iva
        SET porcentaje = ?, nombre = ?, activa = ?
        WHERE id_tasa = ?
    """, (porcentaje, nombre, activa, id_tasa))
    conn.commit()
    conn.close()

def eliminar_tasa_iva(id_tasa):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasas_iva WHERE id_tasa = ?", (id_tasa,))
    conn.commit()
    conn.close