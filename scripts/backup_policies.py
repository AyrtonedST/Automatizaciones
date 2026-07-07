import os
import sys
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
    
    producto_objetivo = os.environ["PRODUCTO"]
    if "Otro" in producto_objetivo:
        producto_objetivo = os.environ.get("PRODUCTO_OTRO", "").strip()
        if not producto_objetivo:
            print("❌ Error: Seleccionaste 'Otro' pero dejaste el campo vacío.")
            sys.exit(1)

    os.makedirs("backups", exist_ok=True)
    
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
    except FileNotFoundError:
        print("❌ Error: No se encontró 'Apim-Expressroute.csv'.")
        sys.exit(1)

    if not filas_a_procesar:
        print(f"❌ No se encontraron APIs para el servicio: '{producto_objetivo}'")
        sys.exit(1)

    token = get_azure_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"
    
    hubo_errores = False
    print(f"--- Iniciando BACKUP para: {producto_objetivo} ---")
    
    for row in filas_a_procesar:
        api_id = row.get('API', '').strip()
        if not api_id:
            continue
            
        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        response = requests.get(policy_url, headers=headers)
        
        if response.status_code == 200:
            policy_xml = response.json().get("properties", {}).get("value", "")
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(policy_xml)
            print(f"✅ Backup guardado: {api_id}.xml")
        elif response.status_code == 404:
            print(f"⚠️ API '{api_id}' no encontrada en el APIM.")
        else:
            print(f"❌ Error al respaldar '{api_id}'. HTTP {response.status_code}")
            hubo_errores = True

    if hubo_errores:
        print("\n⚠️ Advertencia: Algunas APIs fallaron durante el backup.")

if __name__ == "__main__":
    main()
