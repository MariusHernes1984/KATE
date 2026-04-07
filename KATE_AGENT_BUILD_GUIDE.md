# KATE Kundeagent — Bygge- og Iterasjonsguide

Praktisk steg-for-steg guide for å generere agenter i KATE-miljøet, bruke skills, og iterere basert på evalueringer.

Autoritativ referanse: `KATE_AGENT_STANDARD.md` (§1–9). Denne guiden er en arbeidsflyt-oversikt.

---

## Del 1 — Generere en ny kundeagent

### Pre-krav
1. Få tilgang til kundens SharePoint-site.
2. Synk SharePoint-mappen lokalt via OneDrive.
3. Verifiser at Atea har kundeteam, avtaledata og org.info tilgjengelig.

### Infrastruktur (Azure AI Foundry portal)
4. Opprett SharePoint-tilkobling i `kateecosystem`-prosjektet. Navngi den f.eks. `NMD`, `STAF`, `Komplett`.
5. (Valgfritt, men anbefalt) Opprett Azure AI Search-indeks `{alias}-sharepoint-index` og koble til.

### Bygg instruksjonsfilen — `{alias}_instructions.txt`
6. Kopier malen fra `KATE_AGENT_STANDARD.md` §2 — eller bruk `staf_instructions.txt` som utgangspunkt.
7. Fyll ut alle seksjoner:
   - Rollebeskrivelse + latency budget
   - Søkeregler (1–10)
   - Kundeinformasjon (org.nr, bransje, lokasjoner, direktør)
   - Nøkkelkontakter hos kunden
   - Atea kundeteam (KAM, sponsor, etc.)
   - Aktive rammeavtaler
   - Økonomi og omsetning
   - Hardware livssyklus
   - Pågående initiativer
   - Virksomhetsstrategi
   - Tildelingsbrev (KUN offentlig sektor)
   - Topp konsulenter
   - **Dokumentsammendrag** (5–8 nøkkeldokumenter — se Del 4)
   - SharePoint mappestruktur
   - Søkestrategi og verktøybruk
8. QA: ingen tomme `{{PLASSHOLDER}}` igjen.

### Deploy til Azure AI Foundry
9. Kopier `staf_update_agent.py` → `{alias}_update_agent.py`. Endre:
   - `INSTRUCTIONS_FILE`
   - `AGENT_NAME`
   - Siste segment i `CONNECTION_ID`
10. Kjør:
    ```bash
    PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {alias}_update_agent.py
    ```
    Hver kjøring kaller `client.agents.create_version(...)` og lager en NY versjon — ingen overskriving.
11. Røyk-test med 3–5 manuelle spørsmål via Foundry portal eller Conversations API.

---

## Del 2 — Skills (3-lags søkearkitektur)

KATE-agentenes "skills" er tre kombinerte byggeklosser. Søkereglene i instruksjonene styrer orkestreringen.

| Lag | Skill / Tool | Når den brukes | Latency |
|---|---|---|---|
| 1 | **Azure AI Search** (`azure_ai_search`, semantisk, `top_k=10`) | PRIMÆRT — semantisk søk over forhåndsindekserte dokumenter inkl. PDF | <2s |
| 2 | **SharePoint Grounding Preview** (`SharepointPreviewTool`) | FALLBACK — sanntid mot SharePoint Online for nyeste filer | 3–8s |
| 3 | **Innbakte dokumentsammendrag** (i instruksjonene) | SISTE FALLBACK — alltid tilgjengelig når søk feiler | 0s |

### Flyt
```
Brukerspørring
    ↓
[Lag 1] Azure AI Search  ──treff──> svar
    ↓ tomt
[Lag 2] SharePoint Grounding  ──treff──> svar
    ↓ tomt
[Lag 3] Dokumentsammendrag  ──> svar (med kildemerknad)
```

### Legge til en ny skill (f.eks. CRM-lookup, custom function tool)
1. Legg den til i `tools=[...]`-listen i `{alias}_update_agent.py`.
2. Dokumenter den i `--- SØKESTRATEGI OG VERKTØYBRUK ---`-seksjonen i instruksjonene.
3. Legg til konkrete regler for når den skal brukes vs. de eksisterende lagene.
4. Push ny versjon og kjør evaluering for å måle effekten.

---

## Del 3 — Evalueringsrammeverk (33 spørsmål, 3 tiers)

| Tier | Fil | Antall | Hva testes |
|---|---|---|---|
| 1 — Faktakunnskap | `eval_{alias}_15.py` | 15 | Kontakter, avtaler, økonomi, prosjekter, strategi, hardware, konsulenter |
| 2 — Land & Expand | `eval_{alias}_land_expand_10.py` | 10 | Mulighetsidentifisering, account planning, cross-sell, møteforberedelse, risiko |
| 3 — SharePoint Grounding | `eval_{alias}_sharepoint_verify.py` | 8 | Spørsmål som KUN kan besvares fra spesifikke SharePoint-dokumenter (med `kilde`-felt) |

**Mål: ≥ 80/100 samlet score.**

### Iterasjonsløkken

```
endre instruksjoner  →  push ny versjon  →  kjør 33 spm eval  →  dual scoring
       ↑                                                                ↓
       └──────────── analyser svake kategorier ←─── PDF-rapport ────────┘
```

