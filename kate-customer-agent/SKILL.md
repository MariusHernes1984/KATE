---
name: kate-customer-agent
description: Create a new KATE customer agent in Azure AI Foundry for Atea's key accounts. Use this skill whenever the user wants to create, build, set up, or deploy a new customer agent in KATE, Foundry, or mentions onboarding a new customer to the KATE platform. Also trigger when the user mentions building a knowledge base from SharePoint documents for a customer agent, or asks to set up a new kundeagent.
---

# KATE Customer Agent Creator

You are helping create a new customer agent for the KATE platform (Key Account Team Executor) at Atea AS. Every customer agent follows the Komplett-mønsteret — the gold standard for KATE agents.

## Referansedokument

**LES ALLTID FØRST:**
`C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\KATE_AGENT_STANDARD.md`

Dette dokumentet inneholder komplett mal, arkitektur, kodeeksempler og sjekkliste. Følg det slavisk.

## Oversikt

KATE er Ateas AI multi-agent-plattform. Orkestratoren lever i Copilot Studio, og hver kundeagent bygges i Azure AI Foundry. Hver agent:

- Har en instruksjonsfil (`{agent}_instructions.txt`) med alle kundedata
- Har innbakte dokumentsammendrag fra SharePoint-dokumenter (HURTIGREFERANSE)
- Bruker 3-lags søkestrategi: Azure AI Search → SharePoint Grounding → Dokumentsammendrag
- Har et oppdateringsscript (`{agent}_update_agent.py`) som pusher til Foundry
- Har et 3-tier evalueringsrammeverk (33 spørsmål)
- Genererer PDF evalueringsrapport

## Azure-miljø

| Ressurs | Verdi |
|---------|-------|
| Subscription | `59aae656-c78b-4bc5-bcfd-e31748e6f6e2` |
| Resource Group | `RG-KATE` |
| Foundry Resource | `kateecosystem-resource` (Sweden Central) |
| Project | `kateecosystem` |
| Endpoint | `https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem` |
| Model | `gpt-5.3-chat` |
| Python venv | `/tmp/stafenv/Scripts/python.exe` |
| Base path | `C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE` |

## Nødvendig informasjon fra bruker

Før du starter, trenger du:

1. **Kundenavn** (fullt navn, f.eks. "Norsk Medisinaldepot")
2. **Kundealias** (kort kode, f.eks. "NMD")
3. **Lokal SharePoint-mappesti** — synkronisert mappe under `C:\Users\marherne\Atea\...` eller `C:\Users\marherne\OneDrive - Atea\...`
4. **SharePoint site URL** (f.eks. `https://atea.sharepoint.com/sites/...`)
5. **SharePoint connection name** for Foundry (f.eks. "STAF", "BOS", "Komplett")

Hvis brukeren ikke har oppgitt alt, spør etter det manglende.

## Steg-for-steg prosess

### Steg 1: Les standarden

Les `KATE_AGENT_STANDARD.md` for å forstå malen og arkitekturen.

Les også referanseagenter for nivå av detalj:
- STAF: `staf_instructions.txt` + `staf_update_agent.py`
- Komplett: Se Komplett-filene i prosjektmappen

### Steg 2: Analyser kundens SharePoint-dokumenter

Brukeren peker deg til en lokal synkronisert SharePoint-mappe. Systematisk gjennomgang:

1. **Kartlegg mappestruktur** — list alle mapper og undermapper
2. **Les nøkkeldokumenter** — prioriter i denne rekkefølgen:
   - Avtaler/kontrakter (verdier, datoer, parter)
   - Møtereferater (beslutninger, aksjoner, deltakere)
   - Tilbud/proposals (priser, scope, leveranser)
   - Strategidokumenter (mål, KPIer, tidslinjer)
   - Økonomidata (omsetning, faktura, trender)
   - Prosjektdokumenter (tidslinjer, eiere, status)
   - Sikkerhet/compliance (funn, anbefalinger)
3. **Ekstraher kritisk informasjon** til instruksjonene:
   - Nøkkelkontakter hos kunden (navn, roller, telefon, e-post)
   - Atea-team for kontoen (KAM, CM, OM, spesialister)
   - Aktive avtaler (nummer, type, datoer, verdi, omfang)
   - Økonomi (omsetning per kategori, trender, prognoser)
   - Pågående prosjekter og initiativer
   - Hardware livssyklus-datoer
   - Strategiske prioriteringer

### Steg 3: Bygg dokumentsammendrag (KRITISK)

**Dette er det som skiller Komplett-mønsteret fra gammel tilnærming.**

