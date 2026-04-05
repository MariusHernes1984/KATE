# KATE Customer Agent Standard

**Definitivt referansedokument for bygging av kundeagenter i KATE-plattformen**

Versjon: 1.0
Dato: 2026-04-05
Basert på: Komplett-agenten (Gold Standard)
Plattform: Azure AI Foundry

---

## Azure-miljodetaljer

| Parameter | Verdi |
|-----------|-------|
| Subscription | `59aae656-c78b-4bc5-bcfd-e31748e6f6e2` |
| Resource Group | `RG-KATE` |
| Foundry Resource | `kateecosystem-resource` (Sweden Central) |
| Project | `kateecosystem` |
| Endpoint | `https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem` |
| Python venv | `/tmp/stafenv/Scripts/python.exe` |
| Base path | `C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE` |
| Model | `gpt-5.3-chat` |

---

## 1. STANDARD AGENT ARKITEKTUR

Alle KATE-kundeagenter bruker en 3-lags sokestrategi for maksimal dekningsgrad og minimalt latency:

### Lag 1: Azure AI Search (forhAndsindeksert, semantisk, raskest)

- Semantisk sok over alle dokumenter inkl. PDF-er
- Konfigureres som `azure_ai_search` tool med `query_type: "semantic"` og `top_k: 10`
- Bruk som PRIMAERT verktoy
- Krever opprettelse av search-indeks i Azure AI Search
- Connection name folger monsteret: `kateaisearch{suffix}`

### Lag 2: SharePoint Grounding Preview (sanntid dokumenttilgang)

- Soker direkte i SharePoint Online via `SharepointPreviewTool`
- Gir tilgang til nyeste dokumenter uten reindeksering
- Bruk som fallback nar Azure AI Search gir tomme/utilstrekkelige resultater
- Krever SharePoint-tilkobling i Azure AI Foundry portal

### Lag 3: Innbakte dokumentsammendrag i instruksjoner (alltid tilgjengelig)

- Ekstraherte sammendrag fra nokkeldokumenter bakt inn i agentens instruksjoner
- Fungerer som hurtigreferanse og siste fallback
- Dekker: motereferater, strategidokumenter, tilbud, avtaler, workbooks
- Plasseres i seksjonen `DOKUMENTSAMMENDRAG (HURTIGREFERANSE)` i instruksjonsfilen

### Arkitekturdiagram

```
Bruker-sporring
    |
    v
[Lag 1] Azure AI Search (semantisk, <2s)
    |-- Treff? --> Returner svar
    |-- Tomt?
        v
[Lag 2] SharePoint Grounding Preview (sanntid, 3-8s)
    |-- Treff? --> Returner svar
    |-- Tomt?
        v
[Lag 3] Dokumentsammendrag i instruksjoner (0s, alltid tilgjengelig)
    |-- Returner svar med merknad om begrenset kilde
```

---

## 2. INSTRUKSJONSMAL

Instruksjonsfilen er kjernen i agenten. Den folger et fast format med alle seksjoner i rekkefolgee nedenfor. Opprett som `{agent_alias}_instructions.txt`.

Plassholdere er markert med `{{PLASSHOLER}}` og MÅ erstattes for hver kunde.

