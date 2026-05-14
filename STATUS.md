# Cost Intelligence Agent — Status

## What's Deployed & Working

| Component | Status | Details |
|---|---|---|
| AgentCore Runtime (brain) | ✅ Live | `finops_runtime-f25c6ZCRzH` |
| Billing MCP (Cost Explorer, Budgets) | ✅ Live | Via Gateway |
| Pricing MCP | ✅ Live | Via Gateway |
| AgentCore Memory (30-day) | ✅ Live | `finops_memory-wGlPmPF0v3` |
| AgentCore Gateway | ✅ Live | `finops-gateway-c6bkzwrmeg` |
| Amplify Web UI | ✅ Live | https://main.d21aywet1qkneb.amplifyapp.com |
| CloudWatch Alarms (5) | ✅ Live | InputTokens, OutputTokens, RPM, Throttles, TPM Quota |
| SNS Topic | ✅ Live | `cost-intelligence-alerts` |
| AWS Chatbot → Slack | ✅ Configured | Channel: `#cost-op-hackathon` |
| DynamoDB (pattern memory) | ✅ Created | Table: `cost_patterns` |
| GitHub Repo | ✅ Live | https://github.com/amitml/cost-intelligence-agent |

## What's Written But Not Yet Deployed

| Component | File | What's Needed |
|---|---|---|
| CloudWatch Realtime MCP | `extensions/cloudwatch-realtime/server.py` | Containerize + register in Gateway |
| CloudTrail MCP | `extensions/cloudtrail-tools/server.py` | Containerize + register in Gateway |
| Agent Economics MCP | `extensions/agent-economics/server.py` | Containerize + register in Gateway |
| Pattern Memory MCP | `extensions/pattern-memory/server.py` | Containerize + register in Gateway |
| Event Trigger Lambda | `extensions/event-trigger/handler.py` | Deploy Lambda + EventBridge rule |

## Current Flow (working now)

```
Customer → Amplify Web UI → AgentCore → MCP tools (Cost Explorer, Budgets, Pricing) → answer
CloudWatch Alarm → SNS → AWS Chatbot → Slack #cost-op-hackathon (raw alarm)
```

## Target Flow (once extensions deployed)

```
CloudWatch Alarm → EventBridge → Lambda (10-line pass-through) → AgentCore (brain)
    AgentCore investigates:
      ├── CloudWatch MCP: what's spiking?
      ├── CloudTrail MCP: what changed?
      ├── Cost Explorer MCP: how much?
      ├── Pattern Memory MCP: seen this before?
      └── Posts smart explanation → SNS → Chatbot → Slack

Customer replies in Slack → @aws command → Lambda → AgentCore (same session, has memory)
    AgentCore answers using same tools, remembers the investigation context
```

## Key ARNs & IDs

```
Account:          463440883924
Region:           us-east-1
AgentCore ARN:    arn:aws:bedrock-agentcore:us-east-1:463440883924:runtime/finops_runtime-f25c6ZCRzH
Gateway ARN:      arn:aws:bedrock-agentcore:us-east-1:463440883924:gateway/finops-gateway-c6bkzwrmeg
Memory ID:        finops_memory-wGlPmPF0v3
SNS Topic:        arn:aws:sns:us-east-1:463440883924:cost-intelligence-alerts
DynamoDB Table:   cost_patterns
Slack Channel:    C0B0BR1MCCW (#cost-op-hackathon)
Chatbot Config:   cost-op-hackathon_chatbot
Amplify App:      d21aywet1qkneb
Amplify URL:      https://main.d21aywet1qkneb.amplifyapp.com
User Pool ID:     us-east-1_xuxlokqEr
Client ID:        3g0912f70vs77d753jdnb7i1cm
Identity Pool:    us-east-1:24905ab4-2105-4f7a-88b6-4feeb223eaf3
```

## Next Steps

1. Verify Slack alert delivery (alarm triggered, waiting for Chatbot to post)
2. Deploy event-trigger Lambda + wire to EventBridge
3. Containerize + deploy extension MCP servers to Gateway
4. Test full loop: alarm → agent investigates → smart alert in Slack → customer replies
5. Later: Slack app approval for full conversational bot (no @aws prefix)
