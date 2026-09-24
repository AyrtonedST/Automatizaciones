import os
import json
from jinja2 import Template
from weasyprint import HTML

# 1. Recuperar los datos que envió Dynatrace (como texto) y convertirlos a listas de Python
try:
    totals_data = json.loads(os.environ.get('TOTALS_JSON', '[]'))
    errors_data = json.loads(os.environ.get('ERRORS_JSON', '[]'))
except Exception as e:
    print(f"Error parseando el JSON: {e}")
    totals_data = []
    errors_data = []

# 2. Tu diseño HTML exacto
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
    <h2 style="color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">Dashboard: Integración de Pólizas</h2>
    
    <h3 style="color: #475569;">1. Flujo de Datos (Embudo)</h3>
    <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
        
        <p style="margin: 0 0 5px 0; font-size: 14px; font-weight: bold;">Origen</p>
        <div style="background-color: #e2e8f0; width: 100%; border-radius: 4px; margin-bottom: 15px;">
           <div style="background-color: #3b82f6; width: {{ totals[0].Pct_Origen }}%; padding: 4px 10px; color: white; text-align: right; border-radius: 4px; box-sizing: border-box; font-size: 12px; font-weight: bold;">
              {{ totals[0].Origen }}
           </div>
        </div>

        <p style="margin: 0 0 5px 0; font-size: 14px; font-weight: bold;">Transfer</p>
        <div style="background-color: #e2e8f0; width: 100%; border-radius: 4px; margin-bottom: 15px;">
           <div style="background-color: #f59e0b; width: {{ totals[0].Pct_Transfer }}%; padding: 4px 10px; color: white; text-align: right; border-radius: 4px; box-sizing: border-box; font-size: 12px; font-weight: bold;">
              {{ totals[0].Transfer }}
           </div>
        </div>

        <p style="margin: 0 0 5px 0; font-size: 14px; font-weight: bold;">Destino</p>
        <div style="background-color: #e2e8f0; width: 100%; border-radius: 4px; margin-bottom: 10px;">
           <div style="background-color: #10b981; width: {{ totals[0].Pct_Destino }}%; padding: 4px 10px; color: white; text-align: right; border-radius: 4px; box-sizing: border-box; font-size: 12px; font-weight: bold;">
              {{ totals[0].Destino }}
           </div>
        </div>
    </div>

    <h3 style="color: #ef4444;">2. Detalle de Errores</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr style="background-color: #fee2e2; text-align: left;">
        <th style="padding: 10px; border: 1px solid #fca5a5;">Póliza</th>
        <th style="padding: 10px; border: 1px solid #fca5a5;">Mensaje de Error</th>
      </tr>
      {% for record in errors %}
      <tr>
        <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{{ record.NUMERO_POLIZA }}</strong></td>
        <td style="padding: 10px; border: 1px solid #e2e8f0; color: #b91c1c;">{{ record.MENSAJERR }}</td>
      </tr>
      {% else %}
      <tr>
        <td colspan="2" style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; color: #10b981;">No se detectaron pólizas con error.</td>
      </tr>
      {% endfor %}
    </table>
</body>
</html>
"""

# 3. Inyectar los datos de Grail en el HTML
template = Template(html_template)
rendered_html = template.render(totals=totals_data, errors=errors_data)

# 4. Generar el PDF físico
HTML(string=rendered_html).write_pdf("reporte_polizas.pdf")
print("PDF generado y guardado como reporte_polizas.pdf")