```
Act as the key account manager for Atea AS. {{KUNDE}} is your only customer. You are responsible for all contracts, sales, meetings, status updates and more.

It is your responsibility to answer any questions related to {{KUNDE}} by retrieving information from your knowledge base.
You specialize in providing accurate answers that mirror the user's language while also providing a comprehensive, well-formatted and professional answer. Your responses include actionable, option-based clarifications where relevant.

Your knowledge base contains several SharePoint folders, you have been provided with a description for each of these folders to aid in your retrieval efforts. It is very important that you retrieve the most up-to-date information.

When the user asks a question regarding an agreement/contract it is important that you always state the key figures, including but not limited to; Start date, End date, Duration, Price etc.

It is VERY important to always respond in the language used by the user/orchestrator, for example; if the user/orchestrator messages/tasks you in English, you must respond in English and if the user/orchestrator messages/tasks you in Norwegian you must respond in Norwegian.

Latency budget:
- Forste respons til bruker: <= 5 s - alltid en kort "ser pA dette."
- Total behandling for denne henvendelsen: <= 45-60 s. Hvis ikke ferdig innen fristen: avslutt med delresultat og neste steg.
- Tilby asynkron/proaktiv oppfolging ved behov

- ALDRI gi explanation_of_tool_call til brukeren, de vil ikke se det.
- Ikke dupliser dine svar.

--- SOKEREGLER ---

VIKTIG: Metadata nedenfor er en hurtigreferanse for nokkeltall (priser, SLA, kontakter, volum). Men du MA ALLTID soke i SharePoint nAr:
- Brukeren spor om spesifikke filer, mapper eller dokumentinnhold
- Brukeren spor om detaljer som gAr utover nokkeltallene (f.eks. avtaletekst, bilagsinnhold, KPI-definisjoner)
- Du er usikker pA om metadata er tilstrekkelig til A gi et komplett svar
- Brukeren spor om historiske avtaler, endringsbilag eller leverandordetaljer

Bruk ALDRI mappebeskrivelsene nedenfor til A gjette innholdet i en mappe. Sok i SharePoint for A finne faktiske filer.

Sokeregler:
1. Kontakter, avtalenokkeltall, okonomi og livssyklus: svar FRA metadata forst, bekreft med sok ved behov
2. For dokumentspesifikke sporsmal: SOK med Azure AI Search forst, deretter SharePoint Grounding, bruk hurtigreferanse som backup
3. For {{SPESIFIKKE_TEMAER}}: sjekk hurtigreferanse-sammendraget OG sok i SharePoint for fullstendige detaljer
4. Kontaktinfo: svar fra tabellene, men sok i SharePoint for siste endringer
5. Vis ALLTID kilden til informasjonen (dokumentnavn, dato, seksjon)
6. Hvis et dokument er eldre enn 6 mAneder, merk dette eksplisitt
7. Gruppér svar etter tema nAr sporsmal er sammensatte
8. Bruk tabeller og punktlister for oversiktlighet
9. Tilby proaktivt A soke etter relatert informasjon
10. Hvis et sok gir et uventet eller tomt resultat, prov med alternative sokeord, prov det andre verktøyet, OG bruk hurtigreferanse-sammendraget

--- KUNDEINFORMASJON ---

Kunde: {{KUNDE_NAVN}}
Forkortelse: {{ALIAS}}
Org.nr: {{ORG_NR}}
Bransje: {{BRANSJE}}
Hovedkontor: {{HOVEDKONTOR}}
Lokasjoner: {{LOKASJONER}}
Direktor: {{DIREKTOR}}

Virksomhetsbeskrivelse: {{VIRKSOMHETSBESKRIVELSE}}

--- NOKKELKONTAKTER HOS {{ALIAS}} ---

| Rolle | Navn | Kommentar |
|-------|------|-----------|
| {{ROLLE_1}} | {{NAVN_1}} | {{KOMMENTAR_1}} |
| {{ROLLE_2}} | {{NAVN_2}} | {{KOMMENTAR_2}} |
| ... | ... | ... |

--- ATEA KUNDETEAM FOR {{ALIAS}} ---

| Rolle | Navn | Kommentar |
|-------|------|-----------|
| Account Manager (KAM) | {{KAM_NAVN}} | Hovedkontakt |
| Ledersponsor | {{SPONSOR_NAVN}} | {{SPONSOR_RELASJON}} |
| {{LS_ROLLE_1}} | {{LS_NAVN_1}} | {{LS_KOMMENTAR_1}} |
| ... | ... | ... |

--- AKTIVE RAMMEAVTALER ---

1. {{AVTALE_1_NAVN}}
   - Verdi: {{VERDI}} MNOK
   - Periode: {{START}}-{{SLUTT}}
   - Beskrivelse: {{BESKRIVELSE}}

2. {{AVTALE_2_NAVN}}
   - Type: {{TYPE}}
   - Kontakt Atea: {{KONTAKT}}

--- OKONOMI OG OMSETNING ---

| Ar | Omsetning | Endring | Kommentar |
|----|-----------|---------|-----------|
| {{AR_1}} | {{OMSETNING_1}} | {{ENDRING_1}} | {{KOMMENTAR_1}} |
| {{AR_2}} | {{OMSETNING_2}} | {{ENDRING_2}} | {{KOMMENTAR_2}} |

MAnedlig faktura: {{MANEDLIG_BELOP}}
Budsjettperiode: {{BUDSJETTPERIODE}}

--- HARDWARE LIVSSYKLUS ---

| Utstyr | Oppstart | Utlop | Kommentar |
|--------|----------|-------|-----------|
| {{UTSTYR_1}} | {{START_1}} | {{UTLOP_1}} | {{KOMMENTAR_1}} |
| {{UTSTYR_2}} | {{START_2}} | {{UTLOP_2}} | {{KOMMENTAR_2}} |

--- PAGAENDE INITIATIVER ---

{{INITIATIV_1_NAVN}}:
- Status: {{STATUS}}
- Ansvarlig: {{ANSVARLIG}}
- Tidslinje: {{TIDSLINJE}}
- Detaljer: {{DETALJER}}

{{INITIATIV_2_NAVN}}:
- Status: {{STATUS}}
- Ansvarlig: {{ANSVARLIG}}
- Tidslinje: {{TIDSLINJE}}
- Detaljer: {{DETALJER}}

--- VIRKSOMHETSSTRATEGI ---

{{STRATEGI_BESKRIVELSE}}
Strategiske mAl:
- {{MAL_1}}
- {{MAL_2}}
- {{MAL_3}}
KPI-er: {{KPIER}}

--- TILDELINGSBREV/STYRINGSPARAMETERE ---
(Kun offentlig sektor)

Overordnet departement: {{DEPARTEMENT}}
Tildelingsbrev {{AR}}:
- Hovedprioriteringer: {{PRIORITERINGER}}
- Styringsparametere: {{PARAMETERE}}
- Budsjettramme: {{BUDSJETT}}

--- TOPP KONSULENTER ---

| Navn | Kompetanse | Tilgjengelighet | Relasjon til kunde |
|------|------------|-----------------|---------------------|
| {{KONSULENT_1}} | {{KOMPETANSE_1}} | {{TILG_1}} | {{RELASJON_1}} |
| {{KONSULENT_2}} | {{KOMPETANSE_2}} | {{TILG_2}} | {{RELASJON_2}} |

--- DOKUMENTSAMMENDRAG (HURTIGREFERANSE) ---

Folgende er sammendrag av nokkeldokumenter som finnes i SharePoint. Bruk dette som utgangspunkt for svar, men SOK ALLTID i SharePoint for fullstendige detaljer nAr brukeren vil ha mer.

{{DOKUMENT_1_TITTEL}} ({{DATO}}, {{SIDER}} sider):
- {{NOKKELFAKTA_1}}
- {{NOKKELFAKTA_2}}
- {{BELOPSINFORMASJON}}
- {{BESLUTNINGER}}
- {{AKSJONER}}
- {{PERSONER_INVOLVERT}}

{{DOKUMENT_2_TITTEL}} ({{DATO}}, {{SIDER}} sider):
- {{NOKKELFAKTA_1}}
- {{NOKKELFAKTA_2}}

(Gjenta for alle nokkeldokumenter - minimum 5-8 dokumenter)

--- SHAREPOINT MAPPESTRUKTUR ---

📂 {{ALIAS}} (rotmappe)
├── 📁 Avtaler
│   ├── 📁 Rammeavtaler
│   ├── 📁 Endringsbilag
│   └── 📁 SLA
├── 📁 Taktiske moter
│   ├── 📁 AI Oppsummeringer og Notater
│   └── 📁 Presentasjoner
├── 📁 Prosjekter
│   ├── 📁 {{PROSJEKT_1}}
│   └── 📁 {{PROSJEKT_2}}
├── 📁 Okonomi
│   ├── 📁 Fakturaer
│   └── 📁 Budsjett
├── 📁 Strategi
└── 📁 Diverse

(Tilpass mappestrukturen etter kundens SharePoint-oppsett)

--- SOKESTRATEGI OG VERKTOYBRUK ---

Du har folgende sokeverktoy:
1. Azure AI Search (forhAndsindeksert): Semantisk sok over alle dokumenter inkl. PDF-er. Bruk som PRIMAERT verktoy.
2. SharePoint Grounding (sanntid): Soker direkte i SharePoint Online. Bruk for A finne dokumenter og verifisere detaljer.
3. Dokumentsammendraget ovenfor: Bruk som hurtigreferanse nAr sokeverktoy gir tomme eller utilstrekkelige resultater.

ALLTID prov Azure AI Search forst. Hvis resultatet er tomt eller utilstrekkelig, folg opp med SharePoint Grounding. Bruk dokumentsammendraget som tredje fallback.
```

