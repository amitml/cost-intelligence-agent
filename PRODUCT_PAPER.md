# CostOp Intelligence Agent — Product Paper

**An open-source cost investigation agent for Amazon Bedrock workloads**

**Date:** May 14, 2026 · **Authors:** Amit L · **Repo:** github.com/amitml/cost-intelligence-agent

---

## 1. What We Built

A self-hosted AI agent that monitors Bedrock token usage in real-time, investigates cost spikes autonomously, identifies which agent/deployment caused them, and provides one-click remediation. Deploys in a customer's own AWS account.

This is NOT a managed service. It's an open-source solution built on AgentCore, Strands, and the Agent Skills specification that any team can deploy and extend.

---

## 2. The Problem

Customers running Bedrock agents in production have no tool that answers:

- **Which** agent is expensive? (Cost Explorer shows service-level only)
- **Why** did costs spike at 2 AM? (Cost Anomaly Detection tells you next day)
- **What** deployment caused it? (No tool correlates cost with CloudTrail)
- **How** do I stop it NOW? (No tool gives actionable fix commands)

A single recursive agent loop can burn $50-200/day before anyone notices.

---

## 3. How It Works

### Detection (Real-Time)

7 CloudWatch Alarms monitor Bedrock metrics every 5 minutes:
- InputTokenCount (token spike)
- OutputTokenCount (generation spike)
- Invocations (RPM — loop detection)
- InvocationThrottles (hitting limits)
- EstimatedTPMQuotaUsage (approaching quota)
- InvocationClientErrors (wasted retries)

When any alarm fires → EventBridge → Lambda (10 lines) → Agent investigates.

### Investigation (Agent Skills)

The agent follows a structured investigation skill (Agent Skills spec):

1. **get_bedrock_usage** — real-time token rate and $/hour
2. **get_metric_history** — hourly trend, identifies when spike started
3. **get_recent_changes** — CloudTrail across bedrock + bedrock-runtime + bedrock-agentcore
4. **check_invocation_logs** — per-agent ARNs, session IDs, callers (requires logging enabled)
5. **billingMcp (Cost Explorer)** — today vs yesterday vs 2 days ago comparison

4-5 tool calls per investigation. ~$0.39 per investigation with Sonnet.

### Response

Structured report with:
- Current status + cost/hour
- Agent ARNs responsible
- Deployment/change that triggered it
- Cost comparison table
- Exact CLI fix command

### Actions

One-click buttons:
- **Notify** — sends findings to owner via SNS email
- **Budget** — creates AWS Budget with alert threshold
- **Stop** — throttles Lambda concurrency to halt runaway agent

---

## 4. Architecture

```
┌──────────────────────────────────────────────────┐
│ Web Console (Amplify)                             │
│ • Login (Cognito)                                 │
│ • Live alerts (CloudWatch API direct)             │
│ • Alarm history by date (expandable tree)         │
│ • Chat with agent (SigV4 direct to AgentCore)     │
│ • Action buttons                                  │
└───────────────────────┬──────────────────────────┘
                        │ No Lambda, no timeout
                        ▼
┌──────────────────────────────────────────────────┐
│ AgentCore Runtime                                 │
│ • Strands Agent + Claude Sonnet (max_tokens=8192) │
│ • Agent Skills (investigation playbooks)          │
│ • 14 Strands tools (CloudWatch, CloudTrail, etc.) │
│ • 28 MCP tools via Gateway (Cost Explorer, etc.)  │
│ • AgentCore Memory (30-day conversations)         │
│ • DynamoDB (pattern memory)                       │
└───────────────────────┬──────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
  CloudWatch       CloudTrail     Cost Explorer
  (real-time)      (who/what)     ($ amounts)

PROACTIVE PATH:
  CloudWatch Alarm → EventBridge → Lambda (10 lines) → AgentCore
```

---

## 5. Slack Integration (Future — Requires App Approval)

Once a Slack app is approved, the web console becomes optional:

```
Alarm fires → Agent investigates → Posts to Slack channel:
  "⚠️ Agent e92b6952 looping. $5.33/hr burn. Deploy by MCP at 02:20.
   Reply to dig deeper or click [Throttle] to stop."

User replies in thread → Agent responds with full context.
```

Architecture: AgentCore → Slack (via AWS published pattern: github.com/aws-samples/sample-Integrating-Amazon-Bedrock-AgentCore-with-Slack)

