---
name: agent-economics-review
description: Analyze per-Bedrock-agent costs, identify expensive agents, detect loops.
---

# Agent Economics Review

## Steps:
1. `get_agent_costs(hours=24)` — per-agent token usage
2. `detect_agent_loops(minutes=30)` — abnormal patterns
3. `get_metric_history(namespace='AWS/Bedrock', metric_name='Invocations', hours=24)` — trend
4. `get_cost_and_usage(days=2, service='Amazon Bedrock')` — dollar context

## Output format

Respond with a JSON object wrapped in ```json fences. No text before or after.

```json
{
  "type": "economics",
  "severity": "info|warning|critical",
  "summary": "X agents active, total $Y/day, [most expensive agent] is Z% of spend",
  "findings": [
    {"label": "Agent: [name/id]", "value": "$X/day (N invocations)", "status": "danger|warning|ok"},
    {"label": "Agent: [name/id]", "value": "$X/day (N invocations)", "status": "ok"},
    {"label": "Loop detection", "value": "None detected | ALERT: [agent] at N calls/5min", "status": "ok|danger"},
    {"label": "Total agent spend (24h)", "value": "$X", "status": "ok|warning|danger"},
    {"label": "Cost per query (avg)", "value": "$X", "status": "ok|warning"}
  ],
  "timeline": [
    {"time": "HH:MM", "event": "Peak: X invocations/hour"},
    {"time": "HH:MM", "event": "Current: X invocations/hour"}
  ],
  "actions": [
    {"label": "Switch to Haiku", "prompt": "What would costs be if I switched the most expensive agent to Haiku?", "destructive": false},
    {"label": "Stop expensive agent", "prompt": "Stop the most expensive agent", "destructive": true},
    {"label": "Set per-agent budget", "prompt": "Set budget alert at $50/month for Bedrock", "destructive": false}
  ],
  "blind_spots": "Only data you genuinely could NOT obtain in THIS run. If you used invocation-log or per-agent token data, logging is ENABLED — do not list it here or suggest enabling it."
}
```

## Rules:
- List agents ranked by cost (most expensive first)
- severity: critical if loop detected, warning if any agent >$10/day, info otherwise
- Report invocation logging as a blind_spot ONLY if your log/token queries returned no data (logging is actually off). If you successfully read per-agent token or log data, logging is ON — never mention enabling it.