### Steg A — Kjør baseline
```bash
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_15.py
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_land_expand_10.py
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe eval_{alias}_sharepoint_verify.py
```
Gir tre `eval_{alias}_*_resultater.json`.

### Steg B — Dual scoring
Bruk **både** keyword-scoring og LLM-as-judge:
- **Keyword** fanger faktasamsvar (navn, datoer, beløp, avtalenummer).
- **LLM-judge** fanger fullstendighet, struktur og tone.

Lagre i `eval_{alias}_scored.json` / `..._scored_v2.json`.

### Steg C — Generer rapport
```bash
PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {alias}_full_eval_rapport.py
```
PDF gir score per kategori og per spørsmål.

### Steg D — Diagnose svake områder

| Symptom | Sannsynlig årsak | Tiltak |
|---|---|---|
| Lav Tier 1 (faktakunnskap) | Metadata-tabeller i instruksjonene er ufullstendige eller feil | Oppdater strukturerte tabeller (kontakter, avtaler, økonomi, hardware) |
| Lav Tier 2 (Land & Expand) | Agenten mangler strategisk kontekst | Legg til dokumentsammendrag fra strategi, account workbook, modenhetsanalyser. Mer eksplisitte instruksjoner om proaktive forslag |
| Lav Tier 3 (SharePoint Grounding) | Søkelagene fungerer ikke | Sjekk SharePoint-connection, AI Search-indeks oppdatert, dokument i synket mappe, kilde-felt manuelt |
| Hallusinasjoner på enkeltspørsmål | Manglende metadata + svakt søketreff | Legg til relevant fakta i instruksjonene ELLER forbedre dokumentsammendrag |

### Steg E — Iterer
1. Oppdater `{alias}_instructions.txt`.
2. Push ny versjon: `python {alias}_update_agent.py`.
3. Kjør **samme 33 spørsmål** på nytt (epler-mot-epler).
4. Sammenlign v1 vs v2 per kategori (se eksisterende `KATE_Agent_Sammenligning_v2_*.html`).
5. Logg ny versjon i `KATE_AGENT_STANDARD.md` §9 med score.

### Steg F — Utvid eval-settet over tid
- Når nye feilmoduser oppdages i produksjon, legg til spørsmål i passende tier.
- **Behold gamle spørsmål** som regresjonssuite.
- STAF er på v18 — bevis på at iterasjonsløkken funker.

---

## Del 4 — Dokumentsammendrag (Lag 3)

Dette er det viktigste fallback-laget. Uten gode sammendrag faller agenten ned på "fant ingen informasjon".

### Prioritering av dokumenttyper
| Prioritet | Type | Eksempler |
|---|---|---|
| 1 | Møtereferater | Taktiske møter, statusmøter, styringsmøter |
| 2 | Strategidokumenter | Virksomhetsplan, tildelingsbrev, årsrapport |
| 3 | Tilbud / prosjektplaner | SOW, prosjektplaner, bistandsbeskrivelser |
| 4 | Avtaler | Rammeavtaler, endringsbilag, SLA |
| 5 | Workbooks / rapporter | Account workbook, modenhetsanalyser |

### Format per dokument
```
{{TITTEL}} ({{DATO}}, {{ANTALL}} sider):
- Nøkkelfunn 1 med spesifikke tall og navn
- Nøkkelfunn 2
- Beslutning: {{beslutning}} godkjent av {{person}}
- Aksjon: {{handling}} — ansvarlig {{person}}, frist {{dato}}
- Beløp: {{beløp}} NOK for {{formål}}
```

### Tips
- Hold kortfattet, men spesifikt — alltid med tall, datoer, navn.
- Oppdater etter hvert taktisk møte.
- Merk dokumenter eldre enn 6 måneder.
- Plasser sammendragene rett FØR `--- SØKESTRATEGI OG VERKTØYBRUK ---`-seksjonen.

---

## Del 5 — Filnavnkonvensjoner

```
{alias}_instructions.txt                           # Instruksjonsfil
{alias}_update_agent.py                            # Deployment script
eval_{alias}_15.py                                 # Tier 1
eval_{alias}_land_expand_10.py                     # Tier 2
eval_{alias}_sharepoint_verify.py                  # Tier 3
eval_{alias}_*_resultater.json                     # Eval-resultater
eval_{alias}_*_scored*.json                        # Etter dual scoring
{alias}_full_eval_rapport.py                       # PDF-generator
{ALIAS}_Komplett_Evalueringsrapport.pdf            # Sluttrapport
```

---

## Hurtigreferanse: ny agent på 30 minutter

1. Kopier `staf_instructions.txt` → `{alias}_instructions.txt`
2. Bytt all STAF-spesifikk data
3. Oppsummer 5–8 nøkkeldokumenter
4. Opprett SharePoint-tilkobling i Foundry portal
5. Kopier `staf_update_agent.py`, endre AGENT_NAME + CONNECTION
6. Kjør `{alias}_update_agent.py`
7. Test 3–5 spørsmål manuelt
8. Kopier eval-scripts, tilpass spørsmål
9. Kjør 33-spm evaluering
10. Generer PDF, dokumenter score, iterer ved <80
