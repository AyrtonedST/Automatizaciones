import os
import sys
import re
import requests
import subprocess
import csv

def get_azure_token():
    result = subprocess.check_output(
        ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]
    )
    return result.decode("utf-8").strip()

def main():
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RG"]
    apim_name = os.environ["AZURE_APIM_NAME"]
    tipo_red = os.environ["TIPO_RED"]

    producto_objetivo = os.environ["PRODUCTO"]
    if "Otro" in producto_objetivo:
        producto_objetivo = os.environ.get("PRODUCTO_OTRO", "").strip()
        if not producto_objetivo:
            print("❌ Error: Seleccionaste 'Otro' pero dejaste el campo de texto vacío.")
            sys.exit(1)

    columna_url = 'Backend en Expressroute' if tipo_red == 'Expressroute' else 'Backend en Internet'

    filas_a_procesar = []
    
    try:
        with open('Apim-Expressroute.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                servicio_actual = row.get('Servicio', '').strip()
                
                # REGLA ESTRICTA: Solo procesa si el texto es exactamente igual al buscado
                if servicio_actual == producto_objetivo:
                    filas_a_procesar.append(row)
    except Exception as e:
        print(f"❌ Error al leer el CSV: {e}")
        sys.exit(1)

    if not filas_a_procesar:
        print(f"❌ No se encontraron APIs en el CSV para el servicio exacto: '{producto_objetivo}'")
        sys.exit(1)

    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json", 
        "Accept": "application/json",
        "If-Match": "*"
    }
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"

    print(f"--- Iniciando ACTUALIZACIÓN hacia: {tipo_red} para el servicio: {producto_objetivo} ---")

    hubo_errores = False

    for row in filas_a_procesar:
        api_id = row.get('API', '').strip()
        nueva_url = row.get(columna_url, '').strip()
        backup_path = f"backups/{api_id}.xml"
        
        if not os.path.exists(backup_path):
            print(f"⏩ Omitiendo '{api_id}': No se encontró su archivo de backup previo.")
            continue
            
        if not nueva_url:
            print(f"⏩ Omitiendo '{api_id}': La URL en la columna '{columna_url}' está vacía.")
            continue

        with open(backup_path, "r", encoding="utf-8") as f:
            policy_modificada = f.read()

        # Regex robusta para buscar la etiqueta de set-backend-service sin importar el formato de cierre
        if re.search(r'<set-backend-service\b', policy_modificada, re.IGNORECASE):
            policy_modificada = re.sub(
                r'<set-backend-service\b[^>]*\/?>', 
                f'<set-backend-service base-url="{nueva_url}" />', 
                policy_modificada, 
                flags=re.IGNORECASE
            )
            accion = "Reemplazada"
        else:
            # Si no existe la etiqueta en el inbound, la inyectamos antes de cerrar </inbound>
            etiqueta = f'\n        <set-backend-service base-url="{nueva_url}" />\n    </inbound>'
            policy_modificada = re.sub(
                r'<\/inbound>', 
                etiqueta, 
                policy_modificada, 
                flags=re.IGNORECASE
            )
            accion = "Inyectada"

        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        payload = {"properties": {"format": "xml", "value": policy_modificada}}
        
        put_response = requests.put(policy_url, headers=headers, json=payload)
        
        if put_response.status_code in [200, 201]:
            print(f"✅ {api_id}: URL {accion} exitosamente -> {nueva_url}")
        else:
            print(f"❌ {api_id}: Error HTTP {put_response.status_code} - {put_response.text}")
            hubo_errores = True

    if hubo_errores:
        print("\n❌ El proceso de actualización finalizó con errores en algunas APIs.")
        sys.exit(1)
    else:
        print("\n🎉 ¡Todas las APIs se actualizaron correctamente!")

if __name__ == "__main__":
    main()
