# utils/validaciones_contables.py
from config.db import get_connection

def validar_comprobante_contable(tipo, folio):
    """
    Valida que un comprobante cumpla con todas las reglas contables
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Obtener comprobante
        cursor.execute("""
            SELECT total FROM comprobantes 
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        comprobante = cursor.fetchone()
        
        if not comprobante:
            return False, "Comprobante no encontrado"
        
        total_comprobante = float(comprobante.total) if comprobante.total else 0
        
        # 2. Obtener asientos del comprobante
        cursor.execute("""
            SELECT debe, haber FROM asientos_contables 
            WHERE id_comprobante_tipo = ? AND id_comprobante_folio = ?
        """, (tipo, folio))
        
        asientos = cursor.fetchall()
        
        # 3. Validar cantidad de asientos
        if len(asientos) < 2:
            return False, "El comprobante debe tener al menos 2 asientos"
        
        # 4. Calcular sumatorias
        total_debe = sum(float(a.debe) if a.debe else 0 for a in asientos)
        total_haber = sum(float(a.haber) if a.haber else 0 for a in asientos)
        
        # 5. Validar cuadratura
        if abs(total_debe - total_haber) > 0.01:
            return False, f"La suma de debe (${total_debe:,.2f}) no es igual a la suma de haber (${total_haber:,.2f})"
        
        # 6. Validar que total coincide
        if abs(total_debe - total_comprobante) > 0.01:
            return False, f"El total del comprobante (${total_comprobante:,.2f}) no coincide con la suma de asientos (${total_debe:,.2f})"
        
        # 7. Validar que cada asiento tenga solo debe O haber
        for i, asiento in enumerate(asientos):
            debe_val = float(asiento.debe) if asiento.debe else 0
            haber_val = float(asiento.haber) if asiento.haber else 0
            
            if debe_val > 0 and haber_val > 0:
                return False, f"Asiento #{i+1}: No puede tener valores en debe y haber simultáneamente"
            
            if debe_val == 0 and haber_val == 0:
                return False, f"Asiento #{i+1}: Debe tener un valor en debe O haber"
        
        return True, "Comprobante válido"
        
    except Exception as e:
        return False, f"Error en validación: {str(e)}"
    finally:
        conn.close()

