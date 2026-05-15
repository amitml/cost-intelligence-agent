# CostOp Intelligence Agent — Product Paper

**The Cost Investigation Agent for Amazon Bedrock Workloads**

**Date:** May 2026 · **Status:** Working Prototype · **GitHub:** github.com/amitml/cost-intelligence-agent

---

## Executive Summary

CostOp is an AI-powered cost investigation agent built on Amazon Bedrock AgentCore. It detects Bedrock token spikes in real-time, identifies which agent is responsible, correlates the spike with the deployment that caused it, and provides the exact command to stop the bleeding — all within 5 minutes of the incident starting.

It follows the same architectural pattern as AWS DevOps Agent: alarm fires → agent investigates autonomously → delivers root cause + fix. DevOps Agent does this for operational incidents. CostOp does it for cost incidents.

---

## The Problem

Organizations deploying Bedrock agents in production face a visibility gap:

| What They Have | What They Need |
|---|---|
| Cost Explorer: "Bedrock cost $300 today" | Which agent? Which prompt? Which deployment? |
| Cost Anomaly Detection: "Bedrock went up" (next day) | Real-time: "Agent X is looping NOW, burning $63/day" |
| CloudWatch: token metrics per minute | Correlation: "spike started 3 min after deploy by user Y" |
| Budgets: alert after overspend | Prevention: "throttle it before it costs more" |

No existing tool connects CloudWatch metrics + CloudTrail deployments + per-agent token attribution into a single investigation.

---

## How It Works

[**Screenshot: Architecture Diagram**]

```
DETECTION:
  CloudWatch Alarms (5-min evaluation)
    → EventBridge
      → Agent investigates autonomously

INVESTIGATION (Agent Skills):
  1. CloudWatch: real-time token rate, RPM, cost/hour
  2. CloudTrail: what changed, who deployed, which agent ARNs
  3. Invocation Logs: per-agent session IDs, caller identity
  4. Cost Explorer: today vs yesterday vs baseline comparison
  5. Pattern Memory: "seen this before — last time it was a loop"

RESPONSE:
  Structured report: What's happening, Who caused it, Cost impact, Fix command

ACTIONS:
  One-click: Stop agent | Set budget | Notify owner
```

---

## Key Capabilities

### 1. Per-Agent Cost Attribution

[**Screenshot: Investigation showing specific agent ARNs**]

Identifies which Bedrock agent is consuming tokens. Shows agent ARN, invocation count, token consumption, and estimated cost per agent. No other tool provides this level of granularity.

### 2. Real-Time Detection (5 minutes)

CloudWatch Alarms monitor InputTokenCount, OutputTokenCount, RPM, throttles, and TPM quota usage. When thresholds breach, the agent begins investigating immediately — not the next day.

### 3. Cross-Service Correlation

Connects the dots across services in one sentence:

> "UpdateFunctionCode by user MCP at 02:20 UTC changed the prompt in Lambda cost-intelligence-bridge, which triggered agent e92b6952 into a loop, causing 5.5M tokens in 8 hours."

### 4. Investigation Skills

Built on the Agent Skills specification. The agent follows a structured investigation playbook:
- Which tools to call and in what order
- What evidence to collect (ARNs, timestamps, session IDs)
- How to format the response (consistent, SRE-grade)
- When to escalate vs when to act

### 5. Pattern Memory

Stores investigation findings in DynamoDB. Next time a similar spike occurs, the agent recognizes the pattern and resolves faster. Institutional knowledge that doesn't leave when people do.

### 6. One-Click Remediation

Action buttons on every investigation:
- **Stop Agent** — throttle Lambda concurrency to 0
- **Set Budget** — create AWS Budget with alert threshold
- **Notify Owner** — send findings via email/SNS

Agent asks for confirmation before destructive actions.

---

## Slack Integration (When Enabled)

[**Screenshot: Slack alert concept**]

With a Slack app configured, the agent operates directly in Slack:

```
Agent posts to #cost-alerts:
  "⚠️ Bedrock tokens 10x normal. Agent e92b6952 looping.
   Burn rate: $5.33/hr. Deploy by MCP at 02:20 caused it.
   Reply to investigate or click [Throttle] to stop."

User replies: "What changed?"

Agent: "UpdateFunctionCode at 02:20 doubled the system prompt
       from 2K to 8K tokens. Per-query cost went from $0.08 to $0.34."
```