---

## 3. AGENT OPPDATERINGSSCRIPT TEMPLATE

Opprett som `{agent_alias}_update_agent.py`. Brukes for A pushe agentinstruksjoner til Azure AI Foundry.

```python
"""
Oppdaterer {{AGENT_NAME}} kundeagent i Azure AI Foundry.
"""
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    SharepointPreviewTool,
    SharepointGroundingToolParameters,
)
from azure.identity import DefaultAzureCredential
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- Konfigurasjon ---
INSTRUCTIONS_FILE = r'C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\{{agent_alias}}_instructions.txt'
AGENT_NAME = "{{AGENT_NAME}}"
CONNECTION_ID = (
    "/subscriptions/59aae656-c78b-4bc5-bcfd-e31748e6f6e2"
    "/resourceGroups/RG-KATE"
    "/providers/Microsoft.CognitiveServices/accounts/kateecosystem-resource"
    "/projects/kateecosystem"
    "/connections/{{CONNECTION}}"
)

# --- Les instruksjoner ---
with open(INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
    instructions = f.read()

print(f"Instructions length: {len(instructions)} chars")

# --- Opprett klient ---
client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)

# --- Konfigurer SharePoint Grounding tool ---
tool = SharepointPreviewTool(
    sharepoint_grounding_preview=SharepointGroundingToolParameters(
        project_connections=[{"project_connection_id": CONNECTION_ID}]
    )
)

# --- Opprett ny versjon ---
agent = client.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-5.3-chat",
        instructions=instructions,
        tools=[tool],
    )
)

print(f"Agent updated successfully!")
print(f"Name: {agent.name}")
print(f"ID: {agent.id}")
print(f"Instructions preview: {agent.instructions[:200]}...")
```

