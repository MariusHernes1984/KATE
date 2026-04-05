"""
Setup Azure AI Search index for Komplett Services AS.

Forutsetninger:
1. Azure AI Search service er oppgradert til Basic tier eller høyere
2. En Azure AD-app er registrert med Sites.Read.All permission
3. Miljøvariabler er satt (se nedenfor)

Bruk:
  python setup_ai_search_index.py --check          # Sjekk status
  python setup_ai_search_index.py --create-index    # Opprett indeks
  python setup_ai_search_index.py --create-indexer   # Opprett datasource + indexer
  python setup_ai_search_index.py --run              # Kjør indeksering
  python setup_ai_search_index.py --status           # Sjekk indekseringsstatus
  python setup_ai_search_index.py --upgrade-tier     # Oppgrader fra free til basic
"""

import argparse, json, os, sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

# Konfigurasjon
SEARCH_SERVICE = "kateaisearch"
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"
INDEX_NAME = "komplett-sharepoint-index"
DATASOURCE_NAME = "komplett-sharepoint-ds"
INDEXER_NAME = "komplett-sharepoint-indexer"
API_VERSION = "2024-11-01-preview"
RESOURCE_GROUP = "RG-KATE"
SUBSCRIPTION_ID = "3cd0c357-e545-49de-bcbb-f0fc1a61c5af"

# SharePoint-konfigurasjon
SHAREPOINT_SITE = "https://atea.sharepoint.com/sites/AteaRegionSrProspekts"
SHAREPOINT_LIBRARY = "Shared Documents/Komplett Services AS - AM Jørn Are Olsen"


def get_admin_key():
    """Hent admin key for Azure AI Search."""
    from azure.identity import DefaultAzureCredential
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default")

    url = (f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
           f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Search"
           f"/searchServices/{SEARCH_SERVICE}/listAdminKeys?api-version=2023-11-01")

    resp = requests.post(url, headers={"Authorization": f"Bearer {token.token}"})
    resp.raise_for_status()
    return resp.json()["primaryAdminKey"]


def get_headers():
    key = get_admin_key()
    return {
        "Content-Type": "application/json",
        "api-key": key,
    }


def check_status():
    """Sjekk søketjeneste og eksisterende indekser."""
    headers = get_headers()

    # Sjekk indekser
    resp = requests.get(f"{SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}", headers=headers)
    indexes = resp.json().get("value", [])
    print(f"Søketjeneste: {SEARCH_SERVICE}")
    print(f"Antall indekser: {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx['name']} ({idx.get('fields', []).__len__()} felt)")

    # Sjekk datasources
    resp = requests.get(f"{SEARCH_ENDPOINT}/datasources?api-version={API_VERSION}", headers=headers)
    datasources = resp.json().get("value", [])
    print(f"Antall datakilder: {len(datasources)}")
    for ds in datasources:
        print(f"  - {ds['name']} (type: {ds['type']})")

    # Sjekk indexers
    resp = requests.get(f"{SEARCH_ENDPOINT}/indexers?api-version={API_VERSION}", headers=headers)
    indexers = resp.json().get("value", [])
    print(f"Antall indexere: {len(indexers)}")
    for ix in indexers:
        print(f"  - {ix['name']} (target: {ix.get('targetIndexName', '?')})")


def create_index():
    """Opprett søkeindeks for Komplett-dokumenter."""
    headers = get_headers()

    index_def = {
        "name": INDEX_NAME,
        "fields": [
            {"name": "metadata_spo_site_library_item_id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "metadata_spo_item_name", "type": "Edm.String", "searchable": True, "filterable": True, "retrievable": True},
            {"name": "metadata_spo_item_path", "type": "Edm.String", "searchable": False, "filterable": True, "retrievable": True},
            {"name": "metadata_spo_item_content_type", "type": "Edm.String", "filterable": True, "retrievable": True},
            {"name": "metadata_spo_item_last_modified", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True, "retrievable": True},
            {"name": "metadata_spo_item_size", "type": "Edm.Int64", "filterable": True, "retrievable": True},
        ],
        "semantic": {
            "configurations": [
                {
                    "name": "komplett-semantic-config",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "metadata_spo_item_name"},
                        "contentFields": [{"fieldName": "content"}]
                    }
                }
            ]
        }
    }

    resp = requests.put(
        f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}?api-version={API_VERSION}",
        headers=headers,
        json=index_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Indeks '{INDEX_NAME}' opprettet/oppdatert!")
    else:
        print(f"❌ Feil ved oppretting av indeks: {resp.status_code}")
        print(resp.text)


