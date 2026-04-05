"""
KATE Agent Evaluation Report Generator
Generates HTML evaluation reports with scoring, analysis, and recommendations.

Usage:
    python generate_report.py --alias STAF --customer "Statsforvalteren" --agent-name "Statsforvalteren" \
        --base-results eval_staf_resultater.json \
        [--le-results eval_staf_land_expand_resultater.json] \
        [--sp-results eval_staf_sharepoint_verify_resultater.json] \
        [--compare eval_staf_v1_resultater.json]
"""

import json, datetime, argparse, re, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from score_answers import keyword_score, check_sharepoint_indicators, category_averages


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def score_badge(score: float) -> tuple[str, str, str]:
    """Returns (css_class, label, bar_class) for a score."""
    if score >= 80:
        return "score-high", "Utmerket", "bar-green"
    elif score >= 60:
        return "score-mid", "God", "bar-amber"
    else:
        return "score-low", "Trenger forbedring", "bar-red"


def render_eval_items(results: list[dict], show_score: bool = True) -> str:
    html = ""
    for item in results:
        # Use composite_score if available (from dual scoring), fall back to keyword_score or score
        composite = item.get("composite_score", item.get("score", 0))
        kw_score = item.get("keyword_score", item.get("score", 0))
        has_dual = "composite_score" in item and "keyword_score" in item

        badge_cls, _, bar_cls = score_badge(composite)
        answer_escaped = escape_html(item["svar"])
        expected_escaped = escape_html(item["forventet"])

        if show_score:
            if has_dual:
                score_html = f'<span class="score-badge {badge_cls}">{composite}/100</span> <span style="font-size:11px;color:#64748b">KW: {kw_score}%</span>'
            else:
                score_html = f'<span class="score-badge {badge_cls}">{composite}%</span>'
        else:
            score_html = f'<span class="score-badge score-high">{len(item["svar"])} tegn</span>'

        # Judge begrunnelse
        judge_html = ""
        judge_scores = item.get("judge_scores", {})
        if judge_scores.get("begrunnelse"):
            begrunnelse = escape_html(judge_scores["begrunnelse"])
            judge_html = f'<div style="margin-top:6px;font-size:12px;color:#475569;font-style:italic">Judge: {begrunnelse}</div>'

        sp_html = ""
        if "sharepoint_indikatorer" in item and item["sharepoint_indikatorer"]:
            indicators = ", ".join(item["sharepoint_indikatorer"])
            sp_html = f'<div style="margin-top:8px;font-size:12px;color:#16a34a">SharePoint-indikatorer: {indicators}</div>'

        html += f"""
  <div class="eval-item">
    <div class="eval-header">
      <div>
        <span class="eval-id">{item['id']}</span>
        <span class="eval-cat">{item['kategori']}</span>
      </div>
      {score_html}
    </div>
    <div class="eval-q">{escape_html(item['sporsmal'])}</div>
    <div class="eval-expected"><strong>Forventet:</strong> {expected_escaped}</div>
    {"<div class='bar'><div class='bar-fill " + bar_cls + "' style='width:" + str(min(composite, 100)) + "%'></div></div>" if show_score else ""}
    {judge_html}
    <details style="margin-top:10px">
      <summary style="cursor:pointer;color:#004080;font-weight:600">Vis agentens svar ({len(item['svar'])} tegn)</summary>
      <div class="eval-answer">{answer_escaped}</div>
    </details>
    {sp_html}
  </div>
"""
    return html


