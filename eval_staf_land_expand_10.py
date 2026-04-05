"""
STAF Land & Expand Evalueringssett – 10 spørsmål
Tester agentens evne til å identifisere salgsmuligheter, lage account growth-planer,
forberede kundemøter og gi strategisk rådgivning for å utvide Atea-leveransen.
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
    # --- Identifisere muligheter ---
    {
        "id": "STAF-LE-01",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Jeg har et taktisk møte med STAF neste uke. Basert på pågående utfordringer og prosjekter — hva bør jeg ta opp som potensielle nye salgsinitiativ?",
        "forventet": "Bør nevne: 1) Datasenter-utløp HPE nov 2026 (ny plattform), 2) Skyreisen/Elements til sky 2026, 3) Nettverksfornyelse Fortinet, 4) AV-utskifting okt 2026, 5) Sentinel/Purview/CSPM sikkerhet, 6) Overvåkingsverktøy (tilbud ute), 7) AI/Copilot.",
    },
    {
        "id": "STAF-LE-02",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Atea har ikke datasenteret til STAF i dag. HPE-avtalen utløper november 2026. Hvordan kan vi posisjonere oss for å vinne dette?",
        "forventet": "Bør identifisere: Start arkitektur-workshop Q2/Q3 2026. Posisjonere hybrid sky (Azure + on-prem). Koble til Skyreisen/Elements. Bruke Even Ask og FLAKS-programmet som inngang. Kontaktpersoner: Espen Storetvedt, Eskil Notesjø. Estimert verdi 20-40 MNOK.",
    },
    {
        "id": "STAF-LE-03",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Hvilke avtaler hos STAF nærmer seg utløp eller har fornyelses-/utvidelsesmuligheter? Lag en tidslinje.",
        "forventet": "Tidslinje: Okt 2026 - DFØ AV-utstyr utløper. Nov 2026 - HPE Datasenter utløper. Jan 2027 - MS Lisenser utløper (60 MNOK). Okt 2027 - DFØ HP Klienter 1190 stk. Pågående: Fortinet-utskifting, konsulentrammeavtale 2025-2029 (20 MNOK).",
    },
    # --- Strategisk account planning ---
    {
        "id": "STAF-LE-04",
        "kategori": "Account planning",
        "sporsmal": "Lag en 12-måneders account growth plan for STAF med kvartalsvise milepæler og estimert revenue-potensial.",
        "forventet": "Strukturert plan: Q2 2026: Nettverksfornyelse + overvåking + Sentinel-oppfølging. Q3 2026: Datasenter-workshop + AV-planlegging + Purview. Q4 2026: Skymigrering Elements + AI/Copilot. Q1 2027: Ny datasenter/hybridplattform. Med NOK-estimater per initiativ.",
    },
    {
        "id": "STAF-LE-05",
        "kategori": "Account planning",
        "sporsmal": "Hvem hos STAF bør vi bygge sterkere relasjoner med for å utvide samarbeidet? Hvem er de viktigste beslutningstakerne?",
        "forventet": "Prioriterte: Espen Storetvedt (ny avd.dir, erstatter Eldar Hovda - MÅ bygge relasjon). Margot Telnes (direktør, dialog via Kim Sigurd Wennerberg). Erik Drivdal (godkjenner >1,3 MNOK). Tommy Midtun Kjellby (<1,3 MNOK, operasjonell). Jørgen Tistel (digitalisering, AI).",
    },
    # --- Cross-sell og upsell ---
    {
        "id": "STAF-LE-06",
        "kategori": "Cross-sell",
        "sporsmal": "STAF har Sentinel-gjennomgang pågående. Hva bør neste steg være, og hvilke tilleggstjenester kan vi selge inn?",
        "forventet": "Neste steg: Avvente Sentinel-konklusjoner, deretter foreslå helhetlig Microsoft Security roadmap. Tillegg: CSPM, Defender for Storage, Purview (informasjonsklassifisering), SOC-tjenester, sikkerhetsarkitektur for hybrid sky 2027. Koble til virksomhetsstrategi mål 2 (informasjonssikkerhet).",
    },
    {
        "id": "STAF-LE-07",
        "kategori": "Cross-sell",
        "sporsmal": "Kompetanseprogrammet del 1 var svært vellykket hos STAF. Hvordan kan vi utvide dette til et større engasjement?",
        "forventet": "Del 2 allerede planlagt mot 2027. Utvide med: sky-kompetanse (Azure), sikkerhetskompetanse, AI/Copilot governance, plattformdrift. Nøkkelperson Atea: Bård Erik Lund. Koble til STAFs strategimål 4 (relevant kompetanse). Potensial 1-3 MNOK.",
    },
    # --- Møteforberedelse ---
    {
        "id": "STAF-LE-08",
        "kategori": "Møteforberedelse",
        "sporsmal": "Forbered meg til et strategisk møte med Margot Telnes (direktør STAF). Hva bør jeg vite og hvilke budskap bør jeg ha med?",
        "forventet": "Margot er toppsjef STAF. Dialog via ledersponsor Kim Sigurd Wennerberg. Budskap: Atea som strategisk partner for skyreisen, datasenter 2027, og informasjonssikkerhet. Koble til virksomhetsstrategien 2023-2026. Nevn FLAKS-programmets suksess (Even Ask). Vis omsetningsutvikling og prognose 33,6 MNOK 2026. Vekstambisjoner.",
    },
    {
        "id": "STAF-LE-09",
        "kategori": "Møteforberedelse",
        "sporsmal": "Espen Storetvedt er ny avdelingsdirektør Infrastruktur og Drift. Hvordan bør vi bygge relasjonen, og hva bør første møte handle om?",
        "forventet": "Ny i rollen (erstatter Eldar Hovda). Eier: nettverk, datasenter, drift, sikkerhet. Første møte: presentere Atea-teamet, pågående leveranser (Fortinet, konsulenter), kommende utfordringer (datasenter nov 2026, skyreise). Spør om hans prioriteringer. Ta med Lasse Johnson (KAM) og relevante spesialister.",
    },
    # --- Risikohåndtering ---
    {
        "id": "STAF-LE-10",
        "kategori": "Risikohåndtering",
        "sporsmal": "Hva er de største risikoene for at vi mister omsetning hos STAF, og hva kan vi gjøre for å forhindre det?",
        "forventet": "Risiko: 1) MS Lisenser 60 MNOK utløper jan 2027 (konkurranse), 2) Datasenter-beslutning kan gå til annen leverandør, 3) Ny avd.dir Espen Storetvedt er ukjent relasjon, 4) Offentlig anbud kan gi andre fordeler, 5) Budsjettkutt (effektiviseringskrav i tildelingsbrev). Tiltak: Styrke relasjoner, leveranseeksellens, proaktiv rådgivning, synliggjøre verdi.",
    },
]

print(f"STAF Land & Expand Evalueringssett - {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: Statsforvalteren")
print("=" * 100)

results = []

for item in EVAL_SET:
    print(f"\n{'='*100}")
    print(f"[{item['id']}] {item['kategori']}")
    print(f"Sporsmal: {item['sporsmal']}")
    print(f"Forventet: {item['forventet']}")
    print(f"{'-'*50}")

    conv = oai.conversations.create()
    oai.conversations.items.create(
        conversation_id=conv.id,
        items=[{"type": "message", "role": "user", "content": item["sporsmal"]}],
    )
    response = oai.responses.create(
        conversation=conv.id,
        extra_body={"agent_reference": {"name": "Statsforvalteren", "type": "agent_reference"}},
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

outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_staf_land_expand_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*100}")
print(f"Land & Expand evaluering fullfort. Resultater lagret i: {outfile}")
