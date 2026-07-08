import os
import requests

# ==========================================
# CONFIGURACIÓN DEL ENTORNO
# ==========================================
DYNATRACE_URL = os.environ.get("DT_TENANT_URL", "").rstrip('/')
API_TOKEN = os.environ.get("DT_API_TOKEN", "")
SCHEMA_ID = "builtin:anomaly-detection.dql-rule" 

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
    url = f"{DYNATRACE_URL}/api/v2/settings/objects?schemaIds={SCHEMA_ID}&fields=objectId,value,scope&adminAccess=true"
    
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
    raw_names_input = os.environ.get("ALERTS_NAMES_INPUT", "")
    raw_props_input = os.environ.get("PROPERTIES_INPUT", "")
    
    # 1. Limpiar y separar los nombres de las alertas
    selected_names = [name.strip() for name in raw_names_input.split(",") if name.strip()]

    # 2. Convertir el input simple (key:value) en el formato que necesita Dynatrace
    properties_to_add = []
    if raw_props_input:
        pairs = raw_props_input.split(",")
        for pair in pairs:
            if ":" in pair:
                key, val = pair.split(":", 1)
                key = key.strip()
                val = val.strip()
                
                # Si el usuario ingresó solo el valor (ej. squad), lo convertimos a '{dims:squad}' automáticamente
                if not val.startswith("{"):
                    val = f"{{dims:{val}}}"
                    
                properties_to_add.append({"key": key, "value": val})

    if not selected_names:
        print("⚠️ No se proporcionaron nombres de alertas para modificar.")
        return
        
    if not properties_to_add:
        print("⚠️ No se proporcionaron propiedades válidas. Usa el formato key:value.")
        return

    print("Descargando inventario de alertas desde Dynatrace...")
    todas_las_alertas = get_all_alerts()

    alerts_modificadas = 0

    # 3. Iterar y modificar
    for alert in todas_las_alertas:
        object_id = alert.get("objectId")
        value = alert.get("value", {})
        
        alert_title = value.get('name', value.get('title', 'Sin título'))
        
        # Filtrar solo las alertas que coincidan con los nombres ingresados
        if alert_title not in selected_names:
            continue

        print(f"\nProcesando coincidencia encontrada: '{alert_title}' ({object_id})")

        event_template = value.get("eventTemplate", {})
        propiedades_actuales = event_template.get("properties", [])
        modificado = False

        # Inyectar o actualizar las propiedades
        for prop in properties_to_add:
            key_target = prop.get("key")
            val_target = prop.get("value")
            
            existe = False
            for p in propiedades_actuales:
                if p.get("key") == key_target:
                    existe = True
                    if p.get("value") != val_target:
                        p["value"] = val_target
                        modificado = True
                        print(f"   * Actualizando valor: {key_target} -> {val_target}")
                    break
            
            if not existe:
                propiedades_actuales.append({"key": key_target, "value": val_target})
                modificado = True
                print(f"   + Agregando nueva propiedad: {key_target} -> {val_target}")

        # Guardar si hubo cambios
        if modificado:
            event_template["properties"] = propiedades_actuales
            value["eventTemplate"] = event_template
            update_alert(object_id, alert_title, value)
            alerts_modificadas += 1
        else:
            print("   -> No requirió cambios (propiedades ya estaban idénticas).")

    print(f"\n--------------------------------------------------")
    print(f"Proceso completado. Alertas modificadas: {alerts_modificadas}")

if __name__ == "__main__":
    main()
