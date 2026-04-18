"""
Setup Azure AI Search index for a KATE customer agent.

Reads customer config from `agenter/{alias}.json` (fields: kunde.sharepoint_site,
kunde.sharepoint_hovedmappe). CLI flags may override.

Forutsetninger:
1. Azure AI Search service er oppgradert til Basic tier eller høyere
2. En Azure AD-app er registrert med Sites.Read.All permission
3. Miljøvariabler er satt (se nedenfor)

Bruk:
  python setup_ai_search_index.py --alias komplett --check
  python setup_ai_search_index.py --alias komplett --create-index
  python setup_ai_search_index.py --alias komplett --create-indexer
  python setup_ai_search_index.py --alias komplett --run
  python setup_ai_search_index.py --alias komplett --status
  python setup_ai_search_index.py --upgrade-tier
"""

import argparse, json, os, sys, io, urllib.parse, requests
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

# Søketjeneste-konstanter (felles for alle kunder)
SEARCH_SERVICE = "kateaisearch-basic"
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"
API_VERSION = "2024-11-01-preview"
RESOURCE_GROUP = "RG-KATE"
SUBSCRIPTION_ID = "59aae656-c78b-4bc5-bcfd-e31748e6f6e2"

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTER_DIR = REPO_ROOT / "agenter"


class CustomerConfig:
    """Per-kunde konfigurasjon lest fra agenter/{alias}.json med CLI-overrides."""

    def __init__(self, alias: str, site_url: str | None = None, library: str | None = None):
        self.alias = alias.lower()
        self.index_name = f"{self.alias}-sharepoint-index"
        self.datasource_name = f"{self.alias}-sharepoint-ds"
        self.indexer_name = f"{self.alias}-sharepoint-indexer"
        self.semantic_config = f"{self.alias}-semantic-config"

        cfg_path = AGENTER_DIR / f"{self.alias}.json"
        cfg = {}
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        kunde = cfg.get("kunde", {})

        self.site_url = site_url or kunde.get("sharepoint_site", "")
        self.library = library or self._derive_library(self.site_url, kunde.get("sharepoint_hovedmappe", ""))

        if not self.site_url:
            raise ValueError(f"Mangler sharepoint_site for alias '{self.alias}'. Legg til i agenter/{self.alias}.json eller bruk --site-url.")

    @staticmethod
    def _derive_library(site_url: str, hovedmappe_url: str) -> str:
        """Trekker ut library-stien ('Shared Documents/Kundenavn') fra hovedmappe-URL."""
        if not hovedmappe_url or not site_url:
            return ""
        if hovedmappe_url.startswith(site_url):
            rel = hovedmappe_url[len(site_url):].lstrip("/")
            return urllib.parse.unquote(rel)
        return urllib.parse.unquote(hovedmappe_url)


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
    return resp.json()["primaryKey"]


def get_headers():
    key = get_admin_key()
    return {
        "Content-Type": "application/json",
        "api-key": key,
    }


def check_status(cfg: CustomerConfig | None = None):
    """Sjekk søketjeneste og eksisterende indekser."""
    headers = get_headers()

    resp = requests.get(f"{SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}", headers=headers)
    indexes = resp.json().get("value", [])
    print(f"Søketjeneste: {SEARCH_SERVICE}")
    print(f"Antall indekser: {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx['name']} ({idx.get('fields', []).__len__()} felt)")

    resp = requests.get(f"{SEARCH_ENDPOINT}/datasources?api-version={API_VERSION}", headers=headers)
    datasources = resp.json().get("value", [])
    print(f"Antall datakilder: {len(datasources)}")
    for ds in datasources:
        print(f"  - {ds['name']} (type: {ds['type']})")

    resp = requests.get(f"{SEARCH_ENDPOINT}/indexers?api-version={API_VERSION}", headers=headers)
    indexers = resp.json().get("value", [])
    print(f"Antall indexere: {len(indexers)}")
    for ix in indexers:
        print(f"  - {ix['name']} (target: {ix.get('targetIndexName', '?')})")


def index_exists(cfg: CustomerConfig) -> bool:
    """Returner True hvis indeks allerede finnes."""
    headers = get_headers()
    resp = requests.get(
        f"{SEARCH_ENDPOINT}/indexes/{cfg.index_name}?api-version={API_VERSION}",
        headers=headers,
    )
    return resp.status_code == 200