No web UI needed. Agent lives in Slack. Full conversational investigation in-thread with memory.

---

## 6. Cost Model

### Cost to Run (Customer Pays)

| Component | Monthly Cost | Notes |
|---|---|---|
| Bedrock Sonnet (investigations) | $45-50 | ~$0.39/investigation × 20/day |
| Cost Explorer API | $7 | $0.01/call × 720 calls |
| CloudWatch Alarms (7) | $0.70 | $0.10/alarm |
| AgentCore Runtime | Included | Pay-per-invocation |
| DynamoDB | Free tier | Pattern memory |
| Lambda | Free tier | 10-line bridge |
| EventBridge | Free | Alarm routing |
| Amplify | $1 | Static hosting |
| Cognito | Free tier | Auth |
| Invocation logging (optional) | $1-8 | CloudWatch Logs ingestion |
| **Total** | **$55-65/month** | |

### Cost Per Investigation (Breakdown)

| Item | Tokens | Cost |
|---|---|---|
| System prompt + skill | ~3,000 input | $0.009 |
| 28 MCP tool definitions | ~8,000 input | $0.024 |
| Tool results (4-5 calls) | ~4,000 input | $0.012 |
| Agent reasoning | ~2,000 input | $0.006 |
| Response output | ~1,500 output | $0.023 |
| **Total per investigation** | **~18,500 tokens** | **~$0.07-0.39** |

*Range depends on how many tools the agent calls (3 for simple, 5 for complex).*

### If Switched to Haiku

| | Sonnet | Haiku | Savings |
|---|---|---|---|
| Per investigation | $0.39 | $0.03 | 92% |
| Monthly (20/day) | $234 | $18 | $216 |

Haiku is sufficient for structured investigations (following skill steps). Sonnet recommended for complex reasoning and remediation planning.

### ROI

| Scenario | Without CostOp | With CostOp | Savings |
|---|---|---|---|
| Runaway agent (6 hours undetected) | $378 wasted | Caught in 5 min ($5 wasted) | $373 |
| Engineer time to investigate | 2-3 hours ($200-300) | 60 seconds (agent does it) | $200+ |
| Monthly (2 incidents) | $1,000+ wasted | $55 agent cost | 18x ROI |

---

## 7. What's Working Today

| Feature | Status |
|---|---|
| Real-time detection (7 CloudWatch alarms) | ✅ |
| Autonomous investigation (skills + tools) | ✅ |
| Per-agent ARN attribution | ✅ |
| Cross-service correlation (CloudWatch + CloudTrail + CE) | ✅ |
| Web console with live alerts + history | ✅ |
| Conversational follow-ups with memory | ✅ |
| Action buttons (notify, stop, budget) | ✅ |
| Pattern memory (learns from incidents) | ✅ |
| Proactive alarm → investigation → email | ✅ |
| Config change detection (new agents, models) | ✅ |

---

## 8. What's Not Built Yet

| Feature | Effort | Impact |
|---|---|---|
| Slack integration (full conversational) | 1 day (needs app approval) | Eliminates web UI dependency |
| Usage graphs (visual trend comparison) | 1 day | Better visualization |
| Auto-remediation with guardrails | 2 days | Hands-free cost protection |
| One-click deployment (CloudFormation) | 1 day | Customer self-service |
| MCP registry publication | 1 day | Reusable by other agents |
| Multi-account (Organizations) | 3 days | Enterprise scale |
| Predictive alerts (deploy → cost forecast) | 1 week | Prevention vs reaction |

---

## 9. Comparison with Existing Tools

| | Cost Explorer | Cost Anomaly Detection | CloudWatch | Datadog Cost | **CostOp** |
|---|---|---|---|---|---|
| Per-agent attribution | ❌ | ❌ | ❌ | ❌ | ✅ |
| Detection speed | 12hr delay | 24hr batch | Real-time (metrics only) | Hourly | **5 min + investigation** |
| Root cause | ❌ | Service-level | ❌ | Basic | **Agent ARN + deployment + correlation** |
| Conversational | ❌ | ❌ | ❌ | ❌ | ✅ |
| Remediation | ❌ | ❌ | ❌ | ❌ | **One-click + CLI commands** |
| Loop detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pattern memory | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cost | Free | Free | Free | $$$$ | **$55-65/mo** |

