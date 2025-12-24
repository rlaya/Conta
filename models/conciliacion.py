# models/conciliacion.py
from config.db import get_connection
from datetime import datetime

def get_cuentas_bancarias():
    """Obtiene lista de cuentas bancarias para formularios."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id_cuenta_bancaria, nombre_banco, numero_cuenta
            FROM cuentas_bancarias
            ORDER BY nombre_banco
        """)
        return cursor.fetchall()
    finally:
        conn.close()

def crear_conciliacion(id_cuenta, fecha_inicio, fecha_fin, saldo_banco):
    """Crea una nueva conciliación bancaria (estatus = 'pendiente')."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        saldo_sistema = 0.0
        diferencia = saldo_banco - saldo_sistema

        cursor.execute("""
            INSERT INTO conciliaciones (
                id_cuenta_bancaria, fecha_inicio, fecha_fin,
                saldo_banco, saldo_sistema, diferencia, estatus
            ) OUTPUT INSERTED.id_conciliacion
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
        """, (id_cuenta, fecha_inicio, fecha_fin, saldo_banco, saldo_sistema, diferencia))
        
        id_conc = cursor.fetchone()[0]
        conn.commit()
        return id_conc
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def conciliar_conciliacion(id_conciliacion, id_usuario, saldo_sistema, observaciones=None):
    """
    Marca una conciliación como 'conciliada' y actualiza sus datos finales.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verificar que exista y esté pendiente
        cursor.execute("""
            SELECT estatus FROM conciliaciones WHERE id_conciliacion = ?
        """, (id_conciliacion,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Conciliación no encontrada.")
        if row[0] != 'pendiente':
            raise ValueError("La conciliación ya fue procesada.")

        # Calcular nueva diferencia
        cursor.execute("""
            SELECT saldo_banco FROM conciliaciones WHERE id_conciliacion = ?
        """, (id_conciliacion,))
        saldo_banco = cursor.fetchone()[0]
        diferencia = saldo_banco - saldo_sistema

        # Actualizar
        cursor.execute("""
            UPDATE conciliaciones
            SET 
                saldo_sistema = ?,
                diferencia = ?,
                estatus = 'conciliada',
                fecha_conciliacion = ?,
                id_usuario_concilia = ?,
                observaciones = ?
            WHERE id_conciliacion = ?
        """, (saldo_sistema, diferencia, datetime.now(), id_usuario, observaciones, id_conciliacion))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def listar_conciliaciones():
    """Lista todas las conciliaciones, ordenadas por fecha_fin (desc)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                c.id_conciliacion,
                cb.nombre_banco,
                c.fecha_inicio,
                c.fecha_fin,
                c.saldo_banco,
                c.saldo_sistema,
                c.diferencia,
                c.estatus
            FROM conciliaciones c
            INNER JOIN cuentas_bancarias cb ON c.id_cuenta_bancaria = cb.id_cuenta_bancaria
            ORDER BY c.fecha_fin DESC, c.id_conciliacion DESC
        """)
        return cursor.fetchall()
    finally:
        conn.close()