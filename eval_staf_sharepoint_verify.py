"""
STAF SharePoint Grounding Verification — 8 spørsmål
Tester om agenten faktisk henter data fra SharePoint-dokumenter,
ikke bare fra instruksene. Hvert spørsmål krever informasjon som
KUN finnes i SharePoint-dokumentene, ikke i agentens instrukser.
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
    # --- Fra strategisk møte 19.01.2026 ---
    {
        "id": "STAF-SP-01",
        "kategori": "Strategisk mote",
        "sporsmal": "I det strategiske møtet 19. januar 2026 med STAF — hva ble diskutert om markedstrender, og hvilke temaer ble presentert?",
        "forventet": "Markedstrender: prisøkninger og lengre leveringstider, CIO Analytics, ressurser, fokusområder, sikkerhet, AI (to slides dedikert). Atea Norge i tall: 23 kontorer, 1850 ansatte, 9 strategiske partnere, 9 Gold partnere.",
        "kilde": "Dokumentasjon/Presentasjoner/Strategiske møter/STAF Strategisk møte 19.01.2026.pptx"
    },
    # --- Fra taktisk møte 05.03.2026 ---
    {
        "id": "STAF-SP-02",
        "kategori": "Taktisk mote",
        "sporsmal": "Hva ble tatt opp i det taktiske møtet 5. mars 2026 med STAF? Hva var fokusområdene?",
        "forventet": "Fokus på: prisøkninger/lengre leveringstider, ressurser, AI. FLAKS-programmet i praksis. Feedback fra STAF etterspurt. Samme kundeteam og rammeavtaler som strategisk møte.",
        "kilde": "Dokumentasjon/Presentasjoner/Taktiske møter/2026/STAF Taktisk møte 05.03.2026.pptx"
    },
    # --- Fra virksomhetsstrategien (detaljnivå) ---
    {
        "id": "STAF-SP-03",
        "kategori": "Strategi detaljer",
        "sporsmal": "Hva sier STAFs virksomhetsstrategi 2023-2026 om STAFs tre roller? Beskriv dem i detalj.",
        "forventet": "Tre roller: 1) Tjenesteleverandør — stabile, sikre, effektive fellestjenester. 2) Rådgiver og veileder — kompetansebygging, opplæring, veiledning. 3) Pådriver og utviklingsaktør — ny teknologi, standardisering, digital transformasjon.",
        "kilde": "Dokumentasjon/Tildelingsbrev for STAF/2026/stafs-virksomhetsstrategi-2023---2026.pdf"
    },
    # --- Fra tildelingsbrevet (detaljnivå) ---
    {
        "id": "STAF-SP-04",
        "kategori": "Tildelingsbrev detaljer",
        "sporsmal": "Hva er de prioriterte utviklingsprosjektene i tildelingsbrevet 2026 for STAF? List alle med prioritet og bevilgning.",
        "forventet": "Prioritet 1: Digital gravferdsmelding (13,5 MNOK), Nytt felles fagsystem for tilsyn (TBD), Felles tilskuddsforvaltningssystem (4 MNOK), Enklere saksbehandlingsprosesser (1,5 MNOK). Prioritet 2: Rettshjelpsapplikasjon 2.0, Ny partiportal v2.0 (3,4 MNOK), Oppfølging Balanseprosjektet (3 MNOK). Prioritet 3: Digital løsning tros-/livssynssamfunn, Kommunebilde (1 MNOK).",
        "kilde": "Dokumentasjon/Tildelingsbrev for STAF/2026/tildelingsbrev-2026-til-statsforvaltarens-fellestenester-2.pdf"
    },
    # --- Fra rammeavtale-dokumenter ---
    {
        "id": "STAF-SP-05",
        "kategori": "Avtaledokumenter",
        "sporsmal": "Hva inneholder den signerte rammeavtalen for konsulentbistand IKT fra april 2025? Hvem signerte?",
        "forventet": "Signert rammeavtale konsulentbistand IKT, signert 22.04.2025. Detaljer fra selve avtaledokumentet. Bør søke i SharePoint for å hente faktisk innhold fra PDF-en i Avtaler og kontrakter/Rammeavtale Konsulent Microsoft og AV 20.04.2025/.",
        "kilde": "Avtaler og kontrakter/Rammeavtale Konsulent Microsoft og AV 20.04.2025/Signering av rammeavtale konsulentbistand IKT - signert 22.04.2025.pdf"
    },
    # --- Fra SSE presentasjon ---
    {
        "id": "STAF-SP-06",
        "kategori": "SSE Presentasjon",
        "sporsmal": "Hva inneholdt SSE-presentasjonen for STAF i 2024? Hva er SSE i denne konteksten?",
        "forventet": "SSE 2024_STAF.pptx fra mappen Dokumentasjon/Presentasjoner/2024/SSE med Mikael og Hanne/. Bør søke i SharePoint for å finne faktisk innhold. SSE = Strategic Sales Executive eller lignende salgsformat.",
        "kilde": "Dokumentasjon/Presentasjoner/2024/SSE med Mikael og Hanne/SSE 2024_STAF.pptx"
    },
    # --- Fra tilbudsmapper ---
    {
        "id": "STAF-SP-07",
        "kategori": "Tilbudshistorikk",
        "sporsmal": "Atea sendte et tilbud om 'Get Ready 4 Copilot' til STAF i 2024. Hva inneholdt dette tilbudet, og hvilke faser var det?",
        "forventet": "Tre faser i tilbudsmappen: Get Ready 4 Copilot - Fase 1, Get Ready 4 Copilot - Fase 2, Get Ready for CoPilot - Learn and Decide. Bør søke i SharePoint for å finne detaljer om innholdet i tilbudet.",
        "kilde": "Tilbud/2024/Get Ready 4 Copilot - Fase 1, Fase 2, Learn and Decide"
    },
    # --- Fra Workbook ---
    {
        "id": "STAF-SP-08",
        "kategori": "Workbook",
        "sporsmal": "Hva sier Statsforvalteren Workbook fra 2021 om STAFs IT-modenhet og planlagte initiativer den gangen?",
        "forventet": "IT-modenhet vurdert som 'veldig grå' (umoden). 2021-initiativer: Datasenterflytt fra Leikanger til Oslo, datasenteroppgradering Oslo og Hamar, Splunk-implementering, infrastruktur nettverksoppgradering, O365 samhandling, Azure og hybrid sky-utforskning.",
        "kilde": "Dokumentasjon/Workbook/Statsforvalteren Workbook 11.08.2021.docx"
    },
]

print(f"STAF SharePoint Grounding Verification — {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: Statsforvalteren")
print(f"Formaal: Verifisere at agenten henter data fra SharePoint, ikke bare instrukser")
print("=" * 100)

results = []

for item in EVAL_SET:
    print(f"\n{'='*100}")
    print(f"[{item['id']}] {item['kategori']}")
    print(f"Sporsmal: {item['sporsmal']}")
    print(f"Forventet (fra {item['kilde']}): {item['forventet']}")
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
    sp_used = False
    for out in response.output:
        if out.type == "message":
            for block in out.content:
                if block.type == "output_text":
                    answer += block.text
        elif out.type == "sharepoint_grounding_preview_call_output":
            sp_used = True

    print(f"Svar:\n{answer}")

    # Check for SharePoint indicators
    sp_indicators = []
    lower_answer = answer.lower()
    if sp_used:
        sp_indicators.append("SharePoint grounding tool brukt")
    if any(term in lower_answer for term in ["ifolge", "i folge", "i dokumentet", "i rapporten", "i presentasjonen", "fra sharepoint"]):
        sp_indicators.append("Refererer til dokument/kilde")
    if any(term in lower_answer for term in ["strategisk mote 19", "taktisk mote 05", "taktisk mote 5"]):
        sp_indicators.append("Mote-spesifikke detaljer")
    if any(term in lower_answer for term in ["gravferdsmelding", "partiportal", "rettshjelp", "tilsynskalenderen", "balanseprosjektet"]):
        sp_indicators.append("Tildelingsbrev utviklingsprosjekt-detaljer")
    if any(term in lower_answer for term in ["get ready", "copilot", "fase 1", "fase 2", "learn and decide"]):
        sp_indicators.append("Copilot tilbuds-detaljer")
    if any(term in lower_answer for term in ["splunk", "leikanger", "veldig gra", "umoden"]):
        sp_indicators.append("Workbook 2021-spesifikke detaljer")
    if any(term in lower_answer for term in ["22.04.2025", "signering av rammeavtale"]):
        sp_indicators.append("Avtaledokument-spesifikke detaljer")

    results.append({
        "id": item["id"],
        "kategori": item["kategori"],
        "sporsmal": item["sporsmal"],
        "forventet": item["forventet"],
        "kilde": item["kilde"],
        "svar": answer,
        "sharepoint_indikatorer": sp_indicators,
        "tegn": len(answer),
    })

    print(f"\nSharePoint-indikatorer funnet: {sp_indicators if sp_indicators else 'INGEN'}")

# Save results
outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_staf_sharepoint_verify_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Summary
print(f"\n{'='*100}")
print(f"SHAREPOINT GROUNDING VERIFICATION — OPPSUMMERING")
print(f"{'='*100}")
total_with_sp = sum(1 for r in results if r["sharepoint_indikatorer"])
total_without_sp = sum(1 for r in results if not r["sharepoint_indikatorer"])
print(f"Sporsmal med SharePoint-indikatorer: {total_with_sp}/{len(results)}")
print(f"Sporsmal UTEN SharePoint-indikatorer: {total_without_sp}/{len(results)}")
print(f"Resultater lagret i: {outfile}")

for r in results:
    status = "OK SP" if r["sharepoint_indikatorer"] else "NO SP"
    print(f"  {r['id']}: {status} — {', '.join(r['sharepoint_indikatorer']) if r['sharepoint_indikatorer'] else 'Ingen SharePoint-spesifikk info funnet'}")