def registrar_comprobante(tipo, folio):
    """
    Registra un comprobante y actualiza los saldos de las cuentas
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Validar antes de registrar
        valido, mensaje = validar_comprobante_contable(tipo, folio)
        if not valido:
            return False, mensaje
        
        # 2. Obtener asientos
        cursor.execute("""
            SELECT id_cuenta, debe, haber FROM asientos_contables 
            WHERE id_comprobante_tipo = ? AND id_comprobante_folio = ?
        """, (tipo, folio))
        
        asientos = cursor.fetchall()
        
        # 3. Obtener período (año-mes actual)
        from datetime import datetime
        periodo_actual = datetime.now().year * 100 + datetime.now().month
        
        # 4. Actualizar saldos por cada asiento
        for asiento in asientos:
            id_cuenta = asiento.id_cuenta
            debe_val = float(asiento.debe) if asiento.debe else 0
            haber_val = float(asiento.haber) if asiento.haber else 0
            monto = debe_val - haber_val
            
            # Verificar si existe saldo para este período
            cursor.execute("""
                SELECT saldo_final FROM saldos_cuentas 
                WHERE id_cuenta = ? AND periodo = ?
            """, (id_cuenta, periodo_actual))
            
            saldo_existente = cursor.fetchone()
            
            if saldo_existente:
                # Actualizar saldo existente
                nuevo_saldo = float(saldo_existente.saldo_final) + monto
                cursor.execute("""
                    UPDATE saldos_cuentas 
                    SET saldo_final = ? 
                    WHERE id_cuenta = ? AND periodo = ?
                """, (nuevo_saldo, id_cuenta, periodo_actual))
            else:
                # Obtener último saldo anterior
                cursor.execute("""
                    SELECT saldo_final FROM saldos_cuentas 
                    WHERE id_cuenta = ? AND periodo < ?
                    ORDER BY periodo DESC
                """, (id_cuenta, periodo_actual))
                
                saldo_anterior = cursor.fetchone()
                saldo_inicial = float(saldo_anterior.saldo_final) if saldo_anterior else 0
                saldo_final = saldo_inicial + monto
                
                # Insertar nuevo registro de saldo
                cursor.execute("""
                    INSERT INTO saldos_cuentas 
                    (id_cuenta, periodo, saldo_inicial, saldo_final, creado_en)
                    VALUES (?, ?, ?, ?, GETDATE())
                """, (id_cuenta, periodo_actual, saldo_inicial, saldo_final))
        
        # 5. Actualizar estado del comprobante
        cursor.execute("""
            UPDATE comprobantes 
            SET estado = 'Registrado' 
            WHERE tipo = ? AND folio = ?
        """, (tipo, folio))
        
        conn.commit()
        return True, "Comprobante registrado exitosamente"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error al registrar comprobante: {str(e)}"
    finally:
        conn.close()

def crear_comprobante_reverso(tipo_original, folio_original, nuevo_tipo, nuevo_folio):
    """
    Crea un comprobante de reversión intercambiando debe/haber
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Obtener comprobante original
        cursor.execute("""
            SELECT fecha, concepto, total, id_cliente, id_proveedor 
            FROM comprobantes 
            WHERE tipo = ? AND folio = ? AND estado = 'Registrado'
        """, (tipo_original, folio_original))
        
        comprobante_original = cursor.fetchone()
        if not comprobante_original:
            return False, "Comprobante original no encontrado o no está registrado"
        
        # 2. Verificar que no exista ya el nuevo comprobante
        cursor.execute("""
            SELECT COUNT(*) FROM comprobantes 
            WHERE tipo = ? AND folio = ?
        """, (nuevo_tipo, nuevo_folio))
        
        if cursor.fetchone()[0] > 0:
            return False, "Ya existe un comprobante con ese tipo y folio"
        
        # 3. Crear nuevo comprobante (con mismo concepto pero indicando reversión)
        concepto_reverso = f"REVERSO DE {tipo_original}-{folio_original}: {comprobante_original.concepto}"
        
        cursor.execute("""
            INSERT INTO comprobantes 
            (tipo, folio, fecha, concepto, total, estado, 
             id_cliente, id_proveedor, creado_en)
            VALUES (?, ?, ?, ?, ?, 'Pendiente', ?, ?, GETDATE())
        """, (
            nuevo_tipo,
            nuevo_folio,
            comprobante_original.fecha,
            concepto_reverso,
            float(comprobante_original.total),
            comprobante_original.id_cliente,
            comprobante_original.id_proveedor
        ))
        
        # 4. Obtener asientos originales
        cursor.execute("""
            SELECT consecutivo, id_cuenta, fecha, concepto, 
                   debe, haber, referencia
            FROM asientos_contables 
            WHERE id_comprobante_tipo = ? AND id_comprobante_folio = ?
            ORDER BY consecutivo
        """, (tipo_original, folio_original))
        
        asientos_originales = cursor.fetchall()
        
        # 5. Insertar asientos reversados (intercambiar debe/haber)
        for asiento in asientos_originales:
            # Intercambiar debe y haber
            nuevo_debe = float(asiento.haber) if asiento.haber else 0
            nuevo_haber = float(asiento.debe) if asiento.debe else 0
            
            cursor.execute("""
                INSERT INTO asientos_contables 
                (id_comprobante_tipo, id_comprobante_folio, consecutivo, 
                 id_cuenta, fecha, concepto, debe, haber, referencia, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """, (
                nuevo_tipo,
                nuevo_folio,
                asiento.consecutivo,
                asiento.id_cuenta,
                asiento.fecha,
                f"REVERSO: {asiento.concepto}" if asiento.concepto else "Reverso",
                nuevo_debe,
                nuevo_haber,
                asiento.referencia
            ))
        
        conn.commit()
        return True, "Comprobante de reversión creado exitosamente"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error al crear comprobante de reversión: {str(e)}"
    finally:
        conn.close()