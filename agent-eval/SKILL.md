---
name: agent-eval
description: Evaluate a KATE customer agent end-to-end — generate questions, run them against the agent, score answers, and produce a PDF report. Use this skill automatically after creating or deploying a new customer agent, when the user asks to evaluate/test/benchmark any KATE agent, when they say "kjor eval", "test agenten", "evaluer", or mention agent quality, accuracy, or grounding verification. Also trigger when comparing agent versions or checking if an agent update improved results.
---

# KATE Agent Evaluator

You are evaluating an Azure AI Foundry customer agent for the KATE platform. The goal is to verify that the agent accurately retrieves and presents information from its SharePoint knowledge base and embedded document summaries.

## Referansedokument

**LES ALLTID FØRST:**
`C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\KATE_AGENT_STANDARD.md`

Se seksjon 4 (Evalueringsrammeverk) for komplett spesifikasjon.

## Når denne kjører

Automatisk etter at en kundeagent er opprettet/deployet, eller når brukeren vil teste agentens kvalitet. Produserer en scoret PDF-evalueringsrapport.

## Hva du trenger

1. **Agent name** — Foundry-agentnavn (f.eks. "komplett", "Statsforvalteren")
2. **Kundealias** — kort kode (f.eks. "KOMPLETT", "STAF")
3. **Kundens lokale SharePoint-mappe** — synkronisert mappe
4. **Agent instruksjonsfil** — `{agent}_instructions.txt`

