# Cost Intelligence Agent — Next Phase

## What's Working Today
- ✅ Agent with 13 tools + 28 MCP tools
- ✅ Skills-based investigation (correct tool ordering)
- ✅ Action tools (stop agent, send notification, set budget)
- ✅ Pattern memory (learns from past incidents)
- ✅ Web UI with login (Cognito → AgentCore direct, no timeout)
- ✅ CloudWatch alarms → EventBridge → Lambda → Agent (proactive)
- ✅ Slack alerts via Chatbot (basic)

## What's Missing (to be a product)

### 1. Live Alerts Panel
**Left panel shows real alerts, not hardcoded.**

On page load, browser calls `get_alarm_status` + pulls recent investigations from DynamoDB.

Each alert card shows:
- Severity (🔴🟡🔵)
- What: "Bedrock tokens 32x normal"
- When: "5 min ago"
- Status: New / Investigating / Resolved
- One-line cause: "deploy by dev@co at 2:12 PM"

### 2. Structured Response Format
**Agent returns JSON, UI renders as cards.**

```json
{
  "severity": "critical",
  "summary": "Bedrock token spike caused by deployment",
  "findings": [
    {"label": "Current burn rate", "value": "$63/day", "status": "danger"},
    {"label": "Root cause", "value": "Prompt change doubled token count"},
    {"label": "Affected agent", "value": "data-analyst-agent"}
  ],
  "actions": [
    {"label": "Stop agent", "tool": "stop_agent_invocations", "params": {"function_name": "data-analyst"}, "destructive": true},
    {"label": "Set budget at $100/mo", "tool": "set_budget_alert", "params": {"monthly_limit": 100}},
    {"label": "Notify owner", "tool": "send_notification", "params": {"subject": "Cost spike"}}
  ],
  "timeline": [
    {"time": "2:12 PM", "event": "Deployment by dev@co"},
    {"time": "2:15 PM", "event": "Token usage jumped 32x"},
    {"time": "2:46 PM", "event": "CloudWatch alarm fired"},
    {"time": "2:47 PM", "event": "Agent started investigation"}
  ]
}
```

UI renders this as:
- Summary card at top
- Findings as a table
- Action buttons (click to execute)
- Timeline on the side

### 3. One-Click Actions
**Buttons in the response that execute tools.**

User sees: [🛑 Stop Agent] [💰 Set Budget] [📧 Notify Owner]
Clicks one → agent executes → shows result inline.

### 4. Proactive Investigations in UI
**When alarm fires, agent investigates and stores result in DynamoDB.**

When user opens UI, they see:
```
"While you were away (2 investigations):"
├── 2:47 PM: Bedrock spike — caused by deployment, $63/day burn → [View]
└── Yesterday: EC2 idle instance — $4.20/day wasted → [View]
```

### 5. User Notification (while investigating)
**Agent uses `send_notification` tool during proactive investigations.**

Flow:
```
Alarm fires → Agent investigates → Finds root cause
  → Calls send_notification("⚠️ Bedrock spike: $63/day burn. Caused by deploy at 2:12 PM. Open console to take action.")
  → SNS → Email to owner
```

No Slack app needed. Email arrives with:
- What happened
- How much it's costing
- Link to the web console to take action

For Slack (future): Once app is approved, agent posts directly to channel.

---

## Build Estimate

| Task | Time | Effort |
|---|---|---|
| Live alerts panel (CloudWatch → DynamoDB → UI) | 2 hours | Backend + frontend |
| Structured response format (JSON output + UI renderer) | 3 hours | Skill update + frontend |
| One-click action buttons | 1 hour | Frontend only |
| Proactive investigation storage (DynamoDB) | 1 hour | Backend |
| Email notification during proactive investigations | 30 min | Already have send_notification tool |
| Proper Vite build + deploy pipeline | 30 min | DevOps |
| **Total** | **~8 hours** | |

---

## Customer Cost (what they pay monthly)

| Component | Monthly Cost |
|---|---|
| AgentCore Runtime (Sonnet, ~20 investigations/day) | $45-50 |
| Cost Explorer API calls | $7 |
| CloudWatch Alarms (5) | $0.50 |
| DynamoDB (pattern memory + investigations) | Free tier |
| Lambda (10-line bridge) | Free tier |
| Amplify hosting | $1 |
| Cognito | Free tier |
| EventBridge | Free |
| **Total** | **~$55-60/month** |

**Value proposition:** Saves 2-3 hours of engineer time per incident. At $100/hr engineer cost, pays for itself after ONE incident per month.

---

## Architecture (final)

```
┌─────────────────────────────────────────────────────────┐
│ WEB UI (Amplify/CloudFront)                              │
│ ├── Login (Cognito)                                      │
│ ├── Live Alerts Panel (from DynamoDB)                    │
│ ├── Investigation View (structured cards + timeline)     │
│ ├── Action Buttons (call tools on click)                 │
│ └── Chat (follow-up questions)                           │
└────────────────────────┬────────────────────────────────┘
                         │ SigV4 (direct, no timeout)
                         ▼
┌─────────────────────────────────────────────────────────┐
│ AgentCore Runtime (THE BRAIN)                            │
│ ├── Strands + Claude Sonnet                              │
│ ├── Skills (investigation playbooks)                     │
│ ├── Tools:                                               │
│ │   ├── Monitor: alarms, bedrock_usage, metrics          │
│ │   ├── Investigate: cloudtrail, deployments, logs       │
│ │   ├── Economics: agent_costs, detect_loops             │
│ │   ├── Memory: save_pattern, find_patterns              │
│ │   ├── Actions: stop_agent, notify, set_budget          │
│ │   └── MCP: Cost Explorer, Budgets, Pricing            │
│ ├── AgentCore Memory (30-day conversations)              │
│ └── DynamoDB (long-term patterns + investigation results)│
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   CloudWatch      CloudTrail     Cost Explorer
   (real-time)     (what changed)  (dollar amounts)

PROACTIVE TRIGGER:
  CloudWatch Alarm → EventBridge → Lambda (10 lines) → AgentCore
    → Investigates → Stores in DynamoDB → Sends email notification
```

---

## Next Session

Start with structured response format (biggest UX impact), then live alerts, then action buttons. Want me to begin?
