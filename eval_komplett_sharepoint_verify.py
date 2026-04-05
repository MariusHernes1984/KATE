"""
Komplett SharePoint Grounding Verification — 8 spørsmål
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
    # --- Fra Copilot Discovery & Mapping rapport ---
    {
        "id": "SP-01",
        "kategori": "Copilot Discovery",
        "sporsmal": "I Copilot Discovery & Mapping rapporten for Komplett — hvor mange brukere ble inkludert i pilotprogrammet for Copilot, og hva var hovedanbefalingen før bredere utrulling?",
        "forventet": "10 brukere i pilotprogrammet. Anbefaling: Før mer enn 10 brukere må anbefalingene i rapporten følges. Atea anbefaler 'Advise + Plan and Implement' steget. Bør også nevne behov for informasjonsarkitekt og Purview/sensitivity labels.",
        "kilde": "CoPilot/Komplett Microsoft Copilot for M365 Discovery and Mapping.pdf, side 11"
    },
    {
        "id": "SP-02",
        "kategori": "Copilot Discovery",
        "sporsmal": "Hva fant Atea om Kompletts DLP-policyer og Purview-konfigurasjon i Copilot Discovery-rapporten? Vær spesifikk om antall og status.",
        "forventet": "Komplett har kun 1 DLP-policy som ikke er oppdatert siden 2020. Purview har kun 2 DLP-regler. Ingen sensitivity labels er konfigurert. Bruker default MRM-policyer for Exchange som er utdaterte. Ufullstendig GDPR-rapport i Compliance Manager.",
        "kilde": "CoPilot/Komplett Microsoft Copilot for M365 Discovery and Mapping.pdf, side 7-10"
    },
    {
        "id": "SP-03",
        "kategori": "Copilot Discovery",
        "sporsmal": "Hvilke sensitivity labels ble foreslått for Komplett i Copilot Discovery-rapporten? List dem opp.",
        "forventet": "7 labels: Public, General Information, Internal Only, Confidential Internal (protected), User defined Confidential (protected), Sales Information (Pureview_Sales_Information@Komplett.no), HR Information (HRDepartment@komplett.no), Management Information (Management_Information@Komplett.no).",
        "kilde": "CoPilot/Komplett Microsoft Copilot for M365 Discovery and Mapping.pdf, side 13-14"
    },
    # --- Fra taktisk møte 26.03.26 ---
    {
        "id": "SP-04",
        "kategori": "Møtereferat",
        "sporsmal": "Hva ble diskutert om nettverksinfrastruktur i det taktiske møtet 26. mars 2026? Hva var de konkrete aksjonspunktene?",
        "forventet": "MS125-switcher har kapasitetsproblemer, nærmer seg/nådd kapasitetsgrense. Forslag: bytte til MS250 eller 9200-serien. Aksjonspunkter: 1) Sette opp møte med AS for topologi-gjennomgang og få inn arkitekt, 2) Bytte ut kritiske nettverkskomponenter, 3) Teste nye Meraki 9200 switcher, 4) Sjekke tilgjengelige switcher fra lager.",
        "kilde": "Taktiske møter/AI Oppsummeringer og Notater/Transkribering og Copilot sammendrag Taktisk 26.03.26 Komplett.docx"
    },
    {
        "id": "SP-05",
        "kategori": "Møtereferat",
        "sporsmal": "Hva ble sagt om fakturafeil i det siste taktiske møtet med Komplett? Hva var beløpet for kreditnota?",
        "forventet": "Feilfakturering knyttet til kategorisering av timepriser og roller. Konsulenttype og timepriser var ikke riktig i forhold til avtalt. Kreditnota på NOK 131,255. Fakturaer satt på vent skal ikke betales før aksept. Rapportering til CBN AIR i april.",
        "kilde": "Taktiske møter/AI Oppsummeringer og Notater/Transkribering og Copilot sammendrag Taktisk 26.03.26 Komplett.docx"
    },
    {
        "id": "SP-06",
        "kategori": "Møtereferat",
        "sporsmal": "Hvilke arrangementer ble det informert om i det taktiske møtet 26. mars 2026, og når er de?",
        "forventet": "Klientdagen i Sandefjord 22. april, Sikkerhetsdagen i Tønsberg 5. mai, Community-arrangementet i Kristiansand 24. september.",
        "kilde": "Taktiske møter/AI Oppsummeringer og Notater/Transkribering og Copilot sammendrag Taktisk 26.03.26 Komplett.docx"
    },
    # --- Fra NIS2 prosjektplan ---
    {
        "id": "SP-07",
        "kategori": "NIS2 Prosjektplan",
        "sporsmal": "Beskriv gjennomføringsmodellen for NIS2-prosjektet hos Komplett. Hvor mange sprinter har prosjektplanen, og hvilke NIS2-artikler dekkes?",
        "forventet": "Scrum-basert med 2-3 ukers sprinter. 9 sprinter totalt. Dekker NIS2 artikkel 20-23. Områder: Styring, kartlegging/klassifisering/risikohåndtering, leverandør/forsyningskjedesikkerhet, BCP/DR, opplæring/sikkerhetskultur, teknologiske tiltak (MFA, logging, kryptografi, sårbarhetshåndtering), hendelseshåndtering og NIS2-rapportering.",
        "kilde": "2025 Komplett/NIS2 - Prosjektplan og Bistandsbeskrivelse/Prosjektplan og Bistandsbeskrivelse - Komplett Services - NIS2 Compliance.docx"
    },
    # --- Fra NaaS dokumenter ---
    {
        "id": "SP-08",
        "kategori": "NaaS Detaljer",
        "sporsmal": "Hva var NaaS fase 2 for Komplett? Hvilken lokasjon gjaldt det, og finnes det en CDR (Coverage Design Report)?",
        "forventet": "Fase 2 gjaldt Sandefjord. Inkluderte SOW, priskalkyle. Fase 3 var kontornett Sandefjord med CDR dekningsrapport (10 MB). Meraki-inventar versjon 3-4. Investering fra 14.10.2022.",
        "kilde": "NaaS/2023 NaaS Sandefjord Fase 2 og Fase 3"
    },
]

print(f"Komplett SharePoint Grounding Verification — {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: komplett")
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
        extra_body={"agent_reference": {"name": "komplett", "type": "agent_reference"}},
        input="",
    )

    answer = ""
    for out in response.output:
        if out.type == "message":
            for block in out.content:
                if block.type == "output_text":
                    answer += block.text

    print(f"Svar:\n{answer}")

    # Check for SharePoint indicators
    sp_indicators = []
    lower_answer = answer.lower()
    if any(term in lower_answer for term in ["ifølge", "i følge", "i dokumentet", "i rapporten", "basert på", "fra sharepoint"]):
        sp_indicators.append("Refererer til dokument/kilde")
    if any(term in lower_answer for term in ["discovery", "mapping", "purview", "sensitivity label"]):
        sp_indicators.append("Copilot Discovery-spesifikk terminologi")
    if any(term in lower_answer for term in ["sprint", "scrum", "artikkel 20", "artikkel 23"]):
        sp_indicators.append("NIS2 prosjektplan-spesifikke detaljer")
    if any(term in lower_answer for term in ["klientdagen", "sikkerhetsdagen", "community", "22. april", "5. mai"]):
        sp_indicators.append("Møtereferat-spesifikke detaljer")
    if any(term in lower_answer for term in ["10 brukere", "10 ansatte", "pilotprogram"]):
        sp_indicators.append("Copilot pilot-detaljer (kun i dokument)")
    if any(term in lower_answer for term in ["dlp", "2020", "mrm", "compliance manager"]):
        sp_indicators.append("Purview/DLP-funn (kun i dokument)")

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
outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_komplett_sharepoint_verify_resultater.json"
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
    status = "✅ SP" if r["sharepoint_indikatorer"] else "❌ NO SP"
    print(f"  {r['id']}: {status} — {', '.join(r['sharepoint_indikatorer']) if r['sharepoint_indikatorer'] else 'Ingen SharePoint-spesifikk info funnet'}")
