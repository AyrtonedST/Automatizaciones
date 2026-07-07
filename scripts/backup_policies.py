import os
import sys
import requests
import subprocess
import csv
import json

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
    # Agregamos 'Accept' explícito para forzar a Azure a comportarse
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json",
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

    hubo_errores = False
    print(f"--- Iniciando BACKUP para: {producto_objetivo} ---")
    
    for row in filas_a_procesar:
        api_id = row.get('API', '').strip()
        if not api_id:
            continue
            
        policy_url = f"{base_url_azure}/{api_id}/policies/policy?api-version=2022-08-01"
        response = requests.get(policy_url, headers=headers)
        
        if response.status_code == 200:
            texto_limpio = response.content.decode('utf-8-sig').strip()
            policy_xml = ""
            
            if not texto_limpio:
                print(f"⚠️ La respuesta de '{api_id}' llegó vacía. Usando plantilla base...")
                policy_xml = plantilla_base
            elif texto_limpio.startswith("<"):
                print(f"⚠️ Azure devolvió XML crudo para '{api_id}'. Procesando directamente...")
                policy_xml = texto_limpio
            else:
                try:
                    datos_json = json.loads(texto_limpio)
                    policy_xml = datos_json.get("properties", {}).get("value", "")
                    if not policy_xml:
                        policy_xml = plantilla_base
                except json.JSONDecodeError:
                    print(f"❌ Error al interpretar JSON de '{api_id}'. Data recibida: {texto_limpio[:100]}")
                    hubo_errores = True
                    continue
            
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(policy_xml)
            print(f"✅ Backup guardado: {api_id}.xml")
        
        elif response.status_code == 404:
            print(f"⚠️ API '{api_id}' no tiene política personalizada aún. Creando plantilla base...")
            with open(f"backups/{api_id}.xml", "w", encoding="utf-8") as f:
                f.write(plantilla_base)
        else:
            print(f"❌ Error al respaldar '{api_id}'. HTTP {response.status_code}")
            hubo_errores = True

    if hubo_errores:
        print("\n⚠️ Advertencia: Algunas APIs fallaron durante el backup.")

if __name__ == "__main__":
    main()
