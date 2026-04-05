"""
Update BOS agent instructions in Azure AI Foundry with new document summaries.
Creates a new version with the updated instructions from our local JSON.
"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load updated instructions from JSON
with open(r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\agenter\bertel-o-steen.json", "r", encoding="utf-8") as f:
    config = json.load(f)

instructions = config["instructions"]
print(f"New instructions length: {len(instructions)} chars")

# Connect to Azure AI Foundry
client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.services.ai.azure.com/api/projects/kateecosystem',
)

# Get current agent version to preserve tools config
agent_name = "bertel-o-steen"
current_versions = list(client.agents.list_versions(agent_name))
latest = current_versions[0]
latest_dict = latest.as_dict() if hasattr(latest, 'as_dict') else dict(latest)
current_def = latest_dict.get('definition', {})
current_tools = current_def.get('tools', [])
current_model = current_def.get('model', 'gpt-5.3-chat')
current_version = latest_dict.get('version', '4')

print(f"Current version: {current_version}")
print(f"Current model: {current_model}")
print(f"Current tools: {json.dumps(current_tools, indent=2)}")
print(f"Current instructions length: {len(current_def.get('instructions', ''))}")

# Create new version with updated instructions
new_definition = {
    "kind": "prompt",
    "model": current_model,
    "instructions": instructions,
    "tools": current_tools,
}

print(f"\nCreating new version...")
new_version = client.agents.create_version(
    agent_name=agent_name,
    body={
        "definition": new_definition,
        "description": "v5: Added detailed document summaries (Komplett-mønsteret) for KPIer, BOS Log 12.12.2025, Møteplan 2026, and expanded Bærekraft details",
    }
)

new_dict = new_version.as_dict() if hasattr(new_version, 'as_dict') else dict(new_version)
print(f"New version created: {new_dict.get('version', '?')}")
print(f"New instructions length: {len(new_dict.get('definition', {}).get('instructions', ''))}")
print("Done!")