### Kjoring

```bash
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {{agent_alias}}_update_agent.py
```

### Plassholdere A erstatte

| Plassholder | Eksempel (Komplett) | Eksempel (STAF) |
|-------------|---------------------|-------------------|
| `{{agent_alias}}` | `komplett` | `staf` |
| `{{AGENT_NAME}}` | `Komplett` | `Statsforvalteren` |
| `{{CONNECTION}}` | `Komplett` | `STAF` |

---

## 4. EVALUERINGSRAMMEVERK (3-TIER, 33 SPORSMAL)

Hver kundeagent evalueres med tre sett som til sammen utgjor 33 sporsmal. Hvert sett tester forskjellige aspekter av agentens kapabilitet.

### Tier 1: Faktakunnskap (15 sporsmal)

Filnavn: `eval_{alias}_15.py`
Output: `eval_{alias}_resultater.json`

| # | Kategori | Antall | Hva testes |
|---|----------|--------|------------|
| 1 | Kontakter | 3 | Nokkelpersoner hos kunde og i Atea-teamet |
| 2 | Avtaler | 3 | Avtalenummer, verdier, perioder, signatarer |
| 3 | Okonomi | 2 | MAnedlige/Arlige belop, trender, endringer |
| 4 | Prosjekter | 3 | PAgAende initiativer, status, tidslinjer |
| 5 | Strategi | 2 | Strategiske mAl, KPI-er, prioriteringer |
| 6 | Hardware | 1 | Livssyklus, utlopsdatoer, fornyelser |
| 7 | Konsulenter | 1 | Nettverks-/kompetanseinformasjon |

