"""
Komplett Evalueringssett – 15 spørsmål
Komplett Services AS kundeagent evaluering
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
    # --- Kontakter og organisasjon ---
    {
        "id": "KOMPLETT-01",
        "kategori": "Kontakter",
        "sporsmal": "Hvem er primærkontakten for IT hos Komplett, og hvem er Ateas senior account manager?",
        "forventet": "Primærkontakt IT: Henning Ims, Head of IT Operations (henning.ims@komplett.com, +47 48300800). Atea Senior Account Manager: Jørn Are Olsen (91111990).",
    },
    {
        "id": "KOMPLETT-02",
        "kategori": "Kontakter",
        "sporsmal": "Hvem er den nye workspace manageren hos Komplett, og når startet vedkommende?",
        "forventet": "Anders Gjengedal, startet uke 4 i februar 2026. Kom fra Eika Gruppen.",
    },
    {
        "id": "KOMPLETT-03",
        "kategori": "Kontakter",
        "sporsmal": "Hvem signerte SSA-D driftsavtalen på vegne av Komplett og Atea?",
        "forventet": "Komplett: Thomas Røkke (Group CFO). Atea: Borger Kruge (Regionsdirektør). Signert 28.06.2024 i Sandefjord.",
    },
    # --- Avtaler ---
    {
        "id": "KOMPLETT-04",
        "kategori": "Avtaler",
        "sporsmal": "Hva er detaljene for hovedkontrakten SSA-D med Komplett?",
        "forventet": "Avtalenr SA0132799. SSA-D 2018. Drift av IT-systemer og skytjenester. Signert 28.06.2024. Oppstart 01.07.2024. Varighet 5 år (utløper 01.07.2029). Oppsigelse 6 måneder.",
    },
    {
        "id": "KOMPLETT-05",
        "kategori": "Avtaler",
        "sporsmal": "Hva er vilkårene i CSP samarbeidsavtalen med Komplett?",
        "forventet": "Signert 10.04.2025 av Henning Ims og Eivind Sletthaug. Ingen bindingstid, 3 mnd oppsigelse. 10% av Azure-forbruk avsettes til prosjektfond. 2025: opptil 100% støtte. Etter 2025: opptil 50%. Atea Cloud Insights inkludert.",
    },
    {
        "id": "KOMPLETT-06",
        "kategori": "Avtaler",
        "sporsmal": "Beskriv NaaS-avtalen med Komplett – faser, tidslinje og omfang.",
        "forventet": "Avtalenr SA0029879. Fase 1 signert 22.04.2021. Fase 2 (2023): Sandefjord. Fase 3 (2023): Kontornett Sandefjord. 2025-utvidelse: MS250-svitsjer. ~285 Meraki-enheter. Månedlig kostnad ~NOK 260,000+.",
    },
    # --- Økonomi ---
    {
        "id": "KOMPLETT-07",
        "kategori": "Økonomi",
        "sporsmal": "Hva er den månedlige fakturaen til Komplett før og etter nedtrappingen?",
        "forventet": "Før nedtrapping (okt 2025): NOK 830,254/mnd (~9,96 MNOK/år). Månedlig reduksjon: ~NOK 342,321. Etter nedtrapping: ~NOK 500,000/mnd. Kreditering identifisert mars 2026: NOK 131,255.",
    },
    {
        "id": "KOMPLETT-08",
        "kategori": "Økonomi",
        "sporsmal": "Hvilke tjenester beholdes etter nedtrappingen, og hva koster de?",
        "forventet": "NaaS Meraki (~260K), Infrastruktur 2 servere/allflash (50K), VPN 473 brukere (52K), SDM 50% (31K), Backup 36TB (18K), Cloud Connect + ExpressRoute (27K), VM Atea DC 22 stk (14K), Catch & Dispatch (12.5K), Border Control (12K) m.fl.",
    },
    # --- Prosjekter og initiativer ---
    {
        "id": "KOMPLETT-09",
        "kategori": "Prosjekter",
        "sporsmal": "Hva er status på Entra ID-migreringen hos Komplett?",
        "forventet": "Delvis fullført. SHOWSTOPPER identifisert 31.10.2025: nåværende VPN-løsning støtter ikke Entra ID. Krever VPN-oppgradering eller alternativ før fullføring.",
    },
    {
        "id": "KOMPLETT-10",
        "kategori": "Prosjekter",
        "sporsmal": "Beskriv NIS2 compliance-prosjektet for Komplett.",
        "forventet": "Prosjektplan datert 11.09.2025. Scrum-basert, 9 sprinter planlagt. Strategisk rådgiver: Nils-Georg Paus. Bakgrunn: Modenhetsanalyse (2024), NIS2 Modenhetsrapport (2025), Gap-analyse vår 2025.",
    },
    {
        "id": "KOMPLETT-11",
        "kategori": "Prosjekter",
        "sporsmal": "Hva er situasjonen med nettverksinfrastrukturen hos Komplett?",
        "forventet": "MS125-svitsjer nær kapasitetsgrense, forårsaker ustabilitet i produksjon. Foreslått oppgradering til MS250 eller Meraki 9200-serie. Ny nettverksdesign med ekstern arkitekt planlagt. Spesielle behov: MAC-adressehåndtering, WiFi 6/7 i produksjon/retur.",
    },
    # --- Nedtrapping ---
    {
        "id": "KOMPLETT-12",
        "kategori": "Nedtrapping",
        "sporsmal": "Gi en oversikt over Endringsbilag 9 og nedtrappingsplanen for Komplett.",
        "forventet": "Datert 23.03.2026. Komplett insourcer (e-post Henning Ims 03.11.2025). Lokal ressurs Sandefjord terminert 31.01.2026. Azure VMs (69 stk), ServiceDesk, User Basic, Print avsluttes 30.04.2026. 12-mnd verdi: NOK 2,550,970. Avbestillingsgebyr frafalt.",
    },
    {
        "id": "KOMPLETT-13",
        "kategori": "Nedtrapping",
        "sporsmal": "Hvor mange servere skal dekommisjoneres, og hva er tidsplanen?",
        "forventet": "69 Azure-servere (55 Windows + 14 Linux). On-prem Sandefjord: 19+2 servere (avsluttet 31.01.2026). Azure VM-operasjoner avsluttes 30.04.2026. ~22 VMs i Atea Datasenter beholdes.",
    },
    # --- Kjente utfordringer ---
    {
        "id": "KOMPLETT-14",
        "kategori": "Utfordringer",
        "sporsmal": "Hva er de største utfordringene i Komplett-kontoen akkurat nå?",
        "forventet": "1) Omsetningsnedgang pga insourcing (830K→500K/mnd), 2) Fakturafeil NOK 131K kreditering, 3) VPN/Entra ID showstopper, 4) Printproblemer (IP-tap), 5) Nettverkskapasitet MS125-svitsjer, 6) Onboarding-feil, 7) 69 servere utfasing med ukjente avhengigheter.",
    },
    # --- Strategi og muligheter ---
    {
        "id": "KOMPLETT-15",
        "kategori": "Strategi",
        "sporsmal": "Hvilke vekstmuligheter finnes i Komplett-kontoen til tross for nedtrappingen?",
        "forventet": "NaaS-utvidelse (MS250/9200-svitsjer, arkitekt), NIS2-compliance, Entra ID (VPN-oppgradering), E5-lisensiering, CSP prosjektfond (10% Azure), Cloud Operations/Automation, SharePoint-migrering, DFV bestillingsløsning, KATE AI-agent (demonstrert mars 2026).",
    },
]

print(f"Komplett Evalueringssett – {len(EVAL_SET)} spørsmål")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: Komplett")
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
    results.append({
        "id": item["id"],
        "kategori": item["kategori"],
        "sporsmal": item["sporsmal"],
        "forventet": item["forventet"],
        "svar": answer,
    })

# Save results to JSON
outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_komplett_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*100}")
print(f"Evaluering fullført. Resultater lagret i: {outfile}")
