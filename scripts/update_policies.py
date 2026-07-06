import os
import sys
import re
import requests
import subprocess
import pandas as pd

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

    # Manejo de la opción "Otro"
    producto_objetivo = os.environ["PRODUCTO"]
    if "Otro" in producto_objetivo:
        producto_objetivo = os.environ.get("PRODUCTO_OTRO", "").strip()

    # Definir de qué columna sacar la URL
    columna_url = 'Backend en Expressroute' if tipo_red == 'Expressroute' else 'Backend en Internet'

    # Leer Excel
    try:
        df = pd.read_excel("inventario_apis.xlsx")
        df_filtrado = df[df['Servicio'].str.strip() == producto_objetivo]
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        sys.exit(1)

    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json", 
        "If-Match": "*"
    }
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"

    print(f"--- Iniciando ACTUALIZACIÓN hacia: {tipo_red} ---")
    print(f"Columna objetivo del Excel: '{columna_url}'\n")

    for index, row in df_filtrado.iterrows():
        api_id = str(row['API']).strip()
        backup_path = f"backups/{api_id}.xml"
        
        # Validación 1: ¿Existe el backup? Si falló el backup en el paso 1, no modificamos por seguridad
        if not os.path.exists(backup_path):
            print(f"⏩ Omitiendo '{api_id}': No se encontró su archivo de backup original.")
            continue
            
        # Validación 2: ¿Hay una URL configurada en el Excel para esta API?
        if pd.isna(row[columna_url]) or str(row[columna_url]).strip() == "":
            print(f"⏩ Omitiendo '{api_id}': La celda en la columna '{columna_url}' está vacía.")
            continue

        nueva_url = str(row[columna_url]).strip()

        # Leer la política original desde el backup
        with open(backup_path, "r", encoding="utf-8") as f:
            policy_modificada = f.read()

        # Lógica de inyección/reemplazo
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

        # Enviar actualización a Azure
        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        payload = {
            "properties": {
                "format": "xml", 
                "value": policy_modificada
            }
        }
        
        put_response = requests.put(policy_url, headers=headers, json=payload)
        
        if put_response.status_code in [200, 201]:
            print(f"✅ {api_id}: Política {accion}. Nueva URL -> {nueva_url}")
        else:
            print(f"❌ {api_id}: Error al subir. HTTP {put_response.status_code} - {put_response.text}")

if __name__ == "__main__":
    main()
