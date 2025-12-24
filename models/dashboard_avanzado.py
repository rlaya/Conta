# models/dashboard_avanzado.py

from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json

from config.db import get_connection


class DashboardAvanzado:
    def __init__(self):
        pass
    
    def execute_query(self, query, params=None):
        """Ejecutar consulta y devolver resultados como diccionarios"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                conn.commit()
                return cursor.rowcount
        finally:
            cursor.close()
            conn.close()
    
    def execute_query_df(self, query, params=None):
        """Ejecutar consulta y devolver resultados como DataFrame"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame.from_records(rows, columns=columns)
        finally:
            cursor.close()
            conn.close()
    
    def get_executive_summary(self, user_id=None):
        """Resumen ejecutivo del sistema"""
        summary = {
            'total_ventas': 0,
            'total_gastos': 0,
            'saldo_bancos': 0,
            'clientes_activos': 0,
            'facturas_pendientes': 0,
            'conciliaciones_pendientes': 0,
            'utilidad_neta': 0,
            'margen_utilidad': 0
        }
        
        try:
            # Total ventas del mes actual
            query = """
            SELECT ISNULL(SUM(total), 0) as total_ventas
            FROM facturas 
            WHERE tipo = 'ingreso' 
            AND estatus = 'activa'
            AND MONTH(fecha) = MONTH(GETDATE())
            AND YEAR(fecha) = YEAR(GETDATE())
            """
            result = self.execute_query(query)
            if result:
                summary['total_ventas'] = float(result[0]['total_ventas'])
            
            # Total gastos del mes
            query = """
            SELECT ISNULL(SUM(total), 0) as total_gastos
            FROM facturas 
            WHERE tipo = 'egreso' 
            AND estatus = 'activa'
            AND MONTH(fecha) = MONTH(GETDATE())
            AND YEAR(fecha) = YEAR(GETDATE())
            """
            result = self.execute_query(query)
            if result:
                summary['total_gastos'] = float(result[0]['total_gastos'])
            
            # Saldo total en bancos
            query = """
            SELECT 
                ISNULL(SUM(CASE 
                    WHEN mb.monto >= 0 THEN mb.monto 
                    ELSE 0 
                END), 0) as saldo_positivo,
                ISNULL(SUM(CASE 
                    WHEN mb.monto < 0 THEN ABS(mb.monto) 
                    ELSE 0 
                END), 0) as saldo_negativo
            FROM movimientos_bancarios mb
            INNER JOIN cuentas_bancarias cb ON mb.id_cuenta_bancaria = cb.id_cuenta_bancaria
            WHERE mb.conciliado = 1
            """
            result = self.execute_query(query)
            if result:
                saldo_positivo = float(result[0]['saldo_positivo'])
                saldo_negativo = float(result[0]['saldo_negativo'])
                summary['saldo_bancos'] = saldo_positivo - saldo_negativo
            
            # Clientes activos (con facturas en los últimos 90 días)
            query = """
            SELECT ISNULL(COUNT(DISTINCT id_cliente), 0) as clientes_activos
            FROM facturas 
            WHERE id_cliente IS NOT NULL 
            AND fecha >= DATEADD(day, -90, GETDATE())
            """
            result = self.execute_query(query)
            if result:
                summary['clientes_activos'] = int(result[0]['clientes_activos'])
            
            # Facturas pendientes de pago
            query = """
            SELECT ISNULL(COUNT(*), 0) as facturas_pendientes
            FROM facturas 
            WHERE estatus = 'activa' 
            AND fecha_vencimiento IS NOT NULL 
            AND fecha_vencimiento < GETDATE()
            """
            result = self.execute_query(query)
            if result:
                summary['facturas_pendientes'] = int(result[0]['facturas_pendientes'])
            
            # Conciliaciones pendientes
            query = """
            SELECT ISNULL(COUNT(*), 0) as conciliaciones_pendientes
            FROM conciliaciones 
            WHERE estatus = 'pendiente'
            """
            result = self.execute_query(query)
            if result:
                summary['conciliaciones_pendientes'] = int(result[0]['conciliaciones_pendientes'])
            
            # Cálculo de utilidad
            summary['utilidad_neta'] = summary['total_ventas'] - summary['total_gastos']
            if summary['total_ventas'] > 0:
                summary['margen_utilidad'] = (summary['utilidad_neta'] / summary['total_ventas']) * 100
                
        except Exception as e:
            print(f"Error en get_executive_summary: {str(e)}")
        
        return summary
    
    def get_saldos_por_cuenta(self, top_n=10):
        """Saldos por cuenta contable - Versión simplificada"""
        try:
            query = """
            SELECT 
                cc.codigo,
                cc.nombre,
                cc.tipo,
                ISNULL(SUM(ac.debe), 0) as total_debe,
                ISNULL(SUM(ac.haber), 0) as total_haber,
                CASE 
                    WHEN cc.tipo IN ('Activo', 'Gastos') THEN ISNULL(SUM(ac.debe - ac.haber), 0)
                    WHEN cc.tipo IN ('Pasivo', 'Capital', 'Ingresos') THEN ISNULL(SUM(ac.haber - ac.debe), 0)
                    ELSE 0 
                END as saldo
            FROM cuentas_contables cc
            LEFT JOIN asientos_contables ac ON cc.codigo = ac.id_cuenta
            WHERE cc.nivel = 3  -- Cuentas de detalle
            GROUP BY cc.codigo, cc.nombre, cc.tipo
            HAVING CASE 
                WHEN cc.tipo IN ('Activo', 'Gastos') THEN ABS(ISNULL(SUM(ac.debe - ac.haber), 0))
                WHEN cc.tipo IN ('Pasivo', 'Capital', 'Ingresos') THEN ABS(ISNULL(SUM(ac.haber - ac.debe), 0))
                ELSE 0 
            END > 0.01
            ORDER BY ABS(saldo) DESC
            """
            result = self.execute_query(query)
            return result[:top_n] if result else []
        except Exception as e:
            print(f"Error en get_saldos_por_cuenta: {str(e)}")
            return []
    
    def get_facturas_recientes(self, limit=10):
        """Facturas recientes"""
        try:
            query = """
            SELECT TOP(?) 
                f.id_factura,
                f.tipo,
                f.folio,
                f.fecha,
                COALESCE(c.nombre, p.nombre, 'Sin nombre') as nombre_cliente_proveedor,
                f.total,
                f.estatus,
                f.fecha_vencimiento
            FROM facturas f
            LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
            LEFT JOIN proveedores p ON f.id_proveedor = p.id_proveedor
            WHERE f.estatus = 'activa'
            ORDER BY f.fecha DESC
            """
            return self.execute_query(query, (limit,))
        except Exception as e:
            print(f"Error en get_facturas_recientes: {str(e)}")
            return []
    
    def get_conciliaciones_pendientes(self):
        """Conciliaciones bancarias pendientes"""
        try:
            query = """
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
            WHERE c.estatus = 'pendiente'
            ORDER BY c.fecha_inicio DESC
            """
            return self.execute_query(query)
        except Exception as e:
            print(f"Error en get_conciliaciones_pendientes: {str(e)}")
            return []
    
    def get_ventas_mensuales(self, meses=6):
        """Ventas mensuales para gráfico"""
        try:
            query = f"""
            SELECT 
                FORMAT(f.fecha, 'yyyy-MM') as mes,
                ISNULL(SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END), 0) as ventas,
                ISNULL(SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END), 0) as gastos
            FROM facturas f
            WHERE f.fecha >= DATEADD(month, -{meses}, GETDATE())
            AND f.estatus = 'activa'
            GROUP BY FORMAT(f.fecha, 'yyyy-MM')
            ORDER BY mes
            """
            df = self.execute_query_df(query)
            
            if not df.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['mes'],
                    y=df['ventas'],
                    name='Ventas',
                    marker_color='rgb(55, 83, 109)'
                ))
                fig.add_trace(go.Bar(
                    x=df['mes'],
                    y=df['gastos'],
                    name='Gastos',
                    marker_color='rgb(26, 118, 255)'
                ))
                
                fig.update_layout(
                    title='Ventas vs Gastos (Últimos meses)',
                    xaxis_tickfont_size=14,
                    yaxis=dict(
                        title='Monto ($)',
                        titlefont_size=16,
                        tickfont_size=14,
                    ),
                    legend=dict(
                        x=0,
                        y=1.0,
                        bgcolor='rgba(255, 255, 255, 0)',
                        bordercolor='rgba(255, 255, 255, 0)'
                    ),
                    barmode='group',
                    bargap=0.15,
                    bargroupgap=0.1,
                    height=400,
                    plot_bgcolor='white'
                )
                return fig.to_json()
        except Exception as e:
            print(f"Error en get_ventas_mensuales: {str(e)}")
        return None
    
    def get_saldos_por_tipo_cuenta(self):
        """Saldos por tipo de cuenta (Activo, Pasivo, Capital, etc.)"""
        try:
            query = """
            SELECT 
                cc.tipo,
                CASE 
                    WHEN cc.tipo IN ('Activo', 'Gastos') THEN ISNULL(SUM(ac.debe - ac.haber), 0)
                    WHEN cc.tipo IN ('Pasivo', 'Capital', 'Ingresos') THEN ISNULL(SUM(ac.haber - ac.debe), 0)
                    ELSE 0 
                END as saldo_total
            FROM cuentas_contables cc
            LEFT JOIN asientos_contables ac ON cc.codigo = ac.id_cuenta
            WHERE cc.nivel = 2  -- Cuentas de mayor
            GROUP BY cc.tipo
            HAVING ABS(CASE 
                WHEN cc.tipo IN ('Activo', 'Gastos') THEN ISNULL(SUM(ac.debe - ac.haber), 0)
                WHEN cc.tipo IN ('Pasivo', 'Capital', 'Ingresos') THEN ISNULL(SUM(ac.haber - ac.debe), 0)
                ELSE 0 
            END) > 0.01
            """
            df = self.execute_query_df(query)
            
            if not df.empty:
                fig = px.pie(df, values='saldo_total', names='tipo', 
                            title='Distribución por Tipo de Cuenta')
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=400, plot_bgcolor='white')
                return fig.to_json()
        except Exception as e:
            print(f"Error en get_saldos_por_tipo_cuenta: {str(e)}")
        return None
    
    def get_top_clientes(self, limit=5):
        """Top clientes por volumen de compras"""
        try:
            query = """
            SELECT TOP(?) 
                ISNULL(c.nombre, 'Cliente no especificado') as nombre,
                ISNULL(SUM(f.total), 0) as total_compras,
                ISNULL(COUNT(f.id_factura), 0) as cantidad_facturas
            FROM facturas f
            LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
            WHERE f.tipo = 'ingreso' 
            AND f.estatus = 'activa'
            AND f.fecha >= DATEADD(month, -12, GETDATE())
            GROUP BY c.nombre
            ORDER BY total_compras DESC
            """
            return self.execute_query(query, (limit,))
        except Exception as e:
            print(f"Error en get_top_clientes: {str(e)}")
            return []
    
    def get_movimientos_bancarios_recientes(self, limit=10):
        """Movimientos bancarios recientes"""
        try:
            query = """
            SELECT TOP(?) 
                mb.id_movimiento,
                cb.nombre_banco,
                mb.fecha,
                mb.concepto,
                mb.monto,
                mb.referencia,
                CASE WHEN mb.conciliado = 1 THEN 'Conciliado' ELSE 'Pendiente' END as estado
            FROM movimientos_bancarios mb
            INNER JOIN cuentas_bancarias cb ON mb.id_cuenta_bancaria = cb.id_cuenta_bancaria
            ORDER BY mb.fecha DESC, mb.id_movimiento DESC
            """
            return self.execute_query(query, (limit,))
        except Exception as e:
            print(f"Error en get_movimientos_bancarios_recientes: {str(e)}")
            return []
    
    def get_alertas_sistema(self):
        """Alertas del sistema"""
        alertas = []
        
        try:
            # Facturas vencidas
            query = """
            SELECT 'Factura Vencida' as tipo, 
                   'Factura ' + ISNULL(f.folio, 'Sin folio') + ' vencida' as descripcion,
                   'high' as prioridad
            FROM facturas f
            WHERE f.estatus = 'activa' 
            AND f.fecha_vencimiento IS NOT NULL
            AND f.fecha_vencimiento < GETDATE()
            """
            result = self.execute_query(query)
            if result:
                alertas.extend(result)
            
            # Asientos desbalanceados
            query = """
            SELECT 'Asiento Desbalanceado' as tipo,
                   'Comprobante ' + ISNULL(ac.id_comprobante_tipo, 'Sin tipo') + 
                   '-' + ISNULL(ac.id_comprobante_folio, 'Sin folio') as descripcion,
                   'medium' as prioridad
            FROM asientos_contables ac
            GROUP BY ac.id_comprobante_tipo, ac.id_comprobante_folio
            HAVING ABS(ISNULL(SUM(ac.debe), 0) - ISNULL(SUM(ac.haber), 0)) > 0.01
            """
            result = self.execute_query(query)
            if result:
                alertas.extend(result)
            
            # Cuentas sin movimiento en 30 días (solo si tienen registros antiguos)
            query = """
            SELECT 'Cuenta Inactiva' as tipo,
                   'Cuenta ' + cc.codigo + ' - ' + cc.nombre + ' sin movimiento reciente' as descripcion,
                   'low' as prioridad
            FROM cuentas_contables cc
            WHERE cc.nivel = 3  -- Solo cuentas de detalle
            AND cc.codigo IN (
                SELECT DISTINCT ac.id_cuenta 
                FROM asientos_contables ac 
                WHERE ac.fecha < DATEADD(day, -30, GETDATE())
            )
            AND cc.codigo NOT IN (
                SELECT DISTINCT ac.id_cuenta 
                FROM asientos_contables ac 
                WHERE ac.fecha >= DATEADD(day, -30, GETDATE())
            )
            """
            result = self.execute_query(query)
            if result:
                alertas.extend(result)
                
        except Exception as e:
            print(f"Error en get_alertas_sistema: {str(e)}")
        
        return alertas
    
    def get_estado_resultados_mensual(self):
        """Estado de resultados mensual"""
        try:
            query = """
            SELECT 
                FORMAT(f.fecha, 'yyyy-MM') as mes,
                ISNULL(SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END), 0) as ingresos,
                ISNULL(SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END), 0) as gastos,
                ISNULL(SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END), 0) - 
                ISNULL(SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END), 0) as utilidad
            FROM facturas f
            WHERE f.fecha >= DATEADD(month, -5, GETDATE())
            AND f.estatus = 'activa'
            GROUP BY FORMAT(f.fecha, 'yyyy-MM')
            ORDER BY mes
            """
            return self.execute_query_df(query)
        except Exception as e:
            print(f"Error en get_estado_resultados_mensual: {str(e)}")
            return pd.DataFrame()