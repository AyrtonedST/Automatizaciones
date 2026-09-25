import os
import json
from jinja2 import Template
from weasyprint import HTML

# 1. Recuperar los datos de Dynatrace
try:
    totals_raw = os.environ.get('TOTALS_JSON', '[]')
    errors_raw = os.environ.get('ERRORS_JSON', '[]')
    
    if not totals_raw or totals_raw.strip() == '': totals_raw = '[]'
    if not errors_raw or errors_raw.strip() == '': errors_raw = '[]'

    totals_data = json.loads(totals_raw)
    errors_data = json.loads(errors_raw)
except Exception as e:
    print(f"Error parseando el JSON: {e}")
    totals_data = [{"Origen": 0, "Pct_Origen": 0, "Transfer": 0, "Pct_Transfer": 0, "Destino": 0, "Pct_Destino": 0}]
    errors_data = []

# 2. PLANTILLA PDF (Tema Oscuro estilo Dashboard)
html_pdf = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #1e1e24; color: #e2e8f0; margin: 0; padding: 20px; }
        .header-box { background-color: #276749; color: white; padding: 12px; text-align: center; font-weight: bold; font-size: 18px; border-radius: 4px; margin-bottom: 20px; }
        .card { background-color: #25262b; border: 1px solid #373940; border-radius: 6px; padding: 15px; margin-bottom: 20px; }
        .card-title { color: #a0aec0; font-size: 14px; margin-top: 0; margin-bottom: 15px; border-bottom: 1px solid #373940; padding-bottom: 8px; }
        
        .bar-label { font-size: 12px; margin: 5px 0; color: #cbd5e0; }
        .bar-bg { background-color: #1a1b1f; width: 100%; height: 22px; border-radius: 2px; margin-bottom: 15px; position: relative; }
        .bar-fill { height: 100%; border-radius: 2px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; font-size: 12px; font-weight: bold; color: white; }
        
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th { background-color: #1a1b1f; color: #a0aec0; padding: 10px; text-align: left; border: 1px solid #373940; }
        td { padding: 10px; border: 1px solid #373940; color: #e2e8f0; }
        tr:nth-child(even) { background-color: #2c2e33; }
        .poliza-id { font-weight: bold; color: #fff; }
    </style>
</head>
<body>
    <div class="header-box">Status Actual - Integración de Pólizas</div>
    
    <div class="card">
        <h3 class="card-title">Funnel Pólizas</h3>
        <p class="bar-label">Origen</p>
        <div class="bar-bg">
            <div class="bar-fill" style="background-color: #c53030; width: {{ totals[0].Pct_Origen }}%;">{{ totals[0].Origen }}</div>
        </div>
        <p class="bar-label">Transfer</p>
        <div class="bar-bg">
            <div class="bar-fill" style="background-color: #b7791f; width: {{ totals[0].Pct_Transfer }}%;">{{ totals[0].Transfer }}</div>
        </div>
        <p class="bar-label">Destino</p>
        <div class="bar-bg" style="margin-bottom: 0;">
            <div class="bar-fill" style="background-color: #2b6cb0; width: {{ totals[0].Pct_Destino }}%;">{{ totals[0].Destino }}</div>
        </div>
    </div>

    <div class="card">
        <h3 class="card-title">Pólizas con Errores</h3>
        <table>
            <tr>
                <th style="width: 20%;">NUMERO_POLIZA</th>
                <th>MENSAJERR</th>
            </tr>
            {% for record in errors %}
            <tr>
                <td class="poliza-id">{{ record.NUMERO_POLIZA }}</td>
                <td style="color: #fc8181;">{{ record.MENSAJERR }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="2" style="text-align: center; color: #68d391; padding: 15px;">No se encontraron pólizas con errores.</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# 3. PLANTILLA HTML PARA EL CUERPO DEL CORREO
html_email = """
<div style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
    <h2 style="color: #276749;">Resumen de Integración de Pólizas</h2>
    <p>Hola, se ha generado el reporte automatizado desde Dynatrace. Aquí tienes un resumen rápido de los resultados:</p>
    
    <div style="background-color: #f7fafc; border-left: 4px solid #2b6cb0; padding: 15px; margin: 20px 0; border-radius: 4px;">
        <ul style="list-style-type: none; padding: 0; margin: 0; font-size: 15px;">
            <li style="margin-bottom: 10px;">📊 <strong>Pólizas en Origen:</strong> {{ totals[0].Origen if totals else 0 }}</li>
            <li style="margin-bottom: 10px;">✅ <strong>Pólizas procesadas a Destino:</strong> {{ totals[0].Destino if totals else 0 }}</li>
            <li>⚠️ <strong>Cantidad de Errores:</strong> <span style="color: #e53e3e; font-weight: bold;">{{ errors|length }}</span></li>
        </ul>
    </div>
    
    <p>Para ver el detalle completo de los errores y el embudo de conversión, por favor revisa el PDF adjunto.</p>
</div>
"""

# 4. Generar y guardar los archivos
# Guardar PDF
template_pdf = Template(html_pdf)
rendered_pdf = template_pdf.render(totals=totals_data, errors=errors_data)
HTML(string=rendered_pdf).write_pdf("reporte_polizas.pdf")

# Guardar Email Body
template_email = Template(html_email)
rendered_email = template_email.render(totals=totals_data, errors=errors_data)
with open("resumen_email.html", "w", encoding="utf-8") as f:
    f.write(rendered_email)

print("Archivos generados exitosamente.")
