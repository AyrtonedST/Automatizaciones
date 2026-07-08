import os
import requests

# ==========================================
# CONFIGURACIÓN DEL ENTORNO
# ==========================================
DYNATRACE_URL = os.environ.get("DT_TENANT_URL", "").rstrip('/')
API_TOKEN = os.environ.get("DT_API_TOKEN", "")
SCHEMA_ID = "builtin:davis.anomaly-detectors"

if not DYNATRACE_URL or not API_TOKEN:
    print("❌ Faltan las variables de entorno DT_TENANT_URL o DT_API_TOKEN.")
    exit(1)

HEADERS = {
    "Authorization": f"Api-Token {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_all_alerts():
    items = []
    url = f"{DYNATRACE_URL}/api/v2/settings/objects?schemaIds={SCHEMA_ID}&fields=objectId,value,scope&adminAccess=false"
    
    while url:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"❌ Error al obtener alertas: {response.status_code} - {response.text}")
            exit(1)
            
        data = response.json()
        items.extend(data.get("items", []))
        
        next_page_key = data.get("nextPageKey")
        url = f"{DYNATRACE_URL}/api/v2/settings/objects?nextPageKey={next_page_key}" if next_page_key else None
            
    return items

def update_alert(object_id, alert_title, value_payload):
    url = f"{DYNATRACE_URL}/api/v2/settings/objects/{object_id}"
    payload = {
        "schemaId": SCHEMA_ID,
        "value": value_payload
    }
    response = requests.put(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        print(f"✅ Alerta '{alert_title}' actualizada con éxito.")
    else:
        print(f"❌ Error al actualizar '{alert_title}': {response.status_code} - {response.text}")

def main():
    dry_run = os.environ.get("DRY_RUN_INPUT", "true").lower() == "true"
    if dry_run:
        print("⚠️ MODO DRY RUN ACTIVADO: No se aplicará ningún cambio en la plataforma.\n")

    raw_names_input = os.environ.get("ALERTS_NAMES_INPUT", "")
    selected_names = [name.strip() for name in raw_names_input.split(",") if name.strip()]

    if not selected_names:
        print("⚠️ No se proporcionaron nombres de alertas para modificar.")
        return

    # Leer los bloques de DQL desde los archivos
    try:
        # .strip() elimina saltos de línea vacíos al inicio/final que pueden quedar al copiar/pegar
        with open("scripts/buscar.txt", "r", encoding="utf-8") as f:
            dql_a_buscar = f.read().strip()
        with open("scripts/reemplazar.txt", "r", encoding="utf-8") as f:
            dql_nuevo = f.read().strip()
    except FileNotFoundError as e:
        print(f"❌ Error: No se encontraron los archivos de consulta. {e}")
        return

    if not dql_a_buscar or not dql_nuevo:
        print("❌ Error: Los archivos buscar.txt o reemplazar.txt están vacíos.")
        return

    print("Descargando inventario de alertas desde Dynatrace...")
    todas_las_alertas = get_all_alerts()
    alerts_modificadas = 0

    for alert in todas_las_alertas:
        object_id = alert.get("objectId")
        value = alert.get("value", {})
        
        alert_title = value.get('name', value.get('title', 'Sin título'))
        
        if alert_title not in selected_names:
            continue

        print(f"\nProcesando coincidencia encontrada: '{alert_title}' ({object_id})")

        analyzer_inputs = value.get("analyzer", {}).get("input", [])
        modificado = False

        # Buscar el campo de la query DQL
        for input_field in analyzer_inputs:
            if input_field.get("key") == "query.expression":
                query_actual = input_field.get("value", "")
                
                # Búsqueda literal exacta
                if dql_a_buscar in query_actual:
                    nueva_query = query_actual.replace(dql_a_buscar, dql_nuevo)
                    input_field["value"] = nueva_query
                    modificado = True
                    print(f"   * Bloque DQL encontrado y reemplazado en memoria.")
                else:
                    print(f"   -> El bloque DQL a buscar no se encontró en esta alerta (quizás ya fue actualizado o tiene un espaciado diferente).")

        # Guardar cambios
        if modificado:
            if not dry_run:
                update_alert(object_id, alert_title, value)
            else:
                print(f"   -> [DRY RUN] La alerta requeriría un PUT a la API (Omitido).")
                
            alerts_modificadas += 1

    print(f"\n--------------------------------------------------")
    if dry_run:
        print(f"Simulación completada. {alerts_modificadas} consultas habrían sido modificadas.")
    else:
        print(f"Proceso completado. Consultas modificadas: {alerts_modificadas}")

if __name__ == "__main__":
    main()
