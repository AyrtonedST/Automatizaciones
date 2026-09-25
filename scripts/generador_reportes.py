import os
import json
from jinja2 import Template
from weasyprint import HTML

# 1. Recuperar los datos
try:
    totals_raw = os.environ.get('TOTALS_JSON', '[]')
    errors_raw = os.environ.get('ERRORS_JSON', '[]')
    
    # Manejar posibles valores nulos
    if totals_raw is None or totals_raw.strip() == '':
        totals_raw = '[]'
    if errors_raw is None or errors_raw.strip() == '':
        errors_raw = '[]'

    totals_data = json.loads(totals_raw)
    errors_data = json.loads(errors_raw)
except Exception as e:
    print(f"Error parseando el JSON: {e}")
    # Fallback a datos de prueba si falla el parseo
    totals_data = [{"Origen": 100, "Pct_Origen": 100, "Transfer": 95, "Pct_Transfer": 95, "Destino": 90, "Pct_Destino": 90}]
    errors_data = []

# 2. Plantilla HTML (Tu diseño original intacto)
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 0 auto; color: #333; padding: 20px; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: baseline; }
        .title { color: #0f172a; margin: 0; font-size: 24px; }
        .subtitle { color: #64748b; font-size: 12px; margin-top: 5px; }
        .section-title { color: #475569; font-size: 18px; margin-top: 30px; border-left: 4px solid #3b82f6; padding-left: 10px; }
        .section-title-error { color: #ef4444; font-size: 18px; margin-top: 30px; border-left: 4px solid #ef4444; padding-left: 10px; }
        
        .bar-container { background-color: #e2e8f0; width: 100%; border-radius: 4px; margin-bottom: 15px; }
        .bar-label { margin: 0 0 5px 0; font-size: 13px; font-weight: bold; color: #334155; }
        .bar-fill { padding: 4px 10px; color: white; text-align: right; border-radius: 4px; box-sizing: border-box; font-size: 12px; font-weight: bold; }
        
        table { width: 100%; border-collapse: collapse; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th { background-color: #fee2e2; color: #991b1b; padding: 12px; text-align: left; border-bottom: 2px solid #fca5a5; }
        td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; color: #475569; }
        tr:nth-child(even) { background-color: #f8fafc; } /* Estilo Cebra */
        .poliza-id { font-weight: bold; color: #1e293b; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h2 class="title">Dashboard: Integración de Pólizas</h2>
            <div class="subtitle">Reporte Automático generado desde Dynatrace Grail</div>
        </div>
    </div>
    
    <h3 class="section-title">1. Flujo de Datos (Embudo)</h3>
    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
        
        <p class="bar-label">Origen</p>
        <div class="bar-container">
           <div class="bar-fill" style="background-color: #3b82f6; width: {{ totals[0].Pct_Origen }}%;">
              {{ totals[0].Origen }} (100%)
           </div>
        </div>

        <p class="bar-label">Transfer</p>
        <div class="bar-container">
           <div class="bar-fill" style="background-color: #f59e0b; width: {{ totals[0].Pct_Transfer }}%;">
              {{ totals[0].Transfer }} ({{ totals[0].Pct_Transfer | round(1) }}%)
           </div>
        </div>

        <p class="bar-label">Destino</p>
        <div class="bar-container" style="margin-bottom: 0;">
           <div class="bar-fill" style="background-color: #10b981; width: {{ totals[0].Pct_Destino }}%;">
              {{ totals[0].Destino }} ({{ totals[0].Pct_Destino | round(1) }}%)
           </div>
        </div>
    </div>

    <h3 class="section-title-error">2. Detalle de Errores ({{ errors|length }} encontrados)</h3>
    <table>
      <tr>
        <th style="width: 25%;">Nº Póliza</th>
        <th>Mensaje de Error detectado en logs</th>
      </tr>
      {% for record in errors %}
      <tr>
        <td class="poliza-id">{{ record.NUMERO_POLIZA }}</td>
        <td>{{ record.MENSAJERR if record.MENSAJERR else 'Error desconocido / Timeout' }}</td>
      </tr>
      {% else %}
      <tr>
        <td colspan="2" style="text-align: center; color: #10b981; font-weight: bold; padding: 20px;">✅ No se detectaron pólizas con error en este periodo.</td>
      </tr>
      {% endfor %}
    </table>
</body>
</html>
"""

# 3. Renderizar y Guardar PDF
template = Template(html_template)
rendered_html = template.render(totals=totals_data, errors=errors_data)

HTML(string=rendered_html).write_pdf("reporte_polizas.pdf")
print("PDF generado correctamente.")
