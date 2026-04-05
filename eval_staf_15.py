"""
STAF Evalueringssett – 15 spørsmål
Statsforvalterens fellestjenester (STAF) kundeagent evaluering
"""

import json, datetime
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint='https://kateecosystem-resource.cognitiveservices.azure.com/api/projects/kateecosystem',
)
oai = client.get_openai_client()

EVAL_SET = [
    # --- Kontakter og organisasjon ---
    {
        "id": "STAF-01",
        "kategori": "Kontakter",
        "sporsmal": "Hvem er direktør for Statsforvalterens fellestjenester, og hvem er Ateas account manager?",
        "forventet": "Direktør: Margot Telnes. Account Manager: Lasse Johnson.",
    },
    {
        "id": "STAF-02",
        "kategori": "Kontakter",
        "sporsmal": "Hvem har tatt over som avdelingsdirektør Infrastruktur og Drift hos STAF?",
        "forventet": "Espen Storetvedt (erstatter Eldar Hovda).",
    },
    {
        "id": "STAF-03",
        "kategori": "Kontakter",
        "sporsmal": "Hvem hos STAF godkjenner innkjøp under 1,3 MNOK, og hvem godkjenner over 1,3 MNOK?",
        "forventet": "Under 1,3 MNOK: Tommy Midtun Kjellby. Over 1,3 MNOK: Erik Drivdal.",
    },
    # --- Avtaler ---
    {
        "id": "STAF-04",
        "kategori": "Avtaler",
        "sporsmal": "Hva er verdien og varigheten på rammeavtalen for Microsoft-lisenser?",
        "forventet": "Verdi: 60 MNOK. Periode: januar 2024 – januar 2027 (3 år).",
    },
    {
        "id": "STAF-05",
        "kategori": "Avtaler",
        "sporsmal": "Hvilke rammeavtaler ble signert i 2025?",
        "forventet": "Tre avtaler: Konsulent Microsoft og AV (20.04.2025), Nettverk og Nettverkskonsulent (01.04.2025), AV Managed Services/CVI (21.10.2025).",
    },
    {
        "id": "STAF-06",
        "kategori": "Avtaler",
        "sporsmal": "Hva dekker tjenesteavtalen for Managed Video CVI?",
        "forventet": "Managed services for videokonferanseplattform (CVI), signert 21.10.2025.",
    },
    # --- Økonomi ---
    {
        "id": "STAF-07",
        "kategori": "Økonomi",
        "sporsmal": "Hva var total Atea-omsetning mot STAF i 2025, fordelt på kategorier?",
        "forventet": "Total: 28,2 MNOK. Software: 20 MNOK, Support: 1,2 MNOK, HW klient: 1,9 MNOK, HW AV: 0,4 MNOK, HW nettverk: 2,6 MNOK, Konsulenter: 1,9 MNOK.",
    },
    {
        "id": "STAF-08",
        "kategori": "Økonomi",
        "sporsmal": "Hvorfor falt omsetningen fra 2024 til 2025, og hva er prognosen for 2026?",
        "forventet": "Nedgang -32,7% hovedsakelig pga. hardware -74,5% (avsluttede leasingavtaler). Prognose 2026: 33,6 MNOK.",
    },
    # --- Prosjekter og initiativer ---
    {
        "id": "STAF-09",
        "kategori": "Prosjekter",
        "sporsmal": "Hva er FLAKS-programmet, og hvem leder det fra Atea?",
        "forventet": "Transformasjons-/moderniseringsprogram som vokste ut av TOM-arbeidet (startet des 2024). Programleder Atea: Even Ask.",
    },
    {
        "id": "STAF-10",
        "kategori": "Prosjekter",
        "sporsmal": "Hva er planene for datasenter og skyreise i 2026-2027?",
        "forventet": "HPE-datasenter utløper nov 2026. Elements flyttes til sky i 2026. Hybride driftsmodeller fra 2027. Nye datasenter/skyløsninger forberedes.",
    },
    {
        "id": "STAF-11",
        "kategori": "Prosjekter",
        "sporsmal": "Hvilke sikkerhetstiltak pågår hos STAF?",
        "forventet": "Sentinel-gjennomgang (med Martinius), CSPM og Defender Storage avventer Sentinel, Purview skal implementeres.",
    },
    # --- Strategi ---
    {
        "id": "STAF-12",
        "kategori": "Strategi",
        "sporsmal": "Hva er STAFs fem strategiske hovedmål i virksomhetsstrategien 2023-2026?",
        "forventet": "1) Kvalitet i samhandling, 2) Informasjonssikkerhet i alle tjenester, 3) Digitale løsninger med brukerne i sentrum, 4) Relevant kompetanse, 5) Bærekraft i drift.",
    },
    {
        "id": "STAF-13",
        "kategori": "Strategi",
        "sporsmal": "Hva er STAFs driftsbudsjett for 2026, og hva er de viktigste styringsparameterne?",
        "forventet": "Budsjett: 263,5 MNOK. Styringsparametre: brukertilfredshet ≥4,5, oppetid Elements 99,6%, brukerstøtte svar innen 2 timer 95%.",
    },
    # --- Hardware og livssyklus ---
    {
        "id": "STAF-14",
        "kategori": "Hardware",
        "sporsmal": "Hvilke hardware-avtaler utløper i 2026-2027?",
        "forventet": "HPE Datasenter nov 2026, DFØ AV-utstyr alle møterom okt 2026, MS Lisenser jan 2027, DFØ HP Klienter 1190 stk okt 2027.",
    },
    # --- Konsulenter ---
    {
        "id": "STAF-15",
        "kategori": "Konsulenter",
        "sporsmal": "Hvilke Atea-konsulenter er høyest vurdert hos STAF, og hva er deres styrker?",
        "forventet": "Andreas Aspeli (fleksibel, Hamar), Even Ask (programledelse, fremdrift), Jarle Nordby Johnsen (sky, Elements to Cloud).",
    },
]

print(f"STAF Evalueringssett – {len(EVAL_SET)} spørsmål")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: Statsforvalteren (v17)")
print("=" * 100)

results = []

for item in EVAL_SET:
    print(f"\n{'─'*100}")
    print(f"[{item['id']}] {item['kategori']}")
    print(f"Spørsmål: {item['sporsmal']}")
    print(f"Forventet: {item['forventet']}")
    print(f"{'─'*50}")

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

# Save results to JSON
outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_staf_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*100}")
print(f"Evaluering fullført. Resultater lagret i: {outfile}")