CSS = """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f7fa; color: #1a1a2e; line-height: 1.6; }
  .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
  header { background: linear-gradient(135deg, #002855 0%, #004080 100%); color: white; padding: 40px; border-radius: 12px; margin-bottom: 30px; }
  header h1 { font-size: 28px; margin-bottom: 8px; }
  header .subtitle { opacity: 0.85; font-size: 16px; }
  header .meta { margin-top: 20px; display: flex; gap: 30px; font-size: 14px; opacity: 0.8; flex-wrap: wrap; }
  .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 30px; }
  .card { background: white; border-radius: 10px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
  .card .value { font-size: 32px; font-weight: 700; color: #004080; }
  .card .label { font-size: 13px; color: #666; margin-top: 4px; }
  .card.green .value { color: #16a34a; }
  .card.amber .value { color: #d97706; }
  .card.red .value { color: #dc2626; }
  .section { background: white; border-radius: 10px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .section h2 { font-size: 20px; color: #002855; margin-bottom: 16px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
  .section h3 { font-size: 16px; color: #004080; margin: 16px 0 8px; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  th { background: #f1f5f9; text-align: left; padding: 10px 12px; font-weight: 600; font-size: 13px; color: #475569; }
  td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }
  tr:hover { background: #fafbfc; }
  .score-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .score-high { background: #dcfce7; color: #166534; }
  .score-mid { background: #fef3c7; color: #92400e; }
  .score-low { background: #fecaca; color: #991b1b; }
  .eval-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .eval-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .eval-id { font-weight: 700; color: #004080; font-size: 15px; }
  .eval-cat { font-size: 12px; color: #64748b; background: #f1f5f9; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
  .eval-q { font-weight: 600; margin-bottom: 8px; }
  .eval-expected { color: #64748b; font-size: 13px; margin-bottom: 8px; padding: 8px; background: #f8fafc; border-radius: 4px; }
  .eval-answer { font-size: 14px; white-space: pre-wrap; max-height: 400px; overflow-y: auto; padding: 12px; background: #f0fdf4; border-radius: 4px; border-left: 3px solid #16a34a; }
  .bar { height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
  .bar-green { background: #16a34a; }
  .bar-amber { background: #d97706; }
  .bar-red { background: #dc2626; }
  .verdict { font-size: 18px; font-weight: 700; padding: 16px; border-radius: 8px; text-align: center; margin: 20px 0; }
  .verdict.pass { background: #dcfce7; color: #166534; }
  .verdict.fail { background: #fecaca; color: #991b1b; }
  .tab-container { display: flex; gap: 4px; margin-bottom: -1px; position: relative; z-index: 1; }
  .tab { padding: 12px 24px; background: #e5e7eb; border-radius: 8px 8px 0 0; cursor: pointer; font-weight: 600; font-size: 14px; border: 1px solid #d1d5db; border-bottom: none; }
  .tab.active { background: white; border-color: #e5e7eb; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  ul.findings { list-style: none; padding: 0; }
  ul.findings li { padding: 10px 0 10px 24px; border-bottom: 1px solid #f1f5f9; position: relative; }
  ul.findings li:before { content: "\\2713"; position: absolute; left: 0; color: #16a34a; font-weight: bold; }
  ul.findings li.warn:before { content: "\\26A0"; color: #d97706; }
"""


def generate_report(alias, customer, agent_name, base_results, le_results=None, sp_results=None):
    """Generate the full HTML evaluation report."""
    now = datetime.datetime.now()

    # Score all results — use pre-scored data if available, otherwise keyword-score
    def ensure_scored(r):
        """Add keyword_score if not already present (backwards compat with old result files)."""
        if "composite_score" not in r and "keyword_score" not in r:
            kw = keyword_score(r["forventet"], r["svar"])
            r = {**r, "keyword_score": kw["score"], "composite_score": kw["score"]}
        elif "composite_score" not in r:
            r = {**r, "composite_score": r["keyword_score"]}
        return r

    base_scored = [ensure_scored(r) for r in base_results]

    le_scored = []
    if le_results:
        le_scored = [ensure_scored(r) for r in le_results]

    sp_scored = []
    if sp_results:
        for r in sp_results:
            r = ensure_scored(r)
            if "sharepoint_indikatorer" not in r:
                r["sharepoint_indikatorer"] = check_sharepoint_indicators(r["svar"])
            sp_scored.append(r)

    # Aggregates — use composite_score as primary
    all_scored = base_scored + le_scored + sp_scored
    avg_score = sum(s.get("composite_score", s.get("keyword_score", 0)) for s in all_scored) / len(all_scored) if all_scored else 0
    base_avg = sum(s.get("composite_score", s.get("keyword_score", 0)) for s in base_scored) / len(base_scored) if base_scored else 0
    base_cat_avgs = category_averages(base_scored, "composite_score")

    total_q = len(all_scored)
    passed = sum(1 for s in all_scored if s.get("composite_score", s.get("keyword_score", 0)) >= 60)
    verdict_pass = avg_score >= 70

    # Counts
    tier_counts = [f"Grunntest: {len(base_scored)} spm"]
    if le_scored:
        tier_counts.append(f"Land &amp; Expand: {len(le_scored)} spm")
    if sp_scored:
        tier_counts.append(f"SharePoint: {len(sp_scored)} spm")

    # Build tabs
    has_tabs = bool(le_scored or sp_scored)

    html = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<title>KATE {alias} Agent - Evalueringsrapport</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<header>
  <h1>KATE {alias} Agent — Evalueringsrapport</h1>
  <div class="subtitle">{customer} | Azure AI Foundry Agent Evaluering</div>
  <div class="meta">
    <span>Dato: {now.strftime('%d.%m.%Y %H:%M')}</span>
    <span>Agent: {agent_name}</span>
    <span>Antall sporsmal: {total_q}</span>
    <span>{' | '.join(tier_counts)}</span>
  </div>
</header>