## Azure-miljø

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)
oai = client.get_openai_client()
```

Kjør med: `PYTHONIOENCODING=utf-8 /tmp/stafenv/Scripts/python.exe {script}.py`

## 3-Tier Evalueringsrammeverk (33 spørsmål)

Hver agent evalueres over tre tiers. Kjør dem i rekkefølge.

### Tier 1: Faktakunnskap (15 spørsmål)

Tester faktabasert gjenkalling. Dette er baseline — agenten må bestå denne.

| Kategori | Antall | Hva testes |
|----------|--------|------------|
| Kontakter | 3 | Nøkkelpersoner hos kunde og Atea, roller, kontaktinfo |
| Avtaler | 3 | Avtaledetaljer — nummer, datoer, verdier, omfang, signatarer |
| Økonomi | 2 | Omsetning, trender, prognoser, kostnadsfordeling |
| Prosjekter | 3 | Pågående initiativer — tidslinjer, eiere, status, leveranser |
| Strategi | 2 | Strategiske mål, KPIer, prioriteringer |
| Hardware | 1 | Livssyklusdatoer, kommende fornyelser |
| Konsulenter | 1 | Topp konsulenter, vurderinger |

**ID-format:** `{ALIAS}-01` til `{ALIAS}-15`
**Filnavn:** `eval_{alias}_15.py` → `eval_{alias}_resultater.json`

### Tier 2: Land & Expand (10 spørsmål)

Tester agentens evne til å støtte salgsaktiviteter.

| Kategori | Antall | Hva testes |
|----------|--------|------------|
| Identifisere muligheter | 3 | Kan agenten finne salgsmuligheter fra kundedata? |
| Account planning | 2 | Kan den lage vekstplaner med tidslinjer og estimater? |
| Cross-sell | 2 | Kan den foreslå komplementære tjenester? |
| Møteforberedelse | 2 | Kan den forberede møtebriefs med kontekst? |
| Risikohåndtering | 1 | Kan den identifisere churn-risiko? |

Spørsmålene skal formuleres som en KAM ville spurt — samtalebaserte, scenariobaserte.

**ID-format:** `LE-01` til `LE-10`
**Filnavn:** `eval_{alias}_land_expand_10.py` → `eval_{alias}_land_expand_resultater.json`

### Tier 3: SharePoint Grounding Verification (8 spørsmål)

Tester om agenten faktisk henter fra SharePoint-dokumenter vs. bare gjentar instruksjoner.

Hvert spørsmål:
- MÅ ha et `kilde`-felt som peker til spesifikt SharePoint-dokument
- Må spørre om informasjon som KUN finnes i dokumentene, ikke i instruksjonene
- Skal inkludere SharePoint-indikator-sjekk i resultatene

| Hva testes | Eksempler |
|------------|-----------|
| PDF-spesifikke detaljer | Copilot-rapporter, prosjektplaner, SOWer |
| Møtespesifikke aksjoner | Beslutninger, deltakere, datoer fra referater |
| Dokumentinterne tall | Figurer ikke oppsummert i instruksjonene |
| Tekniske detaljer | Fra tilbud, kontrakter, tekniske rapporter |

**ID-format:** `SP-01` til `SP-08` (eller `{ALIAS}-SP-01`)
**Filnavn:** `eval_{alias}_sharepoint_verify.py` → `eval_{alias}_sharepoint_verify_resultater.json`

## Spørsmålsformat

```python
{
    "id": "{ALIAS}-01",
    "kategori": "Kontakter",
    "sporsmal": "Spørsmålstekst på norsk",
    "forventet": "Forventet svar med spesifikke fakta, tall, datoer",
    # Tier 3 kun:
    "kilde": "SharePoint/mappe/dokument.pdf, side N"
}
```

## Evalueringsscript-mønster

```python
"""
{Customer} Evalueringssett – {N} spørsmål
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
    # ... spørsmål her
]

results = []
for item in EVAL_SET:
    conv = oai.conversations.create()
    oai.conversations.items.create(
        conversation_id=conv.id,
        items=[{"type": "message", "role": "user", "content": item["sporsmal"]}],
    )
    response = oai.responses.create(
        conversation=conv.id,
        extra_body={"agent_reference": {"name": "AGENT_NAME", "type": "agent_reference"}},
        input="",
    )
    answer = ""
    for out in response.output:
        if out.type == "message":
            for block in out.content:
                if block.type == "output_text":
                    answer += block.text

    results.append({
        "id": item["id"],
        "kategori": item["kategori"],
        "sporsmal": item["sporsmal"],
        "forventet": item["forventet"],
        "svar": answer,
    })

outfile = f"eval_{alias}_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

## Dual Scoring — Keyword + LLM-as-Judge

Hvert spørsmål scores med **to metoder** som fanger ulike aspekter av svarkvalitet.

### Metode 1: Keyword-matching (hurtigsjekk)

Rask, deterministisk sjekk av om nøkkelfakta finnes i svaret. Kjøres først.

- Ekstraher nøkkelfakta fra `forventet`-feltet (splitt på `. , ; ( ) \n`)
- For hvert faktum: sjekk om minst 50% av signifikante ord (>3 tegn) finnes i svaret
- Score: `(treff / totalt_antall_fakta) * 100`

Keyword-score er nyttig for å raskt identifisere manglende fakta, men den misser omformuleringer og synonymer (f.eks. "kr 977.000" vs "NOK 977 000").

### Metode 2: LLM-as-Judge (hovedscore)

Bruk `gpt-4.1` som dommer via chat completion. Dette er hovedscoren som rapporteres.

**Judge-prompt:**
```
Du er en streng evaluator for en kundeagent hos Atea. Vurder agentens svar mot fasit.

SPØRSMÅL: {sporsmal}
FASIT: {forventet}
NØKKELORD SOM BØR FINNES: {nokkelord}
AGENTENS SVAR: {svar}

Returner BARE et JSON-objekt:
{
  "korrekthet": <0-10>,
  "nokkelord_treff": <antall treff>,
  "nokkelord_totalt": <totalt>,
  "hallusinering": <0-10, 0=ingen, 10=mye feil>,
  "fullstendighet": <0-10>,
  "formatering": <0-10>,
  "begrunnelse": "<kort forklaring, maks 2 setninger>"
}
```

**Composite score (0-100):**
```
composite = (korrekthet * 0.35 + fullstendighet * 0.25 + (10 - hallusinering) * 0.25 + formatering * 0.15) * 10
```

Vektingen reflekterer at korrekthet er viktigst (35%), mens hallusinerings-resistens og fullstendighet teller like mye (25% hver). Formatering er minst viktig (15%) men fortsatt relevant for KAM-brukeropplevelsen.

### Scoring-skala

| Score | Vurdering | Beskrivelse |
|-------|-----------|-------------|
| 95-100 | Utmerket | Alle nøkkelfakta korrekte, godt formatert, komplett |
| 85-94 | Svært bra | De fleste fakta korrekte, minor gaps |
| 75-84 | Bra | Hovedpoengene dekket, mangler noen detaljer |
| 60-74 | Akseptabel | Riktig retning men vesentlige mangler |
| 40-59 | Svak | Ufullstendig, viktige fakta mangler |
| 0-39 | Ikke bestått | Feil informasjon eller ikke besvart |

### Tier 3 tilleggskriterier

I tillegg til dual scoring sjekkes:
- Om `sharepoint_grounding_preview_call_output` finnes i response
- Dokumentspesifikk terminologi i svaret
- Om svaret inneholder detaljer utover instruksjonene

### Resultater-format

Hvert spørsmål lagres med begge scorer:
```json
{
  "id": "STAF-01",
  "kategori": "Kontakter",
  "sporsmal": "...",
  "forventet": "...",
  "svar": "...",
  "keyword_score": 85.5,
  "judge_scores": {
    "korrekthet": 9,
    "hallusinering": 1,
    "fullstendighet": 8,
    "formatering": 9,
    "nokkelord_treff": 4,
    "nokkelord_totalt": 5,
    "begrunnelse": "Alle nøkkelfakta korrekte, mangler kun telefonnummer."
  },
  "composite_score": 91.5,
  "latency_s": 12.3
}

## PDF-rapport

Generer kombinert rapport med reportlab:

**Filnavn:** `{ALIAS}_Komplett_Evalueringsrapport.pdf`

**Innhold:**
1. Forside med totalsnitt og tier-breakdown
2. Tier-oppsummeringer med søylediagram
3. Score-tabeller per tier (ID, kategori, score, vurdering)
4. Alle 33 detaljerte spørsmål/svar
5. Kompetanseanalyse (11 områder)
6. Anbefalinger (6 forbedringsforslag)
7. Konklusjon

**Viktig:** Bruk `clean_md()` for å strippe HTML-tags fra agentsvar:
```python
def clean_md(t):
    t = re.sub(r'<[^>]*>', ' ', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = t.replace('\n', '<br/>')
    return t
```

Og `safe_para()` for fallback ved parse-feil:
```python
def safe_para(text, style):
    try:
        return Paragraph(text, style)
    except Exception:
        plain = re.sub(r'<[^>]*>', ' ', text)
        plain = re.sub(r'\s+', ' ', plain).strip()[:1500]
        return Paragraph(plain, style)
```

Trunkér lange svar til 1200 tegn. Ikke bruk `KeepTogether` for Q&A-blokker.

## Presentere resultater

Oppsummer for brukeren:
1. **Totalsnitt** — "Agent scoret X/100 over 33 spørsmål"
2. **Tier-breakdown** — Tier 1: X, Tier 2: Y, Tier 3: Z
3. **Styrker** — 2-3 sterke områder
4. **Svakheter** — 1-2 forbedringsområder
5. **Anbefalinger** — konkrete tiltak

Hvis totalscore < 80%, foreslå spesifikke instruksjonsforbedringer og tilby å re-kjøre evalueringen.

## Referanseresultater

| Agent | Tier 1 | Tier 2 | Tier 3 | Total |
|-------|--------|--------|--------|-------|
| STAF v18 | 98.3 | 90.3 | 67.5 | 88.4 |
| Komplett | Referanse | Referanse | Referanse | Referanse |

## Filnavnkonvensjoner

| Type | Mønster |
|------|---------|
| Tier 1 script | `eval_{alias}_15.py` |
| Tier 2 script | `eval_{alias}_land_expand_10.py` |
| Tier 3 script | `eval_{alias}_sharepoint_verify.py` |
| Tier 1 resultater | `eval_{alias}_resultater.json` |
| Tier 2 resultater | `eval_{alias}_land_expand_resultater.json` |
| Tier 3 resultater | `eval_{alias}_sharepoint_verify_resultater.json` |
| PDF-rapport | `{ALIAS}_Komplett_Evalueringsrapport.pdf` |
