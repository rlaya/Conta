# models/factura.py
from config.db import get_connection
from decimal import Decimal

# ========================
# FUNCIONES DE CONSULTA
# ========================

def listar_facturas(fecha_inicio=None, fecha_fin=None, tipo=None):
    query = """
        SELECT 
            f.id_factura, f.tipo, f.folio, f.fecha, f.fecha_vencimiento, f.total,
            ISNULL(c.nombre, p.nombre) AS nombre_tercero,
            f.estatus, f.id_asiento
        FROM facturas f
        LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
        LEFT JOIN proveedores p ON f.id_proveedor = p.id_proveedor
        WHERE 1=1
    """
    params = []

    if fecha_inicio:
        query += " AND f.fecha >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND f.fecha <= ?"
        params.append(fecha_fin)
    if tipo:
        query += " AND f.tipo = ?"
        params.append(tipo)

    query += " ORDER BY f.fecha DESC, f.id_factura DESC"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        facturas = cursor.fetchall()
        return facturas
    finally:
        conn.close()

def obtener_factura_por_id(id_factura):
    """
    Obtiene los datos de una factura por ID, incluyendo el nombre del tercero
    (cliente o proveedor) y el ID del asiento asociado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                f.id_factura, 
                f.tipo, 
                f.folio, 
                CONVERT(VARCHAR, f.fecha, 23) AS fecha_str, -- Formato YYYY-MM-DD
                CONVERT(VARCHAR, f.fecha_vencimiento, 23) AS fecha_vencimiento_str, -- Formato YYYY-MM-DD
                f.total, 
                f.id_cliente, 
                f.id_proveedor, 
                f.estatus,
                f.id_asiento, -- Agregado: ID del asiento
                ISNULL(c.nombre, p.nombre) AS nombre_tercero -- Agregado: Nombre del tercero
            FROM facturas f
            LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
            LEFT JOIN proveedores p ON f.id_proveedor = p.id_proveedor
            WHERE f.id_factura = ?
        """
        cursor.execute(query, (id_factura,))
        
        # Obtenemos la fila de resultado
        row = cursor.fetchone()
        
        if row:
            # Mapeamos los resultados a un diccionario para que sea fácil acceder 
            # desde la capa de la aplicación (app.py)
            factura = {
                'id_factura': row[0],
                'tipo': row[1],
                'folio': row[2],
                'fecha': row[3],
                'fecha_vencimiento': row[4],
                'total': row[5],
                'id_cliente': row[6],
                'id_proveedor': row[7],
                'estatus': row[8],
                'id_asiento': row[9],
                'tercero_nombre': row[10]
            }
            return factura
        return None # Devuelve None si no se encuentra la factura

    finally:
        conn.close()



def get_terceros():
    """Obtiene una lista combinada de clientes y proveedores para formularios."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id_cliente AS id, nombre, 'cliente' AS tipo FROM clientes
            UNION ALL
            SELECT id_proveedor AS id, nombre, 'proveedor' AS tipo FROM proveedores
            ORDER BY nombre
        """)
        rows = cursor.fetchall()
        return [{'id': r[0], 'nombre': r[1], 'tipo': r[2]} for r in rows]
    finally:
        conn.close()


# ========================
# FUNCIONES DE ESCRITURA (CRUD)
# ========================