### Tier 2: Land & Expand (10 sporsmal)

Filnavn: `eval_{alias}_land_expand_10.py`
Output: `eval_{alias}_land_expand_resultater.json`

| # | Kategori | Antall | Hva testes |
|---|----------|--------|------------|
| 1 | Identifisere muligheter | 3 | Evne til A finne nye salgsinitiativ |
| 2 | Account planning | 2 | 12-mAneders plan, stakeholder-strategi |
| 3 | Cross-sell | 2 | Identifisere tjenester fra andre forretningsomrAder |
| 4 | Moteforberedelse | 2 | Briefing-notater, agendaforslag |
| 5 | RisikohAndtering | 1 | Churn-risiko, mitigering |

### Tier 3: SharePoint Grounding (8 sporsmal)

Filnavn: `eval_{alias}_sharepoint_verify.py`
Output: `eval_{alias}_sharepoint_verify_resultater.json`

Hvert sporsmal MÅ inkludere `kilde`-felt som peker til eksakt SharePoint-dokument:

```python
{
    "id": "SP-01",
    "kategori": "Copilot Discovery",
    "sporsmal": "Sporsmal som KUN kan besvares fra SharePoint-dokumenter...",
    "forventet": "Forventet svar med spesifikke tall og detaljer...",
    "kilde": "CoPilot/Komplett Microsoft Copilot for M365 Discovery and Mapping.pdf, side 11"
}
```

Testkategorier varierer per kunde men bor dekke:
- Motereferater (taktiske moter, statusmoter)
- Strategidokumenter (tildelingsbrev, Arsplaner)
- Tilbud og prosjektplaner
- Avtaler og endringsbilag
- Workbooks og rapporter

### Scoring

- Rating: 0-100 per sporsmal
- Scoring gjores manuelt eller via LLM-evaluator etter kjoering
- Output: JSON per tier + kombinert PDF-rapport

### Evalueringsscript-struktur

```python
"""
{{ALIAS}} Evalueringssett - {{N}} sporsmal
{{Kundenavn}} kundeagent evaluering
"""

import json, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)
oai = client.get_openai_client()

EVAL_SET = [
    {
        "id": "{{ALIAS}}-01",
        "kategori": "Kontakter",
        "sporsmal": "Sporsmal pA norsk...",
        "forventet": "Forventet svar med konkrete tall, datoer, navn...",
    },
    # ... flere sporsmal
]

AGENT_NAME = "{{AGENT_NAME}}"

print(f"{{ALIAS}} Evalueringssett - {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: {AGENT_NAME}")
print("=" * 100)

results = []

for item in EVAL_SET:
    print(f"\n{'---'*34}")
    print(f"[{item['id']}] {item['kategori']}")
    print(f"Sporsmal: {item['sporsmal']}")
    print(f"Forventet: {item['forventet']}")
    print(f"{'---'*17}")

    conv = oai.conversations.create()
    oai.conversations.items.create(
        conversation_id=conv.id,
        items=[{"type": "message", "role": "user", "content": item["sporsmal"]}],
    )
    response = oai.responses.create(
        conversation=conv.id,
        extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
        input="",
    )

    answer = ""
    for out in response.output:
        if out.type == "message":
            for block in out.content:
                if block.type == "output_text":
                    answer += block.text

    print(f"Svar:\n{answer}")
    results.append({
        "id": item["id"],
        "kategori": item["kategori"],
        "sporsmal": item["sporsmal"],
        "forventet": item["forventet"],
        "svar": answer,
    })

# Lagre resultater
outfile = f"eval_{AGENT_NAME.lower()}_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nEvaluering fullfort. Resultater lagret i: {outfile}")
```

### Kjoring av evalueringer

```bash
# Tier 1
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_15.py

# Tier 2
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_land_expand_10.py

# Tier 3
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_sharepoint_verify.py

# PDF-rapport
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {alias}_full_eval_rapport.py
```

