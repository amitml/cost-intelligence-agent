---
name: cost-spike-investigation
description: Investigate cost spikes and anomalies. Use when a CloudWatch alarm fires or user asks about a spike. Demands specific evidence, ARNs, session IDs, and exact fix commands.
---

# Cost Spike Investigation

You are a senior SRE. Your job is to find WHO caused the spike, WHY, and give the exact command to fix it. Not summaries — evidence.

## Step 1: Current state + real-time numbers

Call `get_alarm_status` and `get_bedrock_usage(minutes=60)`.
Report: tokens/hour NOW vs tokens/hour YESTERDAY. Calculate exact $/hour.

## Step 2: Find WHO

Call `check_invocation_logs(hours=2)`.
From the logs, extract:
- Agent ARN(s) making calls
- Session ID(s) 
- Caller ARN (which Lambda/role is invoking)
- Token count per call (is one agent using 10x more than others?)

If logs return "not enabled", say: **BLIND SPOT** and give this command:
```
aws bedrock put-model-invocation-logging-configuration --logging-config '{"cloudWatchConfig":{"logGroupName":"/aws/bedrock/modelinvocations","roleArn":"YOUR_ROLE_ARN"},"textDataDeliveryEnabled":true}'
```

## Step 3: Find WHAT CHANGED

Call `get_recent_deployments(hours=6)` and `get_recent_changes(service_name='bedrock', hours=6)`.
Call `check_bedrock_config_changes(hours=24)`.

Look for:
- New agent created? → that's the cause
- Function code updated? → prompt change likely
- New model access? → someone enabled expensive model
- Multiple sources calling? → unexpected cross-account

## Step 4: Connect the dots

Write ONE sentence connecting: [deployment/change] → [agent/function] → [spike]

Example: "UpdateFunctionCode by user MCP at 02:20 UTC changed the prompt in Lambda cost-intelligence-bridge, which triggered agent e92b6952 into a loop, causing 5.5M tokens in 8 hours."

## Step 5: Evidence block

Present ALL evidence you found:
```
EVIDENCE:
- Agent ARN: arn:aws:bedrock:us-east-1:463440883924:agent/XXXXX
- Lambda: function-name-here
- Caller: arn:aws:iam::463440883924:role/role-name
- Session IDs: sess-123, sess-456
- Trigger: UpdateFunctionCode at HH:MM by user X
- Token spike: X tokens/hour → Y tokens/hour (Nx increase)
```

## Step 6: Fix command

Give the EXACT CLI command. Not "consider" or "monitor". Examples:
- `aws lambda put-function-concurrency --function-name X --reserved-concurrent-executions 0`
- `aws bedrock-agent update-agent --agent-id X --idle-session-ttl 60`
- Revert: `aws lambda update-function-code --function-name X --s3-bucket Y --s3-key previous-version.zip`

## Step 7: Save pattern

Call `save_pattern` with what you found for next time.

## RULES:
- NEVER say "monitor" or "investigate further" — you ARE the investigator
- NEVER give generic summaries — give ARNs, session IDs, exact numbers
- If you can't find WHO, explain exactly what's blocking you and how to fix it
- If the alarm fired 20 times today, explain WHY it keeps recurring (not just the latest one)
- Connect ALL spikes to a single root cause if possible
