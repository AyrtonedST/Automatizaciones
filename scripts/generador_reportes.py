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

# 2. PLANTILLA PDF (Modo Claro - Estilo Dashboard)
html_pdf = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 20px; }
        .header-box { background-color: #276749; color: white; padding: 12px; text-align: center; font-weight: bold; font-size: 18px; border-radius: 4px; margin-bottom: 20px; }
        
        .card { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 15px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-title { color: #374151; font-size: 15px; margin-top: 0; margin-bottom: 15px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; font-weight: bold; }
        
        .bar-label { font-size: 12px; margin: 5px 0; color: #4b5563; font-weight: bold; }
        .bar-bg { background-color: #e5e7eb; width: 100%; height: 22px; border-radius: 2px; margin-bottom: 15px; position: relative; }
        .bar-fill { height: 100%; border-radius: 2px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; font-size: 12px; font-weight: bold; color: white; }
        
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th { background-color: #f9fafb; color: #4b5563; padding: 10px; text-align: left; border: 1px solid #e5e7eb; }
        td { padding: 10px; border: 1px solid #e5e7eb; color: #1f2937; }
        tr:nth-child(even) { background-color: #f9fafb; }
        .poliza-id { font-weight: bold; color: #111827; }
    </style>
</head>
<body>
    <div class="header-box">Status Actual - Integración de Pólizas</div>
    
    <div class="card">
        <h3 class="card-title">Funnel Pólizas</h3>
        <p class="bar-label">Origen</p>
        <div class="bar-bg">
            <div class="bar-fill" style="background-color: #dc2626; width: {{ totals[0].Pct_Origen }}%;">{{ totals[0].Origen }}</div>
        </div>
        <p class="bar-label">Transfer</p>
        <div class="bar-bg">
            <div class="bar-fill" style="background-color: #d97706; width: {{ totals[0].Pct_Transfer }}%;">{{ totals[0].Transfer }}</div>
        </div>
        <p class="bar-label">Destino</p>
        <div class="bar-bg" style="margin-bottom: 0;">
            <div class="bar-fill" style="background-color: #2563eb; width: {{ totals[0].Pct_Destino }}%;">{{ totals[0].Destino }}</div>
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
                <td style="color: #dc2626;">{{ record.MENSAJERR }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="2" style="text-align: center; color: #059669; padding: 15px; font-weight: bold;">No se encontraron pólizas con errores.</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# 3. PLANTILLA HTML PARA EL CORREO (Solo resumen directo)
html_email = """
<div style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
    <h2 style="color: #276749; margin-bottom: 5px;">Resumen de Integración de Pólizas</h2>
    
    <div style="background-color: #f7fafc; border-left: 4px solid #2b6cb0; padding: 15px; margin: 15px 0; border-radius: 4px;">
        <ul style="list-style-type: none; padding: 0; margin: 0; font-size: 15px;">
            <li style="margin-bottom: 10px;">📊 <strong>Pólizas en Origen:</strong> {{ totals[0].Origen if totals else 0 }}</li>
            <li style="margin-bottom: 10px;">✅ <strong>Pólizas procesadas a Destino:</strong> {{ totals[0].Destino if totals else 0 }}</li>
            <li>⚠️ <strong>Cantidad de Errores:</strong> <span style="color: #e53e3e; font-weight: bold;">{{ errors|length }}</span></li>
        </ul>
    </div>
    
    <p style="font-size: 13px; color: #666; margin-top: 20px;">Revisa el PDF adjunto para ver el detalle de errores y el embudo de conversión.</p>
</div>
"""

# 4. Generar y guardar
template_pdf = Template(html_pdf)
rendered_pdf = template_pdf.render(totals=totals_data, errors=errors_data)
HTML(string=rendered_pdf).write_pdf("reporte_polizas.pdf")

template_email = Template(html_email)
rendered_email = template_email.render(totals=totals_data, errors=errors_data)
with open("resumen_email.html", "w", encoding="utf-8") as f:
    f.write(rendered_email)

print("PDF claro y resumen generados.")
