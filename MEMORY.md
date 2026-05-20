# CostOp Intelligence Agent — Project Memory

**Last updated:** 2026-05-20 15:07 PST
**Status:** Stack deleted. Project packaged and published.
**Repo:** https://github.com/amitml/cost-intelligence-agent
**ECR Public:** public.ecr.aws/y3a7j1y9/amitml/costop-agent:latest

---

## Current State

- **Stack `CostOp` deleted** from account 463440883924 (us-east-1)
- **GitHub repo** is the single source of truth — all old v1 files (CDK, extensions, MCP servers, old frontend) removed
- **GitHub Release v2** has `costop-ui.zip` attached
- **ECR Public image** synced and working
- **Template validated** and ready for any customer to deploy

---

## Template: cloudformation/costop-template.yaml

### Model Selection (updated 2026-05-20)
- **DefaultModel** dropdown: `Sonnet4.6` (default), `Sonnet4.5`, `Haiku4.5`
- **CustomModelId** parameter: override with any Bedrock model ID
- Note in docs: model must be enabled in customer's account/region via Bedrock console
- Logic: CustomModelId takes priority → else dropdown maps to:
  - Sonnet4.6 → `us.anthropic.claude-sonnet-4-6`
  - Sonnet4.5 → `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - Haiku4.5 → `us.anthropic.claude-haiku-4-5-20251001-v1:0`

### All Parameters (fully configurable)
```
AdminEmail (required)
DefaultModel: Sonnet4.6 | Sonnet4.5 | Haiku4.5
CustomModelId: (any Bedrock model ID, optional)
EnableTokenAlarm: Yes/No, TokenAlarmThreshold: 200000
EnableRPMAlarm: Yes/No, RPMAlarmThreshold: 100
EnableTPMAlarm: Yes/No, TPMAlarmThreshold: 80
EnableThrottleAlarm: Yes/No, ThrottleAlarmThreshold: 5
EnableErrorAlarm: Yes/No, ErrorAlarmThreshold: 10
MonthlyBudgetLimit: 100 (0=none)
EnableCostAnomalyDetection: Yes/No
EnableInvocationLogging: Yes/No
MemoryRetentionDays: 30 (7-365)
InvocationLogGroup: (existing or empty to create)
SNSTopicArn: (existing or empty to create)
CloudWatchAlarms: (empty to create, EXISTING to skip)
EnableSlack: Yes/No
SlackBotToken, SlackSigningSecret, SlackChannel
```

---

## Architecture
```
Web UI (Amplify) → Cognito Auth → AgentCore Runtime (11 tools)
                                        ↓
                    CloudWatch + CloudTrail + Cost Explorer + Invocation Logs
                                        ↓
                    Structured investigation → Email + Slack + DynamoDB

Proactive: Alarm/Budget/Anomaly → EventBridge → Bridge Lambda → Agent → SNS Email
Slack: @mention → API GW → SQS → Agent Integration Lambda → Block Kit response
```

---

## Key Files
- `cloudformation/costop-template.yaml` — one-click deployment (~900 lines)
- `agentcore/agent_runtime.py` — main runtime with system prompt
- `agentcore/tools.py` — 11 combined tools
- `agentcore/skills/cost-spike-investigation/SKILL.md` — hypothesis-driven skill
- `web/main.js` — UI with `window.COSTOP_CONFIG` support
- `web/index.html` — dark mode, login with forgot password
- `README.md` — customer-facing quick start
- `cloudformation/README.md` — full deployment guide

---

## Git History (recent)
- `4d7f813` — Add Sonnet 4.6 as default model, 3 model dropdown + custom override
- `0311df0` — Simplify custom model docs
- `171eda3` — Remove dead link to deleted PRODUCT_PAPER.md
- `569a8c9` — Simplify cost section
- `2f95f54` — Professional tone in README
- `9138249` — Update docs: all configurable parameters
- `7a54495` — Make all alarm thresholds configurable (TPM, Throttle, Error)

---

## No Active Deployment
Stack was deleted. To redeploy, customer runs:
```bash
curl -O https://raw.githubusercontent.com/amitml/cost-intelligence-agent/main/cloudformation/costop-template.yaml
aws cloudformation create-stack --stack-name CostOp \
  --template-body file://costop-template.yaml \
  --parameters ParameterKey=AdminEmail,ParameterValue=EMAIL \
  --capabilities CAPABILITY_NAMED_IAM --region us-east-1
```
