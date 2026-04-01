# KATE — Key Account Team Executor

Kundeagenter for Ateas store kunder, bygget på Azure AI Foundry.

## Arkitektur

```
Copilot Studio (Orkestrator)
        │
        ├── Bertel O Steen agent (Foundry + SharePoint)
        ├── Norsk Medisinaldepot agent
        ├── Sykehuspartner agent
        ├── Kitron agent
        ├── Deloitte agent
        ├── NAMMO agent
        ├── Olav Thon agent
        ├── Avarn agent
        ├── Jotun agent
        ├── Komplett agent
        ├── Statsforvalteren agent
        ├── Lerøy Seafood agent
        ├── Trøndelag Fylkeskommune agent
        ├── Bærum Kommune agent
        │
        ├── Saleshelper SAM (salg)
        ├── LEA (teknisk/lisensiering)
        ├── Atea Superoffice Agent (CRM)
        ├── Flowcase CV Agent
        └── Atea Value Advisor
```

## Mappestruktur

```
KATE/
├── agenter/                 # Kundeagent-konfigurasjoner (JSON)
│   ├── governance.json      # Felles regler for alle kundeagenter
│   ├── kundeagent-mal.json  # Mal for nye kundeagenter
│   └── bertel-o-steen.json  # Eksempel: BOS-agent
├── deploy/                  # Deploy-script og konfigurasjon
│   ├── deploy_agents.py
│   ├── deployed_agents.json
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## Ny kunde-agent

1. Kopier `agenter/kundeagent-mal.json` til `agenter/<kundenavn>.json`
2. Fyll inn kundenavn, alias, SharePoint-mappe og SuperOffice ID
3. Kjør `python deploy/deploy_agents.py --only <agent-navn>`
4. Legg til agenten som topic i Copilot Studio-orkestratoren

## Deploy

```bash
cd deploy
cp .env.example .env  # Fyll inn verdier
pip install -r requirements.txt
az login
python deploy_agents.py
```