<div class="summary-cards">
  <div class="card {'green' if avg_score >= 80 else 'amber' if avg_score >= 60 else 'red'}">
    <div class="value">{avg_score:.0f}%</div>
    <div class="label">Gjennomsnittlig score</div>
  </div>
  <div class="card green">
    <div class="value">{passed}/{total_q}</div>
    <div class="label">Bestatt (over 60%)</div>
  </div>
  <div class="card">
    <div class="value">{len(base_cat_avgs)}</div>
    <div class="label">Kategorier dekket</div>
  </div>
  <div class="card">
    <div class="value">{sum(len(r['svar']) for r in all_scored):,}</div>
    <div class="label">Tegn generert totalt</div>
  </div>
</div>

<div class="verdict {'pass' if verdict_pass else 'fail'}">
  {'BESTATT' if verdict_pass else 'IKKE BESTATT'} — Gjennomsnittlig score {avg_score:.0f}% pa tvers av {total_q} sporsmal
</div>
"""

    # Tabs if multiple tiers
    if has_tabs:
        html += '<div class="tab-container">\n'
        html += '  <div class="tab active" onclick="switchTab(\'base\')">Grunntest</div>\n'
        if le_scored:
            html += '  <div class="tab" onclick="switchTab(\'le\')">Land &amp; Expand</div>\n'
        if sp_scored:
            html += '  <div class="tab" onclick="switchTab(\'sp\')">SharePoint</div>\n'
        html += '</div>\n'

    # Base results section
    tab_cls = ' id="tab-base" class="tab-content active"' if has_tabs else ''
    html += f'<div{tab_cls}>\n'
    html += '<div class="section">\n  <h2>Score per kategori</h2>\n  <table>\n'
    html += '    <tr><th>Kategori</th><th>Antall</th><th>Gj.snitt score</th><th>Vurdering</th></tr>\n'

    categories = {}
    for s in base_scored:
        cat = s["kategori"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s.get("composite_score", s.get("keyword_score", 0)))

    for cat, scores in sorted(categories.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        avg = round(sum(scores) / len(scores), 1)
        badge_cls, label, _ = score_badge(avg)
        html += f'    <tr><td><strong>{cat}</strong></td><td>{len(scores)}</td><td><span class="score-badge {badge_cls}">{avg}%</span></td><td>{label}</td></tr>\n'

    html += '  </table>\n</div>\n'
    html += '<div class="section">\n  <h2>Detaljerte resultater — Grunntest</h2>\n'
    html += render_eval_items(base_scored)
    html += '</div>\n</div>\n'

    # Land & Expand tab
    if le_scored:
        html += '<div id="tab-le" class="tab-content">\n'
        html += '<div class="section">\n  <h2>Land &amp; Expand resultater</h2>\n'
        html += render_eval_items(le_scored)
        html += '</div>\n</div>\n'

    # SharePoint tab
    if sp_scored:
        sp_with = sum(1 for s in sp_scored if s.get("sharepoint_indikatorer"))
        html += '<div id="tab-sp" class="tab-content">\n'
        html += f'<div class="section">\n  <h2>SharePoint Grounding Verification</h2>\n'
        html += f'  <p style="margin-bottom:16px">Sporsmal med SharePoint-indikatorer: <strong>{sp_with}/{len(sp_scored)}</strong></p>\n'
        html += render_eval_items(sp_scored, show_score=True)
        html += '</div>\n</div>\n'

    # Tab switching script
    if has_tabs:
        html += """
<script>
function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}
</script>
"""

    html += '</div>\n</body>\n</html>'
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate KATE agent evaluation report")
    parser.add_argument("--alias", required=True, help="Customer alias (e.g., STAF)")
    parser.add_argument("--customer", required=True, help="Customer full name")
    parser.add_argument("--agent-name", required=True, help="Foundry agent name")
    parser.add_argument("--base-results", required=True, help="Path to base evaluation results JSON")
    parser.add_argument("--le-results", help="Path to Land & Expand results JSON")
    parser.add_argument("--sp-results", help="Path to SharePoint verification results JSON")
    parser.add_argument("--output", "-o", help="Output HTML path")
    args = parser.parse_args()

    with open(args.base_results, "r", encoding="utf-8") as f:
        base_results = json.load(f)

    le_results = None
    if args.le_results:
        with open(args.le_results, "r", encoding="utf-8") as f:
            le_results = json.load(f)

    sp_results = None
    if args.sp_results:
        with open(args.sp_results, "r", encoding="utf-8") as f:
            sp_results = json.load(f)

    html = generate_report(args.alias, args.customer, args.agent_name, base_results, le_results, sp_results)

    output_path = args.output or f"KATE_{args.alias}_Evalueringsrapport.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Rapport generert: {output_path}")


if __name__ == "__main__":
    main()
