# utils/pdf_conciliacion.py
from weasyprint import HTML, CSS
from io import BytesIO

def generar_pdf_conciliacion(conciliacion):
    """
    Genera un PDF a partir de los datos de una conciliación.
    :param conciliacion: dict con los datos de la conciliación
    :return: BytesIO con el PDF
    """
    # Formatear fechas
    fecha_inicio = conciliacion['fecha_inicio'].strftime('%d/%m/%Y')
    fecha_fin = conciliacion['fecha_fin'].strftime('%d/%m/%Y')
    fecha_conc = conciliacion['fecha_conciliacion'].strftime('%d/%m/%Y %H:%M') if conciliacion['fecha_conciliacion'] else '—'

    # HTML del PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ color: #2c3e50; margin: 0; }}
            .info {{ margin-bottom: 20px; }}
            .saldos {{ display: flex; justify-content: space-between; margin: 20px 0; }}
            .saldo-box {{ text-align: center; padding: 15px; background: #f9f9f9; border-radius: 6px; flex: 1; margin: 0 10px; }}
            .diferencia {{ text-align: center; margin: 20px 0; padding: 15px; background: #f1f1f1; border-radius: 6px; }}
            .diferencia-valor {{ font-size: 1.4em; font-weight: bold; 
                color: {'green' if conciliacion['diferencia'] == 0 else ('red' if conciliacion['diferencia'] > 0 else 'blue')}; }}
            .observaciones {{ margin-top: 20px; padding: 15px; background: #f1f1f1; border-radius: 6px; }}
            .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>DETALLE DE CONCILIACIÓN BANCARIA</h1>
            <p>Reporte generado desde el sistema Conta</p>
        </div>

        <div class="info">
            <p><strong>Banco:</strong> {conciliacion['nombre_banco']}</p>
            <p><strong>Cuenta:</strong> {conciliacion['numero_cuenta']}</p>
            <p><strong>Periodo:</strong> {fecha_inicio} → {fecha_fin}</p>
            <p><strong>Estado:</strong> 
                <span style="color: {'green' if conciliacion['estatus'] == 'conciliada' else 'orange'};">
                    {'Conciliada' if conciliacion['estatus'] == 'conciliada' else 'Pendiente'}
                </span>
            </p>
            <p><strong>Conciliada el:</strong> {fecha_conc}
                {f" por {conciliacion['usuario_concilia']}" if conciliacion['usuario_concilia'] else ""}
            </p>
        </div>

        <div class="saldos">
            <div class="saldo-box">
                <p>Saldo según banco</p>
                <p style="font-size: 1.3em; font-weight: bold;">₡{conciliacion['saldo_banco']:,.2f}</p>
            </div>
            <div class="saldo-box">
                <p>Saldo según sistema</p>
                <p style="font-size: 1.3em; font-weight: bold;">₡{conciliacion['saldo_sistema']:,.2f}</p>
            </div>
        </div>

        <div class="diferencia">
            <p>Diferencia</p>
            <p class="diferencia-valor">₡{conciliacion['diferencia']:,.2f}</p>
        </div>

        {f'''
        <div class="observaciones">
            <p><strong>Observaciones:</strong></p>
            <p>{conciliacion['observaciones']}</p>
        </div>
        ''' if conciliacion['observaciones'] else ''}
        
        <div class="footer">
            <p>Documento generado el {conciliacion['fecha_conciliacion'].strftime('%d/%m/%Y %H:%M') if conciliacion['fecha_conciliacion'] else '—'}</p>
        </div>
    </body>
    </html>
    """

    # Generar PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer