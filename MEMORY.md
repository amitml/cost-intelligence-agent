# CostOp Intelligence Agent — Project Memory

**Last updated:** 2026-05-17 15:11 PST
**Runtime version:** v57
**Status:** ✅ Deployed and operational
**Repo:** https://github.com/amitml/cost-intelligence-agent
**ECR Public:** public.ecr.aws/y3a7j1y9/costop-agent (repo created, image NOT pushed yet — Docker not running)

---

## NEXT SESSION: One-Click CloudFormation Package

### DONE ✅:
- ECR Public image pushed: `public.ecr.aws/y3a7j1y9/costop-agent:latest` and `:v57`
- CloudFormation template written and validates: `cloudformation/costop-template.yaml`
- Template includes: Cognito, AgentCore Runtime, DynamoDB (3 tables), CloudWatch Alarms (5, conditional), EventBridge (3 rules), Bridge Lambda (inline), Budget (conditional), Invocation Logging (conditional), SNS, IAM roles
- Web UI noted as separate deployment (needs stack outputs for config)

### What's left:
1. **Test deploy** in a clean account (or same account with different stack name)
2. **Web UI packaging** — either include Amplify in template or document as separate step
3. **Slack integration** — conditional resources (API GW + Lambdas) if EnableSlack=Yes
4. **README** for the template (parameter descriptions, deployment guide)

### Template Parameters:
```yaml
AdminEmail (required)
DefaultModel: Sonnet|Haiku
EnableTokenAlarm: Yes/No (threshold)
EnableRPMAlarm: Yes/No (threshold)
EnableTPMAlarm: Yes/No
EnableThrottleAlarm: Yes/No
EnableErrorAlarm: Yes/No
MonthlyBudgetLimit: $0-999 (0=none)
BudgetAlertThreshold: 80%
EnableCostAnomalyDetection: Yes/No
PermissionLevel: ReadOnly|Targeted
EnableInvocationLogging: Yes/No
EnableSlack: Yes/No
SlackBotToken (NoEcho, conditional)
SlackSigningSecret (NoEcho, conditional)
SlackChannel (conditional)
RemovalPolicy: Delete|Retain
```

---

## Current Runtime: v57

### Architecture:
```
Web UI (Amplify) → SigV4 → AgentCore Runtime (v57)
                              ├── 22+ local Strands tools (smart summaries)
                              ├── AgentCore Memory (30-day)
                              ├── DynamoDB (patterns, investigations, topology)
                              └── Sonnet 4.5 / Haiku 4.5 (user choice)

Proactive: CloudWatch Alarm → EventBridge → bridge Lambda → AgentCore → Slack + SNS
           Budget breach → EventBridge → bridge Lambda → AgentCore → Slack + SNS
           Cost Anomaly → EventBridge → bridge Lambda → AgentCore → Slack + SNS
           (5-min dedup + self-alarm filter)

Slack: @mention → API GW → SQS FIFO → agent-integration Lambda → AgentCore → Block Kit
       Button clicks → Interactivity → verification Lambda → SQS → agent processes
```

### Key Changes in v57 (from v41):
- **Tool response optimization**: check_invocation_logs returns smart summary (~1500-2000 tokens) with detail='full' option. get_recent_changes capped to 10 events, params truncated. get_cost_and_usage returns top 20 by cost.
- **Evidence ledger**: in investigation skill, prevents contradictions
- **Topology tool**: check_topology verifies resource connections before claiming correlation
- **Auto-save investigations**: server-side, any response with findings saves to DynamoDB
- **Structured system prompt**: TOOLS → CONSTRAINTS → WORKFLOW → OUTPUT sections
- **Skill loader**: returns empty for non-cost queries (prevents "who are you" triggering investigation)
- **No emojis**: instruction added to system prompt
- **max_tokens=16384**: prevents MaxTokensReachedException on complex queries
- **Flexible UI renderer**: handles different field names (label/name/title, value/description/detail)
- **Slack interactivity**: verification Lambda handles URL-encoded block_actions payloads
- **Slack agent-integration**: extracts `result` field from AgentCore JSON response, formats as Block Kit

### System Prompt (v57):
```
You are a Cost Intelligence Agent. You investigate cost anomalies in real-time.

## TOOLS (11 listed as priority guidance)
## CONSTRAINTS (billingMcp delay, no CLI, confirmations, consistency rule)
## WORKFLOW (6 steps)
## OUTPUT (tiles for data, plain text for simple, no emojis)
```

### Investigation Skill (injected on keyword match):
```
## PROTOCOL (assess → hypothesize → test → attribute → conclude)
## EVIDENCE LEDGER (CONFIRMED/ELIMINATED/UNRESOLVED)
## TOOLS (parallel first pass + targeted)
## OUTPUT (JSON schema: type, severity, summary, findings[], timeline[], actions[], blind_spots)
## RULES (4-8 tiles, multiplier vs baseline, use partial data)
```

---

## What Works Well:
- ✅ Evidence ledger prevents contradictions (~90%)
- ✅ Topology tool prevents false correlations
- ✅ Smart tool summaries keep context focused
- ✅ Auto-save investigations to DynamoDB
- ✅ Self-alarm filter in bridge Lambda
- ✅ Slack Block Kit with buttons (interactivity wired)
- ✅ Dark mode, mobile responsive, tree structure in left panel
- ✅ Model selector (Sonnet/Haiku)
- ✅ Stop button during generation
- ✅ Copy button on responses
- ✅ Budget + Cost Anomaly alerts in left panel + EventBridge triggers

## Known Limitations (accepted):
- Follow-up responses use tiles ~80% of the time (model judgment, no fix without architecture change)
- Model occasionally doesn't call get_service_quotas when it should (20% failure rate on "use all available tools")
- Streaming not implemented (WebSocket handler code exists but browser SigV4 auth is the blocker)
- Structured output (Bedrock constrained decoding) doesn't work with multi-tool agentic workflows
- Opus unified prompt approach produced worse results than skill-based approach

## Experiments Tried & Reverted:
- Opus unified prompt (v54) — model lost output schema, used generic field names
- Strands structured_output_model (v45) — model filled only summary, lost findings
- Server-side JSON wrapping — broke UI with huge escaped JSON
- "When in doubt, tiles" — made simple questions use tiles unnecessarily
- Cost widget (CloudWatch) — XML parsing issues, removed

---

## Key Resources:
| Resource | Value |
|---|---|
| Runtime | arn:aws:bedrock-agentcore:us-east-1:463440883924:runtime/finops_runtime-f25c6ZCRzH |
| Gateway | finops-gateway-c6bkzwrmeg |
| Memory | finops_memory-wGlPmPF0v3 |
| Web UI | https://main.d21aywet1qkneb.amplifyapp.com |
| Login | testuser / CostOp2026! |
| Slack Channel | C0B45LQETJ5 |
| ECR Private | 463440883924.dkr.ecr.us-east-1.amazonaws.com/finops-agent-runtime |
| ECR Public | public.ecr.aws/y3a7j1y9/costop-agent (empty) |
| ECR Stable | finops-agent-runtime:v18-stable |
| DynamoDB | cost_patterns, cost_investigations, cost_topology |
| SNS | arn:aws:sns:us-east-1:463440883924:cost-intelligence-alerts |
| Account | 463440883924 |
| Region | us-east-1 |
| API GW (Slack) | https://ceknhlppe0.execute-api.us-east-1.amazonaws.com/prod/slack-events |

---

## Rollback:
```bash
# Agent to stable:
aws bedrock-agentcore-control update-agent-runtime --agent-runtime-id finops_runtime-f25c6ZCRzH \
  --agent-runtime-artifact '{"containerConfiguration":{"containerUri":"463440883924.dkr.ecr.us-east-1.amazonaws.com/finops-agent-runtime:v18-stable"}}' \
  --role-arn "arn:aws:iam::463440883924:role/FinOpsAgentRuntimeStack-RuntimeRole" \
  --network-configuration '{"networkMode":"PUBLIC"}' --region us-east-1

# UI to early working version:
aws amplify start-job --app-id d21aywet1qkneb --branch-name main --job-type RETRY --job-id 25 --region us-east-1
```

---

## Session Stats (May 16-17):
- Runtime versions: v18 → v57 (39 deployments in 2 days)
- UI deployments: 60+
- Bedrock spend: ~$25-30 (mostly self-investigation loop)
- Key discovery: agent was investigating its own token usage recursively
- Opus consultations: 3 (prompt structure, tool optimization, unified prompt)
