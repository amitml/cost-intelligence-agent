---
name: agent-economics-review
description: Analyze per-Bedrock-agent costs, identify expensive agents, detect runaway loops, and provide optimization recommendations. Use when asked about which agent costs the most, per-agent breakdown, or agent efficiency.
---

# Agent Economics Review

Use this skill when the user asks about per-agent costs, agent efficiency, or which AI agent is expensive.

## Step 1: Get per-agent cost breakdown

Call `get_agent_costs(hours=24)` to get token usage per agent.

Present as a ranked table:
- Agent ID/name
- Invocations
- Input tokens
- Output tokens
- Estimated cost
- Cost per invocation

## Step 2: Check for loops

Call `detect_agent_loops(minutes=30)` to identify any agents with abnormal invocation patterns.

Flag any agent with >50 calls in a 5-minute window as a potential loop.

## Step 3: Compare to baseline

Call `get_metric_history(namespace='AWS/Bedrock', metric_name='Invocations', hours=24)` to see if today's pattern is normal.

Calculate: is any agent using significantly more tokens today vs its average?

## Step 4: Get cost context

Use `billingMcp___cost-explorer` to get Bedrock dollar spend for today vs yesterday.

## Step 5: Provide recommendations

Based on findings:
- **Most expensive agent**: Suggest prompt optimization (shorter system prompts, summarization before sending)
- **Loop detected**: Suggest adding max_iterations limit, circuit breaker, or concurrency throttle
- **Inefficient agent** (high tokens, low value): Suggest switching to a cheaper model (Haiku) or caching responses
- **Cost per query too high**: Calculate if the business value justifies the cost

## Key metrics to report

- Total agent spend (last 24h)
- Cost per conversation/query for each agent
- Token efficiency ratio (output tokens / input tokens — lower = agent is mostly reading, not generating)
- Projected monthly agent spend at current rate