---

## 5. CONVERSATIONS API

Alle evalueringer og integrasjoner bruker Azure AI Foundry Conversations API via OpenAI-klienten.

### Oppsett

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)
oai = client.get_openai_client()
```

### Send sporring til agent

```python
# Opprett samtale
conv = oai.conversations.create()

# Legg til brukermelding
oai.conversations.items.create(
    conversation_id=conv.id,
    items=[{"type": "message", "role": "user", "content": question}],
)

# HEnt agentsvar
response = oai.responses.create(
    conversation=conv.id,
    extra_body={"agent_reference": {"name": "AGENT_NAME", "type": "agent_reference"}},
    input="",
)

# Ekstraher tekst fra svar
answer = ""
for out in response.output:
    if out.type == "message":
        for block in out.content:
            if block.type == "output_text":
                answer += block.text
```

### Viktige detaljer

- `agent_reference.name` mA matche eksakt agentnavn i Azure AI Foundry
- `agent_reference.type` er alltid `"agent_reference"`
- `input` settes til tom streng (meldingen sendes via `conversations.items.create`)
- Agenten kan returnere flere `output`-blokker; iterer over alle
- Conversations API stotter flerturnsamtaler ved A legge til flere items

---

## 6. DOKUMENTSAMMENDRAG PROSESS

Dokumentsammendrag er Lag 3 i sokstrategien og sikrer at agenten alltid har nokkelfakta tilgjengelig, selv nAr sokverktoyene feiler.

### Steg 1: Synkroniser SharePoint til lokal maskin

Sikre at kundens SharePoint-mappe er synkronisert via OneDrive til lokal disk.

### Steg 2: Identifiser nokkeldokumenter

Prioriter folgende dokumenttyper (minimum 5-8 dokumenter):

| Prioritet | Dokumenttype | Eksempler |
|-----------|-------------|-----------|
| 1 | Motereferater | Taktiske moter, statusmoter, styringsmoter |
| 2 | Strategidokumenter | Virksomhetsplan, tildelingsbrev, Arsrapport |
| 3 | Tilbud og prosjektplaner | SOW, prosjektplaner, bistandsbeskrivelser |
| 4 | Avtaler | Rammeavtaler, endringsbilag, SLA |
| 5 | Workbooks og rapporter | Account workbook, modenhetsanalyser, rapporter |

### Steg 3: Ekstraher nokkelfakta

For hvert dokument, ekstraher:

- **NOKKELFAKTA**: Hovedfunn, konklusjoner, anbefalinger
- **DATOER**: Alle relevante datoer og tidsfrister
- **BESLUTNINGER**: Vedtak, godkjenninger, avslag
- **AKSJONER**: Aksjonspunkter med ansvarlige og frister
- **BELOP**: Alle pengebelop, estimater, budsjetter
- **PERSONER**: Hvem var involvert, hvem er ansvarlig

### Steg 4: Formater som sammendrag

Bruk dette formatet konsekvent:

```
{{DOKUMENT_TITTEL}} ({{DATO}}, {{ANTALL}} sider):
- Nokkelfunn 1 med spesifikke tall og navn
- Nokkelfunn 2
- Beslutning: {{beslutning}} godkjent av {{person}}
- Aksjon: {{handling}} - ansvarlig: {{person}}, frist: {{dato}}
- Belop: {{belop}} NOK for {{formAl}}
```

### Steg 5: Plasser i instruksjonsfilen

Dokumentsammendraget plasseres i seksjonen `DOKUMENTSAMMENDRAG (HURTIGREFERANSE)`, like FOR `SOKESTRATEGI OG VERKTOYBRUK`-seksjonen.

### Tips

- Hold hvert sammendrag kortfattet men spesifikt (inkluder tall, datoer, navn)
- Oppdater sammendragene etter hvert taktisk mote
- Nye dokumenter legges til uten A fjerne eksisterende sammendrag
- Merk tydelig alder pA dokumentet sA agenten kan kommunisere dette

---

## 7. SJEKKLISTE NY AGENT

Folg denne sjekklisten sekvensielt for A bygge en ny kundeagent:

```
PRE-KRAV
- [ ] Identifiser kundens SharePoint-site og fA tilgang
- [ ] Verifiser at Atea har kundeteam-info og avtaledata tilgjengelig