def create_datasource_and_indexer():
    """Opprett SharePoint Online datakilde og indexer.

    Støtter to autentiseringsmodeller:
    1. Secretless (managed identity) — anbefalt med Sites.Selected
       Krever: SHAREPOINT_APP_CLIENT_ID, SHAREPOINT_TENANT_ID, SEARCH_MANAGED_IDENTITY_ID
    2. Client secret — fallback
       Krever: SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, SHAREPOINT_TENANT_ID
    """
    headers = get_headers()

    # Sjekk om vi bruker managed identity (secretless) eller client secret
    sp_app_id = os.getenv("SHAREPOINT_APP_CLIENT_ID", "") or os.getenv("SHAREPOINT_CLIENT_ID", "")
    sp_secret = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
    sp_tenant = os.getenv("SHAREPOINT_TENANT_ID", "")
    managed_identity_id = os.getenv("SEARCH_MANAGED_IDENTITY_ID", "")

    if not sp_app_id or not sp_tenant:
        print("Mangler miljovariabler:")
        print("  For secretless (anbefalt): SHAREPOINT_APP_CLIENT_ID, SHAREPOINT_TENANT_ID, SEARCH_MANAGED_IDENTITY_ID")
        print("  For client secret: SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, SHAREPOINT_TENANT_ID")
        return

    # Bygg connection string basert på autentiseringsmetode
    if managed_identity_id and not sp_secret:
        # Secretless med managed identity (Sites.Selected)
        connection_string = (
            f"SharePointOnlineEndpoint={SHAREPOINT_SITE};"
            f"ApplicationId={sp_app_id};"
            f"FederatedCredentialObjectId={managed_identity_id};"
            f"TenantId={sp_tenant}"
        )
        print(f"Bruker secretless autentisering (managed identity)")
    elif sp_secret:
        # Client secret
        connection_string = (
            f"SharePointOnlineEndpoint={SHAREPOINT_SITE};"
            f"ApplicationId={sp_app_id};"
            f"ApplicationSecret={sp_secret};"
            f"TenantId={sp_tenant}"
        )
        print(f"Bruker client secret autentisering")
    else:
        print("Mangler SEARCH_MANAGED_IDENTITY_ID eller SHAREPOINT_CLIENT_SECRET")
        return

    # Opprett datakilde
    datasource_def = {
        "name": DATASOURCE_NAME,
        "type": "sharepoint",
        "credentials": {
            "connectionString": connection_string
        },
        "container": {
            "name": "useQuery",
            "query": f"includeLibrariesList={SHAREPOINT_LIBRARY}"
        }
    }

    resp = requests.put(
        f"{SEARCH_ENDPOINT}/datasources/{DATASOURCE_NAME}?api-version={API_VERSION}",
        headers=headers,
        json=datasource_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Datakilde '{DATASOURCE_NAME}' opprettet!")
    else:
        print(f"❌ Feil ved oppretting av datakilde: {resp.status_code}")
        print(resp.text)
        return

    # Opprett indexer
    indexer_def = {
        "name": INDEXER_NAME,
        "dataSourceName": DATASOURCE_NAME,
        "targetIndexName": INDEX_NAME,
        "parameters": {
            "configuration": {
                "indexedFileNameExtensions": ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.msg,.txt,.csv,.html"
            }
        },
        "schedule": {
            "interval": "PT4H"
        }
    }

    resp = requests.put(
        f"{SEARCH_ENDPOINT}/indexers/{INDEXER_NAME}?api-version={API_VERSION}",
        headers=headers,
        json=indexer_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Indexer '{INDEXER_NAME}' opprettet! Kjører hver 4. time.")
    else:
        print(f"❌ Feil ved oppretting av indexer: {resp.status_code}")
        print(resp.text)


def run_indexer():
    """Kjør indeksering manuelt."""
    headers = get_headers()
    resp = requests.post(
        f"{SEARCH_ENDPOINT}/indexers/{INDEXER_NAME}/run?api-version={API_VERSION}",
        headers=headers
    )
    if resp.status_code == 202:
        print(f"✅ Indeksering startet for '{INDEXER_NAME}'!")
    else:
        print(f"❌ Feil: {resp.status_code} - {resp.text}")


def indexer_status():
    """Sjekk indekseringsstatus."""
    headers = get_headers()
    resp = requests.get(
        f"{SEARCH_ENDPOINT}/indexers/{INDEXER_NAME}/status?api-version={API_VERSION}",
        headers=headers
    )
    if resp.status_code == 200:
        status = resp.json()
        last = status.get("lastResult", {})
        print(f"Indexer: {INDEXER_NAME}")
        print(f"  Status: {status.get('status', '?')}")
        print(f"  Siste kjøring: {last.get('startTime', '?')}")
        print(f"  Resultat: {last.get('status', '?')}")
        print(f"  Dokumenter behandlet: {last.get('itemCount', 0)}")
        print(f"  Feil: {last.get('failedItemCount', 0)}")
    else:
        print(f"❌ Feil: {resp.status_code} - {resp.text}")


def upgrade_tier():
    """Oppgrader Azure AI Search fra free til basic."""
    print("⚠️  Oppgradering fra free til basic krever at eksisterende tjeneste slettes og opprettes på nytt.")
    print("   Azure AI Search støtter IKKE in-place tier-endring.")
    print()
    print("Alternativ: Opprett en ny Basic-tier søketjeneste:")
    print()
    print(f"  az search service create \\")
    print(f"    --name kateaisearch-basic \\")
    print(f"    --resource-group {RESOURCE_GROUP} \\")
    print(f"    --sku basic \\")
    print(f"    --location norwayeast \\")
    print(f"    --replica-count 1 \\")
    print(f"    --partition-count 1")
    print()
    print("Deretter:")
    print("  1. Oppdater Foundry-connection til ny søketjeneste")
    print("  2. Kjør dette scriptet med --create-index --create-indexer --run")
    print("  3. Oppdater SEARCH_SERVICE variabelen i dette scriptet")
    print()

    confirm = input("Vil du opprette ny Basic-tier tjeneste nå? (ja/nei): ")
    if confirm.lower() == "ja":
        import subprocess
        result = subprocess.run([
            "az", "search", "service", "create",
            "--name", "kateaisearch-basic",
            "--resource-group", RESOURCE_GROUP,
            "--sku", "basic",
            "--location", "norwayeast",
            "--replica-count", "1",
            "--partition-count", "1"
        ], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"❌ {result.stderr}")
        else:
            print("✅ Ny Basic-tier søketjeneste opprettet!")
            print("   Oppdater SEARCH_SERVICE i dette scriptet til 'kateaisearch-basic'")
    else:
        print("Avbrutt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Azure AI Search for Komplett")
    parser.add_argument("--check", action="store_true", help="Sjekk status")
    parser.add_argument("--create-index", action="store_true", help="Opprett indeks")
    parser.add_argument("--create-indexer", action="store_true", help="Opprett datasource + indexer")
    parser.add_argument("--run", action="store_true", help="Kjør indeksering")
    parser.add_argument("--status", action="store_true", help="Sjekk indekseringsstatus")
    parser.add_argument("--upgrade-tier", action="store_true", help="Oppgrader til Basic tier")
    args = parser.parse_args()

    if args.check:
        check_status()
    elif args.create_index:
        create_index()
    elif args.create_indexer:
        create_datasource_and_indexer()
    elif args.run:
        run_indexer()
    elif args.status:
        indexer_status()
    elif args.upgrade_tier:
        upgrade_tier()
    else:
        parser.print_help()
