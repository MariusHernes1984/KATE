"""
Komplett Land & Expand Evalueringssett – 10 spørsmål
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
        "id": "LE-01",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Jeg har et taktisk møte med Komplett neste uke. Basert på pågående utfordringer og prosjekter — hva bør jeg ta opp som potensielle nye salgsinitiativ?",
        "forventet": "Bør nevne: 1) Nettverksoppgradering MS125→MS250/9200 (kapasitetsproblemer i produksjon), 2) VPN-løsning for Entra ID showstopper, 3) NIS2 utvidelse etter gap-analyse, 4) Copilot rollout etter forprosjekt, 5) E5 lisensstrategi (4 MNOK besparingsmål), 6) CSP prosjektfondmuligheter.",
    },
    {
        "id": "LE-02",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Komplett insourcer mye av driften. Hva kan vi tilby i stedet for å kompensere for omsetningsnedgangen? Gi meg en konkret plan med estimater.",
        "forventet": "Bør identifisere skift fra MRR til prosjekt/konsulent. Konkrete muligheter: nettverksoppgradering (HW + prosjekt), VPN/Zero Trust, NIS2 implementering, Copilot, lisensrådgivning, Azure governance, sikkerhetstjenester (MDR/XDR). Bør inkludere estimater og tidsrammer.",
    },
    {
        "id": "LE-03",
        "kategori": "Identifisere muligheter",
        "sporsmal": "Hvilke avtaler hos Komplett nærmer seg utløp eller har opsjonsmuligheter vi bør utnytte? Lag en tidslinje.",
        "forventet": "SSA-D løper til 01.07.2029. NaaS har pågående utvidelser. CSP samarbeidsavtale har ingen binding (3 mnd oppsigelse - må sikres). Bør identifisere at NaaS er strategisk viktigst å forsvare. Meraki-utstyr har livssyklus. Cisco Support Agreement (2020-2021) er utgått.",
    },
    # --- Strategisk account planning ---
    {
        "id": "LE-04",
        "kategori": "Account planning",
        "sporsmal": "Lag en 12-måneders account growth plan for Komplett med kvartalsvise milepæler og estimert revenue-potensial.",
        "forventet": "Bør lage strukturert plan. Q2 2026: Nettverksoppgradering (akutt kapasitetsproblem), VPN-løsning. Q3: NIS2 implementeringsfase, Copilot rollout. Q4: Lisensfornyelse strategi. Q1 2027: Ny nettverksarkitektur. Med NOK-estimater per initiativ.",
    },
    {
        "id": "LE-05",
        "kategori": "Account planning",
        "sporsmal": "Hvem hos Komplett bør vi bygge relasjoner med for å utvide samarbeidet? Hvilke stakeholders mangler vi kontakt med?",
        "forventet": "Eksisterende: Henning Ims (IT Ops), Anders Gjengedal (Workspace, ny). Mangler: ny CEO (bakgrunn olje/gass), ny CFO (Thomas Røkke erstatning). Bør adressere at Thomas Pedersen som signerte kontrakten har sluttet. Ledersponsor Børge Wilhelmsen bør aktiveres mot nye ledere.",
    },
    # --- Cross-sell og upsell ---
    {
        "id": "LE-06",
        "kategori": "Cross-sell",
        "sporsmal": "Komplett har et Copilot forprosjekt som er signert. Hva bør neste steg være, og hvilke tilleggstjenester kan vi selge inn i forbindelse med dette?",
        "forventet": "Copilot rollout etter Discovery & Mapping. Tillegg: Purview Information Protection (allerede tilbudt), Data governance/klassifisering, Change management/adopsjon, E5 lisensoppgradering (Copilot krever E3 minimum). CSP prosjektfond kan finansiere deler.",
    },
    {
        "id": "LE-07",
        "kategori": "Cross-sell",
        "sporsmal": "Komplett har SOC+ fra oss allerede. Med NIS2-kravene som kommer, hva kan vi selge inn av ekstra sikkerhetstjenester?",
        "forventet": "MDR/XDR utvidelse, Identity Threat Detection, Attack surface management, CSPM i Azure, Incident response retainer, Sikkerhetsopplæring/awareness, Leverandørstyring (NIS2 krav). Bør koble til NIS2-prosjektets funn fra gap-analyse.",
    },
    # --- Møteforberedelse ---
    {
        "id": "LE-08",
        "kategori": "Møteforberedelse",
        "sporsmal": "Forbered meg til et strategisk møte med den nye CEO-en hos Komplett. Hva bør jeg vite og hvilke budskap bør jeg ha med?",
        "forventet": "Ny CEO fra olje/gass sektoren (startet mars 2026). Komplett går godt (bunnlinje 200 MNOK). Atea leverer kritisk nettverksinfrastruktur. Budskap: strategisk partner (ikke bare leverandør), NIS2 compliance, digital transformasjon, kostnadseffektivitet. Bør ha med Børge Wilhelmsen.",
    },
    {
        "id": "LE-09",
        "kategori": "Møteforberedelse",
        "sporsmal": "Vi skal ha kvartalsmøte om CSP samarbeidsavtalen. Hva bør vi presentere for å maksimere bruken av prosjektfondet?",
        "forventet": "Vise opptjente prosjektmidler (10% av Azure-forbruk). Foreslå prosjekter: Azure governance, sikkerhet (Sentinel/Defender), Copilot forberedelser, cloud optimalisering. Maks 50% støtte etter 2025. Midler utløper etter 6 måneder. Bør ha konkrete prosjektforslag klare.",
    },
    # --- Risikohåndtering ---
    {
        "id": "LE-10",
        "kategori": "Risikohåndtering",
        "sporsmal": "Hva er de største risikoene for at vi mister mer omsetning hos Komplett, og hva kan vi gjøre for å forhindre det?",
        "forventet": "Risiko: 1) NaaS kan insources (største gjenværende ~260K/mnd), 2) CSP-avtale har 3 mnd oppsigelse, 3) Ny CEO ukjent holdning til Atea, 4) Fakturafeil undergraver tillit, 5) Konkurrenter kan tilby bedre nettverk. Tiltak: styrke relasjoner, leveranseeksellens, proaktiv rådgivning, løse fakturaproblemene raskt.",
    },
]

print(f"Komplett Land & Expand Evalueringssett - {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: komplett")
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
outfile = r"C:\Users\marherne\.claude\projects\C--Users-marherne--claude-projects-KATE\eval_komplett_land_expand_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*100}")
print(f"Land & Expand evaluering fullfort. Resultater lagret i: {outfile}")
