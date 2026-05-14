# Cost Intelligence Agent

Extends the [AWS FinOps Agent](https://github.com/aws-samples/sample-finops-agent-amazon-bedrock-agentcore) with proactive cost alerting, root cause correlation, and per-agent cost tracking.

## What's Added

| Extension | What It Does |
|---|---|
| `extensions/cloudtrail-tools/` | MCP server that correlates cost spikes with deployments and infrastructure changes |
| `extensions/proactive-watcher/` | Lambda triggered by CloudWatch Alarms + Cost Anomaly Detection → asks the agent to investigate → posts to Slack |
| `extensions/agent-economics/` | MCP server for per-Bedrock-agent cost tracking and loop detection |

## Architecture

```
BASE (from AWS sample):
  AgentCore Runtime (Strands + Claude Sonnet)
  ├── AgentCore Gateway
  │   ├── Billing MCP Server (Cost Explorer, Budgets, Compute Optimizer)
  │   └── Pricing MCP Server (Price List API)
  ├── AgentCore Memory (30-day conversation history)
  └── Amplify Frontend + Cognito Auth

EXTENSIONS (this repo adds):
  ├── CloudTrail MCP Server (what changed? who deployed?)
  ├── Agent Economics MCP Server (per-agent costs, loop detection)
  ├── CloudWatch Alarm → EventBridge → Proactive Watcher Lambda
  └── SNS → Slack/Email notifications
```

## Quick Start

### 1. Deploy the base FinOps agent

```bash
export ADMIN_EMAIL="your-email@company.com"
cd cdk && npm install && npm run build && npx cdk bootstrap && npx cdk deploy --all --require-approval never
```

### 2. Deploy extensions

```bash
# TODO: CDK stack for extensions (CloudWatch Alarm + EventBridge + Lambda + MCP runtimes)
cd extensions/
# Instructions coming soon
```

### 3. Enable Bedrock model invocation logging (for Agent Economics)

Console → Amazon Bedrock → Settings → Model invocation logging → Enable → CloudWatch Logs

## Two Modes

**Proactive** (agent alerts you):
```
CloudWatch detects spike → EventBridge → Lambda asks agent → Slack:
"⚠️ Bedrock invocations up 5x. Deployment by dev@co 30min ago.
 Similar to March 12 incident ($2,400). Projected burn: $67/day."
```

**Reactive** (you ask):
```
You: "Why are my costs up this week?"
Agent: "Bedrock up 340%. Driver: data-analyst-agent.
       Prompt change Tuesday added 6K tokens/query.
       Per-query cost: $0.34 now vs $0.08 before."
```

## Prerequisites

- AWS account with Bedrock, AgentCore, Cost Explorer access
- Node.js 18+, Python 3.13+, AWS CDK installed
- Bedrock model invocation logging enabled (for agent economics)
