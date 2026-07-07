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

    columna_url = 'Backend en Expressroute' if tipo_red == 'Expressroute' else 'Backend en Internet'

    filas_a_procesar = []
    ultimo_servicio = ""
    
    try:
        with open('Apim-Expressroute.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                servicio_actual = row.get('Servicio', '').strip()
                if servicio_actual:
                    ultimo_servicio = servicio_actual
                else:
                    servicio_actual = ultimo_servicio
                
                if servicio_actual == producto_objetivo:
                    filas_a_procesar.append(row)
    except Exception as e:
        print(f"❌ Error al leer el CSV: {e}")
        sys.exit(1)

    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json", 
        "If-Match": "*"
    }
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"

    print(f"--- Iniciando ACTUALIZACIÓN hacia: {tipo_red} ---")

    for row in filas_a_procesar:
        api_id = row.get('API', '').strip()
        nueva_url = row.get(columna_url, '').strip()
        backup_path = f"backups/{api_id}.xml"
        
        if not os.path.exists(backup_path):
            print(f"⏩ Omitiendo '{api_id}': No hay backup previo.")
            continue
            
        if not nueva_url:
            print(f"⏩ Omitiendo '{api_id}': URL vacía en columna {columna_url}.")
            continue

        with open(backup_path, "r", encoding="utf-8") as f:
            policy_modificada = f.read()

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

        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        payload = {"properties": {"format": "xml", "value": policy_modificada}}
        
        put_response = requests.put(policy_url, headers=headers, json=payload)
        
        if put_response.status_code in [200, 201]:
            print(f"✅ {api_id}: URL {accion} -> {nueva_url}")
        else:
            print(f"❌ {api_id}: Error HTTP {put_response.status_code} - {put_response.text}")

if __name__ == "__main__":
    main()