For hvert nøkkeldokument, lag et sammendrag med:
- **Tittel og dato** (f.eks. "COPILOT TILBUD FASE 1 (15. januar 2024):")
- **Nøkkelfakta** som bullet points: tall, navn, beslutninger, aksjoner, beløp
- **Spesifikke detaljer** som agenten trenger for å svare presist

Plasser alle sammendrag i seksjonen `--- DOKUMENTSAMMENDRAG (HURTIGREFERANSE) ---` FØR søkestrategien.

Mål: minimum 5-8 dokumentsammendrag per agent.

### Steg 4: Opprett instruksjonsfil

Opprett `{agent}_instructions.txt` i base path. Følg malen fra `KATE_AGENT_STANDARD.md` med alle 16 seksjoner i riktig rekkefølge:

1. Rolledefinisjon
2. Latency budget
3. Tekniske regler
4. SØKEREGLER
5. KUNDEINFORMASJON
6. NØKKELKONTAKTER HOS KUNDE
7. ATEA KUNDETEAM
8. AKTIVE RAMMEAVTALER
9. ØKONOMI OG OMSETNING
10. HARDWARE LIVSSYKLUS
11. PÅGÅENDE INITIATIVER
12. VIRKSOMHETSSTRATEGI
13. TILDELINGSBREV/STYRINGSPARAMETERE (offentlig sektor)
14. TOPP KONSULENTER
15. **DOKUMENTSAMMENDRAG (HURTIGREFERANSE)** ← Komplett-mønsteret
16. SHAREPOINT MAPPESTRUKTUR
17. SØKESTRATEGI OG VERKTØYBRUK (3-lags)

### Steg 5: Opprett oppdateringsscript

Opprett `{agent}_update_agent.py`:

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, SharepointPreviewTool, SharepointGroundingToolParameters
from azure.identity import DefaultAzureCredential
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INSTRUCTIONS_FILE = r'C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\{agent}_instructions.txt'

with open(INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
    instructions = f.read()

print(f"Instructions length: {len(instructions)} chars")

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)

CONNECTION_ID = "/subscriptions/59aae656-c78b-4bc5-bcfd-e31748e6f6e2/resourceGroups/RG-KATE/providers/Microsoft.CognitiveServices/accounts/kateecosystem-resource/projects/kateecosystem/connections/{CONNECTION_NAME}"

tool = SharepointPreviewTool(
    sharepoint_grounding_preview=SharepointGroundingToolParameters(
        project_connections=[{"project_connection_id": CONNECTION_ID}]
    )
)

agent = client.agents.create_version(
    agent_name="{AGENT_NAME}",
    definition=PromptAgentDefinition(
        model="gpt-5.3-chat",
        instructions=instructions,
        tools=[tool],
    )
)
print(f"Agent updated successfully!")
print(f"Name: {agent.name}")
print(f"ID: {agent.id}")
```

Kjør med: `PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {agent}_update_agent.py`

### Steg 6: Push agent til Azure

Kjør oppdateringsscriptet og verifiser at agenten opprettes. Forventet output:
```
Instructions length: XXXXX chars
Agent updated successfully!
Name: {AgentName}
ID: {AgentName}:{version}
```

(Ignorer eventuell `AttributeError: 'AgentVersionDetails' object has no attribute 'model'` — dette er harmløst.)

### Steg 7: Kjør 3-tier evaluering

Etter deployment, kjør `agent-eval` skillen for å verifisere agenten. Se `agent-eval/SKILL.md` for detaljer.

## Sjekkliste

```
- [ ] SharePoint-tilkobling opprettet i Azure AI Foundry portal
- [ ] (Valgfritt) Azure AI Search indeks opprettet
- [ ] OneDrive-dokumenter synkronisert lokalt
- [ ] Nøkkeldokumenter lest og oppsummert (minst 5-8 dokumenter)
- [ ] Instruksjonsfil opprettet med alle seksjoner
- [ ] Oppdateringsscript opprettet
- [ ] Agent pushet til Azure (create_version)
- [ ] Tier 1 evaluering kjørt (15 spm)
- [ ] Tier 2 evaluering kjørt (10 spm)
- [ ] Tier 3 evaluering kjørt (8 spm)
- [ ] Kombinert PDF-rapport generert
- [ ] Agent-versjon dokumentert
```

## Viktige regler

- Instruksjoner skrives på engelsk med norske domene-termer (som BOS/STAF/Komplett)
- Metadata-seksjonene er hurtigreferanse — agenten skal ALLTID søke SharePoint for detaljerte spørsmål
- All informasjon i instruksjonene MÅ komme fra faktiske dokumenter — aldri fabrikér data
- Dokumentsammendraget er den viktigste forbedringen — det gir agenten en fallback når søkeverktøy feiler
- Temperature: alltid 0 for deterministiske svar