---

## 10. Technical Details

### Tools (14 Strands + 28 MCP)

**Strands (custom, in-agent):**
- get_alarm_status, get_bedrock_usage, get_metric_history
- get_recent_changes, get_recent_deployments
- get_agent_costs, detect_agent_loops
- check_invocation_logs, check_bedrock_config_changes
- save_pattern, find_similar_patterns
- send_notification, stop_agent_invocations, set_budget_alert

**MCP (via AgentCore Gateway):**
- 28 tools from AWS Labs Billing + Pricing MCP servers
- Cost Explorer, Budgets, Compute Optimizer, Free Tier, Pricing API

### Skills (Agent Skills Specification)

- `cost-spike-investigation` — structured investigation playbook
- `agent-economics-review` — per-agent cost analysis
- `cost-overview` — general cost questions

Skills control tool ordering and output format. Agent follows the playbook for investigations, responds freely for follow-up questions.

### Stack

- Runtime: Amazon Bedrock AgentCore
- Framework: Strands Agents SDK (Python)
- Model: Claude Sonnet 4.5 (configurable)
- Memory: AgentCore Memory (30-day) + DynamoDB (permanent patterns)
- Auth: Amazon Cognito
- Hosting: AWS Amplify
- Detection: CloudWatch Alarms + EventBridge
- Data: Cost Explorer MCP, CloudWatch API, CloudTrail API

---

## 11. How to Deploy (Current State)

```bash
git clone https://github.com/amitml/cost-intelligence-agent
cd cost-intelligence-agent/cdk
export ADMIN_EMAIL="your@email.com"
npm install && npx cdk deploy --all
```

Deploys: AgentCore runtime, Gateway, MCP servers, Cognito, Amplify, Memory.

Then manually: create CloudWatch alarms, EventBridge rule, Lambda bridge.

**Future:** Single CloudFormation template that does everything including alarms and thresholds.

---

## 12. Live Demo

- **Console:** https://main.d21aywet1qkneb.amplifyapp.com
- **Login:** testuser / CostOp2026!
- **GitHub:** https://github.com/amitml/cost-intelligence-agent

[**Screenshot: Alert panel with tree structure**]

[**Screenshot: Investigation response with ARNs and fix commands**]

[**Screenshot: Action buttons — Notify, Budget, Stop**]

[**Screenshot: Follow-up conversation with memory**]

---

*Built with: Amazon Bedrock AgentCore, Strands Agents SDK, Agent Skills spec, AWS Labs MCP servers, Claude Sonnet 4.5*


---

## 13. PRFAQ — Working Backwards

### Press Release (Internal)

**CostOp Intelligence Agent — The first AI agent that investigates your other AI agents' costs**

Teams running Bedrock agents in production have no visibility into per-agent costs. Cost Explorer shows a single line item. Cost Anomaly Detection flags it a day later. By then, a looping agent has wasted hundreds of dollars.

CostOp is a self-hosted investigation agent that detects Bedrock cost spikes in 5 minutes, identifies the specific agent ARN and deployment responsible, and provides the exact command to stop it. It follows the same pattern as AWS DevOps Agent — alarm fires, agent investigates, delivers root cause + fix — but for cost incidents instead of operational incidents.

**What it does today:**
- Detects token/RPM spikes via CloudWatch Alarms (5-minute evaluation)
- Investigates autonomously: correlates CloudWatch + CloudTrail + Cost Explorer
- Identifies specific agent ARNs causing the spike
- Shows cost impact ($/hour now vs baseline, today vs yesterday)
- Provides exact CLI fix commands
- One-click actions: stop agent, set budget, notify owner
- Learns from past incidents (pattern memory)
- Conversational follow-ups with 30-day memory

**What it doesn't do yet:**
- Full Slack integration (needs app approval)
- Usage graphs/visualization
- Auto-remediation without human confirmation
- One-click deployment for new customers
- Multi-account support
- Predictive cost forecasting

---

### FAQ

**Q: How is this different from DevOps Agent?**

DevOps Agent investigates operational incidents (latency, errors, outages). CostOp investigates cost incidents (token spikes, runaway agents, budget overruns). Same pattern — alarm → investigate → root cause → fix. Different domain.

DevOps Agent is a managed AWS service. CostOp is self-hosted in the customer's account. Built on the same foundation (AgentCore, Strands, Skills) but customer-owned and extensible.