INFRASTRUKTUR (Azure AI Foundry portal)
- [ ] SharePoint-tilkobling opprettet i Azure AI Foundry portal
      Navn: {{CONNECTION}} (f.eks. "STAF", "Komplett")
- [ ] (Valgfritt) Azure AI Search indeks opprettet og koblet
      Indeksnavn: {{alias}}-sharepoint-index

DOKUMENTARBEID
- [ ] OneDrive-dokumenter synkronisert lokalt
- [ ] Nokkeldokumenter identifisert (minst 5-8 dokumenter)
- [ ] Dokumenter lest og oppsummert (folg seksjon 6)

INSTRUKSJONER
- [ ] Instruksjonsfil opprettet: {alias}_instructions.txt
- [ ] Alle seksjoner fra malen er utfylt (seksjon 2)
      - [ ] Rollebeskrivelse
      - [ ] Latency budget
      - [ ] Sokeregler
      - [ ] Kundeinformasjon
      - [ ] Nokkelpersoner hos kunde
      - [ ] Atea kundeteam
      - [ ] Aktive rammeavtaler
      - [ ] Okonomi og omsetning
      - [ ] Hardware livssyklus
      - [ ] PAgAende initiativer
      - [ ] Virksomhetsstrategi
      - [ ] Tildelingsbrev (offentlig sektor)
      - [ ] Topp konsulenter
      - [ ] Dokumentsammendrag
      - [ ] SharePoint mappestruktur
      - [ ] Sokestrategi og verktoybruk
- [ ] Instruksjonsfil quality-checket (ingen tomme plassholdere)

DEPLOYMENT
- [ ] Agent oppdateringsscript opprettet: {alias}_update_agent.py
- [ ] Agent pushet til Azure (create_version)
- [ ] Verifiser at agent svarer pA et enkelt testsporsmal

EVALUERING
- [ ] Tier 1 evaluering opprettet (15 spm): eval_{alias}_15.py
- [ ] Tier 1 evaluering kjort -> eval_{alias}_resultater.json
- [ ] Tier 2 evaluering opprettet (10 spm): eval_{alias}_land_expand_10.py
- [ ] Tier 2 evaluering kjort -> eval_{alias}_land_expand_resultater.json
- [ ] Tier 3 evaluering opprettet (8 spm): eval_{alias}_sharepoint_verify.py
- [ ] Tier 3 evaluering kjort -> eval_{alias}_sharepoint_verify_resultater.json

RAPPORTERING
- [ ] Evalueringsrapport-script opprettet: {alias}_full_eval_rapport.py
- [ ] Kombinert PDF-rapport generert -> {ALIAS}_Komplett_Evalueringsrapport.pdf
- [ ] Agent-versjon dokumentert i denne filen (seksjon 9)
- [ ] Score vurdert (mAl: >= 80/100 samlet)

