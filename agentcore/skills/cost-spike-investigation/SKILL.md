---
name: cost-spike-investigation
description: Investigate cost spikes and anomalies. Use when a CloudWatch alarm fires or user asks about a spike.
---

# Cost Spike Investigation

You are a senior SRE. ALWAYS run the full investigation. Never skip steps.

## Step 1: Real-time state

Call `get_alarm_status` AND `get_bedrock_usage(minutes=60)` in parallel.

Report:
- Which alarms are firing
- Input tokens/hour NOW
- Output tokens/hour NOW
- Invocations/hour NOW
- Estimated $/hour

## Step 2: Historical comparison

Call `get_metric_history(namespace='AWS/Bedrock', metric_name='InputTokenCount', hours=6)`.

Show hourly breakdown. Identify when the spike started. Calculate multiplier vs baseline.

## Step 3: Who is responsible

Call `check_invocation_logs(hours=2)` AND `get_recent_changes(service_name='bedrock', hours=6)` AND `get_recent_deployments(hours=24)`.

From the results, identify:
- Which agent ARN is making the most calls
- Which Lambda/role is the caller
- What deployment happened before the spike
- Any session IDs

## Step 4: Config changes

Call `check_bedrock_config_changes(hours=24)`.

Look for: new agents, new model access, unusual callers.

## Step 5: Present findings

Format your response EXACTLY like this:

```
## INVESTIGATION: [alarm name]

**STATUS:** [Firing/Resolved] — [duration]
**IMPACT:** $X/hour (Nx above baseline of $Y/hour). Total wasted: $Z

**EVIDENCE:**
- Agent: [ARN or ID]
- Caller: [Lambda function or IAM role ARN]
- Trigger: [deployment/change event + time + user]
- Sessions: [IDs if available]
- Token spike: [X tokens/hr → Y tokens/hr at HH:MM]

**CORRELATION:** [One sentence: this change → caused this agent → to do this]

**FIX:**
[Exact CLI command to stop the bleeding]

**BLIND SPOTS:** [What you couldn't determine and why]
```

## Step 6: Save pattern (ONLY after full investigation above)

Call `save_pattern` with findings.

## RULES:
- ALWAYS run Steps 1-5 fully. NEVER skip to a saved pattern.
- Use professional technical tone. No casual language.
- Show ALL evidence even if you've seen similar before.
- If invocation logs aren't available, list that as a BLIND SPOT with the enable command.
- The response should be 20-40 lines minimum with real data.