def create_index(cfg: CustomerConfig):
    """Opprett søkeindeks for kundens dokumenter."""
    headers = get_headers()

    index_def = {
        "name": cfg.index_name,
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
                    "name": cfg.semantic_config,
                    "prioritizedFields": {
                        "titleField": {"fieldName": "metadata_spo_item_name"},
                        "contentFields": [{"fieldName": "content"}]
                    }
                }
            ]
        }
    }

    resp = requests.put(
        f"{SEARCH_ENDPOINT}/indexes/{cfg.index_name}?api-version={API_VERSION}",
        headers=headers,
        json=index_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Indeks '{cfg.index_name}' opprettet/oppdatert!")
    else:
        print(f"❌ Feil ved oppretting av indeks: {resp.status_code}")
        print(resp.text)


def create_datasource_and_indexer(cfg: CustomerConfig):
    """Opprett SharePoint Online datakilde og indexer.

    Støtter to autentiseringsmodeller:
    1. Secretless (managed identity) — anbefalt med Sites.Selected
       Krever: SHAREPOINT_APP_CLIENT_ID, SHAREPOINT_TENANT_ID, SEARCH_MANAGED_IDENTITY_ID
    2. Client secret — fallback
       Krever: SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, SHAREPOINT_TENANT_ID
    """
    if not cfg.library:
        print(f"❌ Mangler SharePoint library for '{cfg.alias}'. Sett kunde.sharepoint_hovedmappe i agenter/{cfg.alias}.json eller bruk --library.")
        return

    headers = get_headers()

    sp_app_id = os.getenv("SHAREPOINT_APP_CLIENT_ID", "") or os.getenv("SHAREPOINT_CLIENT_ID", "")
    sp_secret = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
    sp_tenant = os.getenv("SHAREPOINT_TENANT_ID", "")
    managed_identity_id = os.getenv("SEARCH_MANAGED_IDENTITY_ID", "")

    if not sp_app_id or not sp_tenant:
        print("Mangler miljovariabler:")
        print("  For secretless (anbefalt): SHAREPOINT_APP_CLIENT_ID, SHAREPOINT_TENANT_ID, SEARCH_MANAGED_IDENTITY_ID")
        print("  For client secret: SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET, SHAREPOINT_TENANT_ID")
        return

    if managed_identity_id and not sp_secret:
        connection_string = (
            f"SharePointOnlineEndpoint={cfg.site_url};"
            f"ApplicationId={sp_app_id};"
            f"FederatedCredentialObjectId={managed_identity_id};"
            f"TenantId={sp_tenant}"
        )
        print(f"Bruker secretless autentisering (managed identity)")
    elif sp_secret:
        connection_string = (
            f"SharePointOnlineEndpoint={cfg.site_url};"
            f"ApplicationId={sp_app_id};"
            f"ApplicationSecret={sp_secret};"
            f"TenantId={sp_tenant}"
        )
        print(f"Bruker client secret autentisering")
    else:
        print("Mangler SEARCH_MANAGED_IDENTITY_ID eller SHAREPOINT_CLIENT_SECRET")
        return

    datasource_def = {
        "name": cfg.datasource_name,
        "type": "sharepoint",
        "credentials": {
            "connectionString": connection_string
        },
        "container": {
            "name": "useQuery",
            "query": f"includeLibrariesList={cfg.library}"
        }
    }

    resp = requests.put(
        f"{SEARCH_ENDPOINT}/datasources/{cfg.datasource_name}?api-version={API_VERSION}",
        headers=headers,
        json=datasource_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Datakilde '{cfg.datasource_name}' opprettet!")
    else:
        print(f"❌ Feil ved oppretting av datakilde: {resp.status_code}")
        print(resp.text)
        return

    indexer_def = {
        "name": cfg.indexer_name,
        "dataSourceName": cfg.datasource_name,
        "targetIndexName": cfg.index_name,
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
        f"{SEARCH_ENDPOINT}/indexers/{cfg.indexer_name}?api-version={API_VERSION}",
        headers=headers,
        json=indexer_def
    )

    if resp.status_code in (200, 201):
        print(f"✅ Indexer '{cfg.indexer_name}' opprettet! Kjører hver 4. time.")
    else:
        print(f"❌ Feil ved oppretting av indexer: {resp.status_code}")
        print(resp.text)


def run_indexer(cfg: CustomerConfig):
    """Kjør indeksering manuelt."""
    headers = get_headers()
    resp = requests.post(
        f"{SEARCH_ENDPOINT}/indexers/{cfg.indexer_name}/run?api-version={API_VERSION}",
        headers=headers
    )
    if resp.status_code == 202:
        print(f"✅ Indeksering startet for '{cfg.indexer_name}'!")
    else:
        print(f"❌ Feil: {resp.status_code} - {resp.text}")


def indexer_status(cfg: CustomerConfig):
    """Sjekk indekseringsstatus."""
    headers = get_headers()
    resp = requests.get(
        f"{SEARCH_ENDPOINT}/indexers/{cfg.indexer_name}/status?api-version={API_VERSION}",
        headers=headers
    )
    if resp.status_code == 200:
        status = resp.json()
        last = status.get("lastResult", {})
        print(f"Indexer: {cfg.indexer_name}")
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
    parser = argparse.ArgumentParser(description="Setup Azure AI Search for en KATE kundeagent")
    parser.add_argument("--alias", help="Kunde-alias (matcher agenter/{alias}.json)")
    parser.add_argument("--site-url", help="SharePoint site-URL (overstyrer config)")
    parser.add_argument("--library", help="SharePoint library-sti (overstyrer config)")
    parser.add_argument("--check", action="store_true", help="Sjekk status for alle indekser")
    parser.add_argument("--create-index", action="store_true", help="Opprett indeks")
    parser.add_argument("--create-indexer", action="store_true", help="Opprett datasource + indexer")
    parser.add_argument("--run", action="store_true", help="Kjør indeksering")
    parser.add_argument("--status", action="store_true", help="Sjekk indekseringsstatus")
    parser.add_argument("--upgrade-tier", action="store_true", help="Oppgrader til Basic tier")
    args = parser.parse_args()

    # --check (uten alias) og --upgrade-tier trenger ikke kundekontekst
    if args.upgrade_tier:
        upgrade_tier()
    elif args.check and not args.alias:
        check_status()
    else:
        if not args.alias:
            parser.error("--alias er påkrevd (unntatt for --check uten alias og --upgrade-tier)")
        cfg = CustomerConfig(args.alias, site_url=args.site_url, library=args.library)

        if args.check:
            check_status(cfg)
        elif args.create_index:
            create_index(cfg)
        elif args.create_indexer:
            create_datasource_and_indexer(cfg)
        elif args.run:
            run_indexer(cfg)
        elif args.status:
            indexer_status(cfg)
        else:
            parser.print_help()