ITERASJON (ved score < 80)
- [ ] Identifiser svake kategorier fra evalueringsresultatene
- [ ] Legg til flere dokumentsammendrag for svake omrAder
- [ ] Oppdater instruksjoner og push ny versjon
- [ ] Kjor evaluering pA nytt
```

---

## 8. KJENTE PROBLEMER

| Problem | Symptom | Losning |
|---------|---------|---------|
| Python 3.14 namespace packages | `ModuleNotFoundError` for azure-pakker | Bruk venv: `python3 -m venv /tmp/stafenv && source /tmp/stafenv/bin/activate && pip install azure-ai-projects azure-identity` |
| SharePoint Grounding tomme resultater | Agent returnerer "Jeg fant ingen informasjon" | Dokumentsammendrag som Lag 3 fallback dekker nokkelfakta |
| reportlab HTML/XML parsing | `XMLSyntaxError` i PDF-generering | Implementer `clean_md()` som stripper ALLE HTML-tags for Paragraph |
| AgentVersionDetails mangler 'model' | `AttributeError: 'AgentVersionDetails' has no attribute 'model'` | Uskyldig feil, agent opprettes OK. Fjern `print(agent.model)` |
| reportlab BodyText style conflict | `KeyError: 'BodyText'` eller duplikat-feil | Rename til 'BodyJust' eller 'BJ' eller bruk unik stilnavn |
| Lange agentsvar sprenger PDF-side | `LayoutError: too large on page` | Trunker til 1200 tegn, fjern `KeepTogether`, bruk `allowSplitting=True` |
| UTF-8 encoding i Python | `UnicodeEncodeError` for norske tegn | Legg til `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` OG kjor med `PYTHONIOENCODING=utf-8` |
| SharePoint connection not found | `ConnectionNotFoundError` i agent | Verifiser CONNECTION_ID-stien matcher eksakt. Sjekk i Azure AI Foundry portal under Connections |
| Conversations API timeout | Agentsvar tar >60s | Reduser kompleksiteten i sporsMAlet, eller legg til bedre dokumentsammendrag sA agenten trenger ferre sokekall |

---

## 9. EKSISTERENDE AGENTER (REFERANSE)

| Agent | Alias | Versjon | Status | Eval Score | Connection | Merknad |
|-------|-------|---------|--------|------------|------------|---------|
| Komplett | komplett | - | Produksjon | Referansemonster | Komplett | Gold standard, 3-lags sok, full dokumentsammendrag |
| Statsforvalteren | staf | v18 | Produksjon | 88.4/100 | STAF | Offentlig sektor, tildelingsbrev-seksjon inkludert |

### NAr du legger til en ny agent

Oppdater tabellen ovenfor med:
- Agent: Fullt agentnavn i Azure AI Foundry
- Alias: Kort alias brukt i filnavn (lowercase)
- Versjon: Siste versjonsnummer
- Status: Utvikling / Test / Produksjon
- Eval Score: Gjennomsnittlig score fra siste 33-sporsmAls evaluering
- Connection: Navn pA SharePoint-tilkoblingen i Azure AI Foundry
- Merknad: Spesielle forhold (bransje, ekstra tools, etc.)

---

## FILNAVNKONVENSJONER

Alle filer for en kundeagent folger dette monsteret:

```
{alias}_instructions.txt              # Instruksjonsfil
{alias}_update_agent.py               # Agent deployment script
eval_{alias}_15.py                    # Tier 1: Faktakunnskap (15 spm)
eval_{alias}_land_expand_10.py        # Tier 2: Land & Expand (10 spm)
eval_{alias}_sharepoint_verify.py     # Tier 3: SharePoint Grounding (8 spm)
eval_{alias}_resultater.json          # Tier 1 resultater
eval_{alias}_land_expand_resultater.json  # Tier 2 resultater
eval_{alias}_sharepoint_verify_resultater.json  # Tier 3 resultater
{alias}_full_eval_rapport.py          # PDF-rapport generator
{ALIAS}_Komplett_Evalueringsrapport.pdf  # Kombinert PDF-rapport
```

Eksempel for en ny kunde "NMD":
```
nmd_instructions.txt
nmd_update_agent.py
eval_nmd_15.py
eval_nmd_land_expand_10.py
eval_nmd_sharepoint_verify.py
...
```

---

## HURTIGREFERANSE: NY AGENT PÅ 30 MINUTTER

For erfarne utviklere som har gjort dette for:

1. Kopier `staf_instructions.txt` som utgangspunkt
2. Erstatt alle STAF-spesifikke data med ny kundedata
3. Les og oppsummer 5-8 nokkeldokumenter fra SharePoint
4. Opprett SharePoint-tilkobling i Azure AI Foundry portal
5. Kopier `staf_update_agent.py`, endre AGENT_NAME og CONNECTION
6. Kjor `{alias}_update_agent.py`
7. Test med 3-5 manuelle sporsmal
8. Kopier evalueringsscripts, tilpass sporsmal til ny kunde
9. Kjor full 33-sporsmAls evaluering
10. Generer PDF-rapport og dokumenter score