def crear_factura_db(tipo, folio, fecha, fecha_vencimiento, total, id_cliente=None, id_proveedor=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if id_cliente and id_proveedor:
            raise ValueError("Una factura no puede tener cliente y proveedor al mismo tiempo.")
        if not id_cliente and not id_proveedor:
            raise ValueError("Debe especificar un cliente o un proveedor.")

        cursor.execute("""
            INSERT INTO facturas (tipo, folio, fecha, fecha_vencimiento, total, id_cliente, id_proveedor, estatus)
            OUTPUT INSERTED.id_factura
            VALUES (?, ?, ?, ?, ?, ?, ?, 'activa')
        """, (tipo, folio, fecha, fecha_vencimiento, total, id_cliente, id_proveedor))
        id_factura = cursor.fetchone()[0]
        conn.commit()
        return id_factura
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def actualizar_factura_db(id_factura, tipo, folio, fecha, fecha_vencimiento, total, estatus):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE facturas
            SET tipo = ?, folio = ?, fecha = ?, fecha_vencimiento = ?, total = ?, estatus = ?
            WHERE id_factura = ?
        """, (tipo, folio, fecha, fecha_vencimiento, total, estatus, id_factura))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def eliminar_factura_db(id_factura):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM facturas WHERE id_factura = ?", (id_factura,))
        if cursor.rowcount == 0:
            raise ValueError("Factura no encontrada.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ========================
# FUNCIONES DE ANULACIÓN
# ========================

def obtener_datos_factura_para_anulacion(id_factura):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                f.tipo, f.id_asiento, f.id_cliente, f.id_proveedor,
                p.id_cuenta, p.debe, p.haber, p.id_cliente AS partida_cliente, p.id_proveedor AS partida_proveedor
            FROM facturas f
            JOIN partidas p ON f.id_asiento = p.id_asiento
            WHERE f.id_factura = ?
        """, (id_factura,))
        return cursor.fetchall()
    finally:
        conn.close()


def cancelar_factura_con_anulacion(id_factura, id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        from utils.email import enviar_correo
        from config.email_config import DEFAULT_RECEIVER   

        cursor.execute("SELECT estatus, id_asiento FROM facturas WHERE id_factura = ?", (id_factura,))
        row = cursor.fetchone()
        if not row or row[0] == 'cancelada':
            raise ValueError("Factura ya cancelada o inexistente.")
        id_asiento_original = row[1]

        if not id_asiento_original:
            raise ValueError("La factura no tiene asiento asociado.")

        partidas_orig = obtener_datos_factura_para_anulacion(id_factura)
        if not partidas_orig:
            raise ValueError("No se encontraron partidas para anular.")

        cursor.execute("""
            SELECT fecha, concepto, id_diario 
            FROM asientos 
            WHERE id_asiento = ?
        """, (id_asiento_original,))
        asiento_orig = cursor.fetchone()
        if not asiento_orig:
            raise ValueError("Asiento original no encontrado.")

        fecha_anul = asiento_orig[0]
        concepto_anul = f"ANULACIÓN FACTURA {id_factura} - {asiento_orig[1]}"
        id_diario = asiento_orig[2]

        cursor.execute("""
            INSERT INTO asientos (id_diario, fecha, concepto, id_usuario_creador)
            OUTPUT INSERTED.id_asiento
            VALUES (?, ?, ?, ?)
        """, (id_diario, fecha_anul, concepto_anul, id_usuario))
        id_asiento_anul = cursor.fetchone()[0]

        for p in partidas_orig:
            debe_inv = p[6]  # lo que era haber
            haber_inv = p[5]  # lo que era debe

            cursor.execute("""
                INSERT INTO partidas (id_asiento, id_cuenta, id_cliente, id_proveedor, debe, haber, concepto_detallado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                id_asiento_anul,
                p[4],  # id_cuenta
                p[7],  # id_cliente de la partida
                p[8],  # id_proveedor de la partida
                debe_inv,
                haber_inv,
                f"Anulación de partida original"
            ))

        cursor.execute("UPDATE facturas SET estatus = 'cancelada' WHERE id_factura = ?", (id_factura,))
        cursor.execute("""
            INSERT INTO bitacora_actividad (id_usuario, accion, tabla_afectada, id_registro_afectado, ip)
            VALUES (?, 'canceló factura con asiento de anulación', 'facturas', ?, ?)
        """, (id_usuario, id_factura, '127.0.0.1'))

        conn.commit()

        enviar_correo(
            asunto=f"Factura {id_factura} cancelada",
            cuerpo=f"""
            <h3>Cancelación de factura</h3>
            <p>La factura <strong>{id_factura}</strong> ha sido cancelada.</p>
            <p>Asiento de anulación: {id_asiento_anul}</p>
            <p>Usuario: {id_usuario}</p>
            """,
            destinatario=DEFAULT_RECEIVER
        )
        return id_asiento_anul

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# Alias para compatibilidad
def cancelar_factura(id_factura, id_usuario):
    return cancelar_factura_con_anulacion(id_factura, id_usuario)