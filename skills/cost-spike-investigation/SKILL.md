---
name: cost-spike-investigation
description: Investigate cost spikes and anomalies in real-time. Use when a CloudWatch alarm fires, when a user reports unexpected costs, or when asked to investigate why costs increased. Covers Bedrock token spikes, Lambda invocation surges, and general service cost anomalies.
---

# Cost Spike Investigation

Use this skill when investigating any cost anomaly, spike, or alarm.

## Step 1: Check real-time status

Call `get_alarm_status` to see what CloudWatch alarms are currently firing.
Call `get_bedrock_usage(minutes=60)` to get current token counts and invocations.

Report: which alarms are in ALARM state, current token burn rate, estimated cost/hour.

## Step 2: Get metric history

Call `get_metric_history(namespace='AWS/Bedrock', metric_name='InputTokenCount', hours=6)` to see the trend.

Compare current hour to previous hours. Calculate the multiplier (e.g., "4x normal").

## Step 3: Identify what changed

Call `get_recent_deployments(hours=24)` to find code changes.
Call `get_recent_changes(service_name='bedrock', hours=6)` for Bedrock-specific API activity.

Correlate: did a deployment happen shortly before the spike started?

## Step 4: Check for known patterns

Call `find_similar_patterns(pattern_type='bedrock-token-spike')` to see if we've seen this before.

If a pattern matches, reference the previous root cause and resolution.

## Step 5: Get dollar context

Only NOW use `billingMcp___cost-explorer` to get the dollar amount for context.
Compare today's cost to yesterday and last week.

## Step 6: Determine root cause and recommend action

Based on findings, provide:
1. **Root cause** — what specifically is causing the spike (which resource, what change)
2. **Cost impact** — current burn rate and projected daily/weekly cost if unchecked
3. **Recommended actions** (ranked by urgency):
   - Immediate: throttle, revert, or cap (stop the bleeding)
   - Short-term: fix the underlying issue
   - Long-term: add monitoring/guardrails to prevent recurrence

## Step 7: Save pattern

If this is a new pattern, call `save_pattern` with the type, root cause, resolution, and cost impact for future reference.

## Remediation options to suggest

- **Throttle Lambda concurrency**: Reduce concurrent executions to limit invocations
- **Add Bedrock token budget**: Set max_tokens on model calls
- **Revert deployment**: If a recent deploy caused it, suggest rollback
- **Add CloudWatch alarm**: If no alarm existed for this metric, suggest creating one
- **Set AWS Budget alert**: If no budget exists, suggest creating one at current spend + 20%

## Actions you can take (ask user permission first)

- `send_notification` — Alert the agent owner with your findings
- `stop_agent_invocations(function_name, 0)` — Stop a runaway Lambda (CAUTION: affects production)
- `set_budget_alert(monthly_limit)` — Create a budget to prevent future overspend
- `check_invocation_logs` — Get detailed per-call logs if logging is enabled

IMPORTANT: Before taking any destructive action (stop_agent_invocations), explain what it will do and ask the user to confirm.
