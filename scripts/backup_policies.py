import os
import sys
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
    
    # Manejo de la opción "Otro"
    producto_objetivo = os.environ["PRODUCTO"]
    if "Otro" in producto_objetivo:
        producto_objetivo = os.environ.get("PRODUCTO_OTRO", "").strip()
        if not producto_objetivo:
            print("❌ Error: Seleccionaste 'Otro' pero dejaste el campo de texto vacío.")
            sys.exit(1)

    # Crear carpeta de backups
    os.makedirs("backups", exist_ok=True)
    
    # Leer Excel y filtrar
    try:
        df = pd.read_excel("inventario_apis.xlsx")
        df_filtrado = df[df['Servicio'].str.strip() == producto_objetivo]
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        sys.exit(1)

    if df_filtrado.empty:
        print(f"❌ No se encontraron APIs en el Excel para el servicio: '{producto_objetivo}'")
        sys.exit(1)

    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"
    
    hubo_errores = False

    print(f"--- Iniciando BACKUP para: {producto_objetivo} ---")
    for index, row in df_filtrado.iterrows():
        api_id = str(row['API']).strip()
        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        
        response = requests.get(policy_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            policy_xml = data.get("properties", {}).get("value", "")
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(policy_xml)
            print(f"✅ Backup guardado: {api_id}.xml")
        elif response.status_code == 404:
            print(f"⚠️ La API '{api_id}' no existe en este APIM. Se omitirá el backup.")
        else:
            print(f"❌ Error al respaldar '{api_id}'. Código HTTP {response.status_code}")
            hubo_errores = True

    if hubo_errores:
        print("\n⚠️ Advertencia: Algunas APIs fallaron durante el backup.")

if __name__ == "__main__":
    main()
