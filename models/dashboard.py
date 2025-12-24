# models/dashboard.py
from .database import DatabaseConnection
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json

class DashboardData:
    def __init__(self, config):
        self.db = DatabaseConnection(config)
    
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
        
        # Total ventas del mes actual
        query = """
        SELECT SUM(total) as total_ventas
        FROM facturas 
        WHERE tipo = 'ingreso' 
        AND estatus = 'activa'
        AND MONTH(fecha) = MONTH(GETDATE())
        AND YEAR(fecha) = YEAR(GETDATE())
        """
        result = self.db.execute_query(query)
        summary['total_ventas'] = float(result[0]['total_ventas'] or 0)
        
        # Total gastos del mes
        query = """
        SELECT SUM(total) as total_gastos
        FROM facturas 
        WHERE tipo = 'egreso' 
        AND estatus = 'activa'
        AND MONTH(fecha) = MONTH(GETDATE())
        AND YEAR(fecha) = YEAR(GETDATE())
        """
        result = self.db.execute_query(query)
        summary['total_gastos'] = float(result[0]['total_gastos'] or 0)
        
        # Saldo total en bancos
        query = """
        SELECT 
            SUM(CASE 
                WHEN mb.monto >= 0 THEN mb.monto 
                ELSE 0 
            END) as saldo_positivo,
            SUM(CASE 
                WHEN mb.monto < 0 THEN ABS(mb.monto) 
                ELSE 0 
            END) as saldo_negativo
        FROM movimientos_bancarios mb
        INNER JOIN cuentas_bancarias cb ON mb.id_cuenta_bancaria = cb.id_cuenta_bancaria
        WHERE mb.conciliado = 1
        """
        result = self.db.execute_query(query)
        if result:
            summary['saldo_bancos'] = float(result[0]['saldo_positivo'] or 0) - float(result[0]['saldo_negativo'] or 0)
        
        # Clientes activos (con facturas en los últimos 90 días)
        query = """
        SELECT COUNT(DISTINCT id_cliente) as clientes_activos
        FROM facturas 
        WHERE id_cliente IS NOT NULL 
        AND fecha >= DATEADD(day, -90, GETDATE())
        """
        result = self.db.execute_query(query)
        summary['clientes_activos'] = int(result[0]['clientes_activos'] or 0)
        
        # Facturas pendientes de pago
        query = """
        SELECT COUNT(*) as facturas_pendientes
        FROM facturas 
        WHERE estatus = 'activa' 
        AND fecha_vencimiento IS NOT NULL 
        AND fecha_vencimiento < GETDATE()
        """
        result = self.db.execute_query(query)
        summary['facturas_pendientes'] = int(result[0]['facturas_pendientes'] or 0)
        
        # Conciliaciones pendientes
        query = """
        SELECT COUNT(*) as conciliaciones_pendientes
        FROM conciliaciones 
        WHERE estatus = 'pendiente'
        """
        result = self.db.execute_query(query)
        summary['conciliaciones_pendientes'] = int(result[0]['conciliaciones_pendientes'] or 0)
        
        # Cálculo de utilidad
        summary['utilidad_neta'] = summary['total_ventas'] - summary['total_gastos']
        if summary['total_ventas'] > 0:
            summary['margen_utilidad'] = (summary['utilidad_neta'] / summary['total_ventas']) * 100
        
        return summary
    
    def get_saldos_por_cuenta(self, top_n=10):
        """Saldos por cuenta contable"""
        query = """
        SELECT 
            cc.codigo,
            cc.nombre,
            cc.tipo,
            SUM(CASE 
                WHEN ac.debe > 0 THEN ac.debe 
                ELSE 0 
            END) as total_debe,
            SUM(CASE 
                WHEN ac.haber > 0 THEN ac.haber 
                ELSE 0 
            END) as total_haber,
            (SUM(CASE 
                WHEN cc.naturaleza = 'Débito' THEN ac.debe - ac.haber
                ELSE ac.haber - ac.debe
            END)) as saldo
        FROM cuentas_contables cc
        LEFT JOIN asientos_contables ac ON cc.codigo = ac.id_cuenta
        WHERE cc.nivel = 3  -- Cuentas de detalle
        GROUP BY cc.codigo, cc.nombre, cc.tipo, cc.naturaleza
        HAVING (SUM(CASE 
                WHEN cc.naturaleza = 'Débito' THEN ac.debe - ac.haber
                ELSE ac.haber - ac.debe
            END)) != 0
        ORDER BY ABS(saldo) DESC
        """
        result = self.db.execute_query(query)
        return result[:top_n]
    
    def get_facturas_recientes(self, limit=10):
        """Facturas recientes"""
        query = """
        SELECT TOP(?) 
            f.id_factura,
            f.tipo,
            f.folio,
            f.fecha,
            COALESCE(c.nombre, p.nombre) as nombre_cliente_proveedor,
            f.total,
            f.estatus,
            f.fecha_vencimiento
        FROM facturas f
        LEFT JOIN clientes c ON f.id_cliente = c.id_cliente
        LEFT JOIN proveedores p ON f.id_proveedor = p.id_proveedor
        WHERE f.estatus = 'activa'
        ORDER BY f.fecha DESC
        """
        return self.db.execute_query(query, (limit,))
    
    def get_conciliaciones_pendientes(self):
        """Conciliaciones bancarias pendientes"""
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
        return self.db.execute_query(query)
    
    def get_ventas_mensuales(self, meses=6):
        """Ventas mensuales para gráfico"""
        query = f"""
        SELECT 
            FORMAT(f.fecha, 'yyyy-MM') as mes,
            SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END) as ventas,
            SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END) as gastos
        FROM facturas f
        WHERE f.fecha >= DATEADD(month, -{meses}, GETDATE())
        AND f.estatus = 'activa'
        GROUP BY FORMAT(f.fecha, 'yyyy-MM')
        ORDER BY mes
        """
        df = self.db.execute_query_df(query)
        
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
                title='Ventas vs Gastos (Últimos 6 meses)',
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
        return None
    
    def get_saldos_por_tipo_cuenta(self):
        """Saldos por tipo de cuenta (Activo, Pasivo, Capital, etc.)"""
        query = """
        SELECT 
            cc.tipo,
            SUM(CASE 
                WHEN cc.naturaleza = 'Débito' THEN ac.debe - ac.haber
                ELSE ac.haber - ac.debe
            END) as saldo_total
        FROM cuentas_contables cc
        LEFT JOIN asientos_contables ac ON cc.codigo = ac.id_cuenta
        WHERE cc.nivel = 2  -- Cuentas de mayor
        GROUP BY cc.tipo
        HAVING SUM(CASE 
                WHEN cc.naturaleza = 'Débito' THEN ac.debe - ac.haber
                ELSE ac.haber - ac.debe
            END) != 0
        """
        df = self.db.execute_query_df(query)
        
        if not df.empty:
            fig = px.pie(df, values='saldo_total', names='tipo', 
                        title='Distribución por Tipo de Cuenta')
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400, plot_bgcolor='white')
            return fig.to_json()
        return None
    
    def get_top_clientes(self, limit=5):
        """Top clientes por volumen de compras"""
        query = """
        SELECT TOP(?) 
            c.nombre,
            SUM(f.total) as total_compras,
            COUNT(f.id_factura) as cantidad_facturas
        FROM facturas f
        INNER JOIN clientes c ON f.id_cliente = c.id_cliente
        WHERE f.tipo = 'ingreso' 
        AND f.estatus = 'activa'
        AND f.fecha >= DATEADD(month, -12, GETDATE())
        GROUP BY c.nombre
        ORDER BY total_compras DESC
        """
        return self.db.execute_query(query, (limit,))
    
    def get_movimientos_bancarios_recientes(self, limit=10):
        """Movimientos bancarios recientes"""
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
        return self.db.execute_query(query, (limit,))
    
    def get_alertas_sistema(self):
        """Alertas del sistema"""
        alertas = []
        
        # Facturas vencidas
        query = """
        SELECT 'Factura Vencida' as tipo, 
               'Factura ' + f.folio + ' vencida el ' + CONVERT(VARCHAR, f.fecha_vencimiento) as descripcion,
               'high' as prioridad
        FROM facturas f
        WHERE f.estatus = 'activa' 
        AND f.fecha_vencimiento < GETDATE()
        """
        result = self.db.execute_query(query)
        alertas.extend(result)
        
        # Asientos desbalanceados
        query = """
        SELECT 'Asiento Desbalanceado' as tipo,
               'Comprobante ' + ac.id_comprobante_tipo + '-' + ac.id_comprobante_folio as descripcion,
               'medium' as prioridad
        FROM asientos_contables ac
        GROUP BY ac.id_comprobante_tipo, ac.id_comprobante_folio
        HAVING ABS(SUM(ac.debe) - SUM(ac.haber)) > 0.01
        """
        result = self.db.execute_query(query)
        alertas.extend(result)
        
        # Cuentas sin movimiento en 30 días
        query = """
        SELECT 'Cuenta Inactiva' as tipo,
               'Cuenta ' + cc.codigo + ' - ' + cc.nombre + ' sin movimiento en 30 días' as descripcion,
               'low' as prioridad
        FROM cuentas_contables cc
        LEFT JOIN asientos_contables ac ON cc.codigo = ac.id_cuenta
        WHERE ac.fecha IS NULL OR ac.fecha < DATEADD(day, -30, GETDATE())
        GROUP BY cc.codigo, cc.nombre
        HAVING COUNT(ac.id_cuenta) > 0
        """
        result = self.db.execute_query(query)
        alertas.extend(result)
        
        return alertas
    
    def get_estado_resultados_mensual(self):
        """Estado de resultados mensual"""
        query = """
        SELECT 
            FORMAT(f.fecha, 'yyyy-MM') as mes,
            SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END) as ingresos,
            SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END) as gastos,
            SUM(CASE WHEN f.tipo = 'ingreso' THEN f.total ELSE 0 END) - 
            SUM(CASE WHEN f.tipo = 'egreso' THEN f.total ELSE 0 END) as utilidad
        FROM facturas f
        WHERE f.fecha >= DATEADD(month, -5, GETDATE())
        AND f.estatus = 'activa'
        GROUP BY FORMAT(f.fecha, 'yyyy-MM')
        ORDER BY mes
        """
        return self.db.execute_query_df(query)