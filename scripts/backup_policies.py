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
    
    try:
        with open('Apim-Expressroute.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                servicio_actual = row.get('Servicio', '').strip()
                if servicio_actual == producto_objetivo:
                    filas_a_procesar.append(row)
    except FileNotFoundError:
        print("❌ Error: No se encontró 'Apim-Expressroute.csv'.")
        sys.exit(1)

    if not filas_a_procesar:
        print(f"❌ No se encontraron APIs para el servicio exacto: '{producto_objetivo}'")
        sys.exit(1)

    token = get_azure_token()
    headers = {
        "Authorization": f"Bearer {token}", 
        "Accept": "application/json"
    }
    base_url_azure = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ApiManagement/service/{apim_name}/apis"
    
    plantilla_base = """<policies>
    <inbound>
        <base />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>"""

    print(f"--- Iniciando BACKUP SEGURO para: {producto_objetivo} ---")
    
    for row in filas_a_procesar:
        api_id = row.get('API', '').strip()
        if not api_id:
            continue
            
        # 1. Agregado format=rawxml para traer el código puro
        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01&format=rawxml"
        response = requests.get(policy_url, headers=headers)
        
        if response.status_code == 200:
            policy_xml = response.text.strip()
            
            # 2. Seguro CRÍTICO: Falla el job si el texto está vacío
            if not policy_xml:
                print(f"❌ CRÍTICO: La API '{api_id}' devolvió un texto vacío. Abortando para proteger Producción.")
                sys.exit(1) 
                
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(policy_xml)
            print(f"✅ Backup guardado exitosamente: {api_id}.xml")
        
        elif response.status_code == 404:
            print(f"⚠️ API '{api_id}' no tiene política personalizada aún. Creando plantilla base...")
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(plantilla_base)
        else:
            # 3. Falla el job ante cualquier otro error HTTP
            print(f"❌ Error al respaldar '{api_id}'. HTTP {response.status_code}. Abortando.")
            sys.exit(1)

if __name__ == "__main__":
    main()
