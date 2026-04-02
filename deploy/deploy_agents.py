"""
Deploy KATE kundeagenter til Azure AI Foundry.

Hver kundeagent er en dedikert Foundry-agent med Azure AI Search
koblet til kundens SharePoint Online-mappe.

Bruk:
  1. Kopier .env.example til .env og fyll inn verdier
  2. pip install -r requirements.txt
  3. az login
  4. python deploy_agents.py
  5. python deploy_agents.py --only bertel-o-steen  (deploy kun en agent)
  6. python deploy_agents.py --list                  (vis alle agenter)
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    SharepointPreviewTool,
    SharepointGroundingToolParameters,
    ToolProjectConnection,
)

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL = os.environ.get("MODEL_DEPLOYMENT", "gpt-4o")
SEARCH_CONNECTION_NAME = os.environ.get("SEARCH_CONNECTION_NAME", "")

AGENTER_DIR = Path(__file__).parent.parent / "agenter"
DEPLOY_DIR = Path(__file__).parent


def load_kundeagenter() -> dict[str, dict]:
    """Last alle kundeagent-konfigurasjoner fra agenter/-mappen."""
    agenter = {}
    skip_files = {"governance.json", "kundeagent-mal.json", "bos-dokumentkatalog.json"}

    for filepath in AGENTER_DIR.glob("*.json"):
        if filepath.name in skip_files:
            continue

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        agent_name = filepath.stem  # f.eks. "bertel-o-steen"
        agenter[agent_name] = data

    return agenter


def build_search_tool(client: AIProjectClient, index_name: str) -> AzureAISearchTool:
    """Opprett en AzureAISearchTool for kundens SharePoint-indeks."""
    connection_name = SEARCH_CONNECTION_NAME
    connection = client.connections.get(connection_name)

    return AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[
                AISearchIndexResource(
                    project_connection_id=connection.id,
                    index_name=index_name,
                    query_type=AzureAISearchQueryType.SEMANTIC,
                    top_k=10,
                ),
            ]
        )
    )


def build_sharepoint_tool(client: AIProjectClient, connection_name: str) -> SharepointPreviewTool:
    """Opprett en SharepointPreviewTool for direkte SharePoint-tilgang."""
    connection = client.connections.get(connection_name)

    return SharepointPreviewTool(
        sharepoint_grounding_preview=SharepointGroundingToolParameters(
            project_connections=[
                ToolProjectConnection(project_connection_id=connection.id)
            ]
        )
    )


def deploy_agent(client: AIProjectClient, agent_name: str, config: dict) -> dict:
    """Opprett en kundeagent i Azure AI Foundry."""
    tools = []

    # Legg til SharePoint Grounding Preview for direkte dokumenttilgang
    sp_config = config.get("tools", {}).get("sharepoint_grounding", {})
    sp_connection = sp_config.get("connection_name")
    if sp_connection:
        tools.append(build_sharepoint_tool(client, sp_connection))

    # Legg til Azure AI Search for kundens dokumenter (alternativ)
    search_config = config.get("tools", {}).get("azure_ai_search", {})
    index_name = search_config.get("index_name")
    if index_name:
        tools.append(build_search_tool(client, index_name))

    model = config.get("model", {}).get("deployment", MODEL)

    agent = client.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=model,
            instructions=config["instructions"],
            tools=tools,
        ),
    )

    result = {
        "name": agent.name,
        "id": agent.id,
        "version": agent.version,
        "kunde": config.get("kunde", {}).get("navn", ""),
    }
    print(f"  OK: {agent_name} (id: {agent.id}, versjon: {agent.version})")
    return result


def main():
    # Parse argumenter
    if "--list" in sys.argv:
        agenter = load_kundeagenter()
        print(f"Tilgjengelige kundeagenter ({len(agenter)}):\n")
        for name, config in sorted(agenter.items()):
            kunde = config.get("kunde", {})
            print(f"  {name}")
            print(f"    Kunde: {kunde.get('navn', '?')}")
            print(f"    Alias: {kunde.get('alias', '?')}")
            print(f"    SuperOffice ID: {kunde.get('superoffice_id', '?')}")
            print()
        return

    only_agent = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only_agent = sys.argv[idx + 1]

    print(f"Kobler til Azure AI Foundry: {PROJECT_ENDPOINT}")
    print(f"Modell: {MODEL}\n")

    client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    agenter = load_kundeagenter()

    if only_agent:
        if only_agent not in agenter:
            print(f"FEIL: Ukjent agent '{only_agent}'")
            print(f"Tilgjengelige: {', '.join(sorted(agenter.keys()))}")
            sys.exit(1)
        agenter = {only_agent: agenter[only_agent]}

    print(f"Deployer {len(agenter)} kundeagent(er)...\n")

    results = {}
    for agent_name, config in agenter.items():
        results[agent_name] = deploy_agent(client, agent_name, config)

    print("\n--- Deployment fullført ---\n")

    # Lagre resultater
    output_file = DEPLOY_DIR / "deployed_agents.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Agent-IDer lagret til: {output_file}")
    print(f"\nOpprettede agenter:")
    for name, info in results.items():
        print(f"  {name} ({info['kunde']}): {info['id']} (v{info['version']})")


if __name__ == "__main__":
    main()
