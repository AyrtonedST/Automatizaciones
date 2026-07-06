import os
import json
import re
import requests
import subprocess
import sys

def get_azure_token():
    result = subprocess.check_output(
        ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]
    )
    return result.decode("utf-8").strip()

def main():
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RG"]
    apim_name = os.environ["AZURE_APIM_NAME"]
    producto_objetivo = os.environ["PRODUCTO"]
    nueva_url = os.environ["NUEVA_URL"]

    # Crear directorio para almacenar los respaldos
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    with open("apis_config.json", "r") as f:
        config = json.load(f)

    if producto_objetivo not in config:
        print(f"Error: El producto '{producto_objetivo}' no existe en apis_config.json")
        sys.exit(1)

    apis_a_actualizar = config[producto_objetivo]
    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "If-Match": "*" 
    }

    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"
    api_version = "?api-version=2022-08-01"

    print(f"Iniciando actualización para el producto: {producto_objetivo}")
    print(f"Nueva URL de backend: {nueva_url}\n")

    for api_id in apis_a_actualizar:
        policy_url = f"{base_url_azure}/{api_id}/policies/policy{api_version}"
        
        response = requests.get(policy_url, headers=headers)
        
        if response.status_code == 404:
            print(f"⚠️ API '{api_id}' no encontrada en el APIM. Omitiendo...")
            continue
        elif response.status_code != 200:
            print(f"❌ Error al obtener '{api_id}': {response.text}")
            continue

        data = response.json()
        policy_xml = data.get("properties", {}).get("value", "")

        if not policy_xml:
            print(f"⚠️ API '{api_id}' no tiene un XML válido. Omitiendo...")
            continue

        # --- FASE DE BACKUP ---
        backup_path = os.path.join(backup_dir, f"{api_id}_backup.xml")
        with open(backup_path, "w", encoding="utf-8") as bf:
            bf.write(policy_xml)
        print(f"💾 Backup original guardado localmente para {api_id}")

        # --- FASE DE MODIFICACIÓN ---
        policy_modificada = policy_xml
        if '<set-backend-service' in policy_modificada:
            policy_modificada = re.sub(
                r'<set-backend-service[^>]*\/>', 
                f'<set-backend-service base-url="{nueva_url}" />', 
                policy_modificada,
                flags=re.IGNORECASE
            )
            accion = "Reemplazada"
        else:
            etiqueta = f'\n        <set-backend-service base-url="{nueva_url}" />\n    </inbound>'
            policy_modificada = re.sub(
                r'<\/inbound>', 
                etiqueta, 
                policy_modificada,
                flags=re.IGNORECASE
            )
            accion = "Inyectada"

        payload = {
            "properties": {
                "format": "xml",
                "value": policy_modificada
            }
        }
        
        put_response = requests.put(policy_url, headers=headers, json=payload)
        
        if put_response.status_code in [200, 201]:
            print(f"✅ {api_id}: Política {accion} exitosamente.\n")
        else:
            print(f"❌ {api_id}: Error al guardar política. {put_response.text}\n")

if __name__ == "__main__":
    main()