Full conversational investigation in-thread with memory.

---

## Architecture

| Component | Service | Purpose |
|---|---|---|
| Brain | AgentCore Runtime (Strands + Sonnet) | Investigation logic |
| Skills | Agent Skills spec (SKILL.md) | Investigation playbooks |
| Tools (14) | Strands @tool functions | CloudWatch, CloudTrail, invocation logs, actions |
| Cost Data (28 tools) | MCP via AgentCore Gateway | Cost Explorer, Budgets, Pricing |
| Memory | AgentCore Memory + DynamoDB | 30-day conversations + permanent patterns |
| Detection | CloudWatch Alarms (7) | Real-time spike detection |
| Trigger | EventBridge + Lambda (10 lines) | Alarm → agent |
| UI | Amplify (Vite + Cognito) | Web console with alerts + chat |
| Auth | Cognito → SigV4 | Direct browser-to-AgentCore (no timeout) |

---

## Cost to Operate

| Component | Monthly |
|---|---|
| AgentCore + Sonnet (~20 investigations/day) | $45-50 |
| Cost Explorer API | $7 |
| CloudWatch Alarms | $0.50 |
| DynamoDB, Lambda, EventBridge | Free tier |
| Amplify hosting | $1 |
| Invocation logging (recommended) | $1-8 |
| **Total** | **$55-65/month** |

**ROI:** One caught runaway agent saves $50-200/day. Pays for itself in the first incident.

---

## Comparison

| Capability | Cost Explorer | Cost Anomaly Detection | CloudWatch | CostOp |
|---|---|---|---|---|
| Per-agent attribution | ❌ | ❌ | ❌ | ✅ |
| Real-time detection | ❌ (12hr delay) | ❌ (24hr batch) | ✅ (metrics only) | ✅ (5 min) |
| Root cause correlation | ❌ | ❌ | ❌ | ✅ |
| Deployment correlation | ❌ | ❌ | ❌ | ✅ |
| Conversational investigation | ❌ | ❌ | ❌ | ✅ |
| Remediation commands | ❌ | ❌ | ❌ | ✅ |
| Pattern memory | ❌ | ❌ | ❌ | ✅ |
| Loop detection | ❌ | ❌ | ❌ | ✅ |

---

## What's Next

| Feature | Status | Timeline |
|---|---|---|
| Core investigation (CloudWatch + CloudTrail + CE) | ✅ Working | Done |
| Per-agent attribution | ✅ Working | Done |
| Web UI with alerts + chat | ✅ Working | Done |
| Action buttons (stop, budget, notify) | ✅ Working | Done |
| Pattern memory | ✅ Working | Done |
| Proactive alarm → investigation → email | ✅ Working | Done |
| Slack integration (full conversational) | 🔲 Ready to deploy | Needs app approval |
| Usage graphs (visual comparison) | 🔲 | Next sprint |
| Auto-remediation with guardrails | 🔲 | Next sprint |
| One-click deployment (CloudFormation) | 🔲 | Next sprint |
| MCP registry publication | 🔲 | Future |
| Multi-account (Organizations) | 🔲 | Future |

---

## Customer Pitch

> "DevOps Agent watches your infrastructure. CostOp watches your AI spend. Together, you've got operational coverage and cost coverage in one agentic layer."

> "Your Bedrock agents cost you $X/month. You don't know which one is expensive, which one is looping, or why costs spiked Tuesday. CostOp watches 24/7, catches spikes in 5 minutes, tells you exactly which agent and which deployment caused it, and stops the bleeding with one click."

---

## Try It

- **Web Console:** https://main.d21aywet1qkneb.amplifyapp.com
- **Login:** testuser / CostOp2026!
- **GitHub:** https://github.com/amitml/cost-intelligence-agent

---

*Built on: Amazon Bedrock AgentCore, Strands Agents SDK, Agent Skills specification, Claude Sonnet, CloudWatch, CloudTrail, Cost Explorer MCP*
