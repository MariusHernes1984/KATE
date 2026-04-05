# Evaluation Test Suite Pattern

Each customer agent gets an evaluation script that tests its knowledge across all key categories.

## File naming

`eval_{alias_lowercase}_{number_of_questions}.py`

Example: `eval_staf_15.py`, `eval_nmd_12.py`

## Structure

```python
"""
{ALIAS} Evalueringssett – {N} sporsmal
{Customer Name} kundeagent evaluering
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
    {
        "id": "{ALIAS}-01",
        "kategori": "Kontakter",
        "sporsmal": "Question in Norwegian",
        "forventet": "Expected answer summary",
    },
    # ... more questions
]

# Run evaluation
print(f"{ALIAS} Evalueringssett – {len(EVAL_SET)} sporsmal")
print(f"Tidspunkt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Agent: {AgentName}")
print("=" * 100)

results = []

for item in EVAL_SET:
    print(f"\n{'─'*100}")
    print(f"[{item['id']}] {item['kategori']}")
    print(f"Sporsmal: {item['sporsmal']}")
    print(f"Forventet: {item['forventet']}")
    print(f"{'─'*50}")

    conv = oai.conversations.create()
    oai.conversations.items.create(
        conversation_id=conv.id,
        items=[{"type": "message", "role": "user", "content": item["sporsmal"]}],
    )
    response = oai.responses.create(
        conversation=conv.id,
        extra_body={"agent_reference": {"name": "{AgentName}", "type": "agent_reference"}},
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

# Save results
outfile = f"eval_{alias}_resultater.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nEvaluering fullfort. Resultater lagret i: {outfile}")
```

## Question Categories

Every eval should cover these categories (where documents exist):

| Category | What to test | Min questions |
|----------|-------------|---------------|
| Kontakter | Key contacts at customer and Atea team | 2-3 |
| Avtaler | Agreement details, dates, values, scope | 2-3 |
| Okonomi | Revenue figures, trends, forecasts | 1-2 |
| Prosjekter | Ongoing initiatives, timelines, owners | 2-3 |
| Strategi | Strategic goals, KPIs, priorities | 1-2 |
| Hardware | Lifecycle dates, upcoming renewals | 1-2 |

## Guidelines

- Write questions in Norwegian (the agent should respond in Norwegian)
- Expected answers should be concise but specific (include actual numbers, dates, names)
- Questions should test both metadata recall and document search capability
- Include at least one question that requires the agent to search SharePoint (not just return metadata)
- Total: minimum 10, ideally 15 questions