---

**Q: Why not just add this as a feature to Cost Anomaly Detection?**

Cost Anomaly Detection is batch (daily). This is real-time (5 minutes). CAD tells you WHAT changed. This tells you WHY, WHO, and HOW TO FIX. Different architecture, different latency, different value.

They're complementary. CostOp can consume CAD alerts as one input signal.

---

**Q: Why not use the existing FinOps Agent (AWS sample)?**

The FinOps Agent (aws-samples/sample-finops-agent-amazon-bedrock-agentcore) answers cost questions conversationally. It's reactive — you ask, it answers.

CostOp adds:
- Proactive detection (alarms trigger investigation without human asking)
- Per-agent attribution (which Bedrock agent costs what)
- Cross-service correlation (deployment → agent → spike)
- Investigation skills (structured playbooks, not free-form)
- Pattern memory (learns from past incidents)
- Remediation actions (stop, throttle, budget)

We started from the FinOps Agent codebase and extended it.

---

**Q: What's the killer demo?**

A Bedrock agent starts looping. Within 5 minutes:
1. CloudWatch alarm fires (tokens > threshold)
2. Agent investigates automatically
3. Finds: agent ARN e92b6952, 8 calls/minute, started after deploy at 02:20 by user MCP
4. Reports: "$5.33/hour burn rate, 10x baseline"
5. Gives fix: `aws lambda put-function-concurrency --function-name X --reserved-concurrent-executions 0`
6. User clicks "Stop" → done

Without CostOp: engineer wakes up next day, sees $200 charge, spends 2 hours in 3 consoles figuring out what happened.

---

**Q: What happens when Slack is enabled?**

The web console becomes optional. The agent lives in Slack:
- Proactive: posts investigation results to #cost-alerts channel
- Reactive: user replies in-thread, agent responds with full context
- Actions: buttons in Slack messages (Throttle, Budget, Notify)

Same agent, same tools, same memory. Just a different interface. Uses the published AWS pattern (sample-Integrating-Amazon-Bedrock-AgentCore-with-Slack).

---

**Q: What's the moat? Why can't someone else build this?**

They can. It's open source. The value is:
1. It's already built and working
2. It uses the Agent Skills spec (portable, extensible)
3. It integrates with the AWS cost ecosystem (CE, CAD, Budgets, CloudTrail)
4. Pattern memory creates compounding value over time
5. The investigation skill can be published to MCP registry for any agent to use

---

**Q: What are the risks?**

| Risk | Mitigation |
|---|---|
| Agent itself costs money (Sonnet) | Switch to Haiku for 92% savings. $0.03/investigation. |
| Agent causes the spike it's investigating | Concurrency limit on bridge Lambda. Circuit breaker. |
| False positives (alarm fires, nothing wrong) | Agent reports "all clear" quickly (2-3 tools, not 5). |
| Invocation logging not enabled | Agent reports blind spot + gives enable command. Deployment package auto-enables. |
| Response quality varies | Skills enforce structure. Steering hooks (future) enforce tool ordering. |

---

**Q: What's the 6-month roadmap?**

| Month | Milestone |
|---|---|
| Month 1 (done) | Core agent, web UI, alarms, investigation, actions |
| Month 2 | Slack integration, usage graphs, Haiku option |
| Month 3 | One-click CloudFormation deployment, auto-enable logging |
| Month 4 | Auto-remediation with guardrails, multi-account |
| Month 5 | Publish as MCP server on registry |
| Month 6 | Predictive alerts (deploy → cost forecast) |

---

**Q: Who is this for?**

- Platform engineering teams running 3+ Bedrock agents in production
- FinOps teams responsible for AI/ML spend
- SREs on-call for cost incidents
- Any team where a single runaway agent can burn $100+/day undetected

---

**Q: Can this be extended beyond Bedrock?**

Yes. The architecture (skills + tools + alarms) works for any service. Add tools for EC2, RDS, SageMaker. Add skills for "EC2 idle instance investigation" or "RDS storage spike." The framework is service-agnostic. We started with Bedrock because that's where the visibility gap is worst.

---

*"Cost Anomaly Detection tells you WHAT changed. CostOp tells you WHY, WHO caused it, HOW MUCH it's costing, and gives you the command to STOP it — in 5 minutes, not 24 hours."*
