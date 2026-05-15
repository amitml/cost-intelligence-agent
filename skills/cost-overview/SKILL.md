---
name: cost-overview
description: Provide a summary of current AWS costs, budget status, and trends. Use when asked general questions like "what are my costs", "am I over budget", "show me spending", or "cost summary".
---

# Cost Overview

Use this skill for general cost questions that don't involve investigating a specific spike.

## Step 1: Get current spend

Use `billingMcp___cost-explorer` to get:
- This month's spend (MTD)
- Last month's total
- Daily breakdown for the last 7 days

## Step 2: Check budget status

Use `billingMcp___budgets` to see if any budgets are set and their current status.

## Step 3: Check for active anomalies

Call `get_alarm_status` to see if any cost-related alarms are firing right now.
Use `billingMcp___cost-anomaly` to check for detected anomalies.

## Step 4: Present summary

Format as:
- **MTD spend**: $X (Y% of budget)
- **Projected month-end**: $Z
- **Top 5 services** with amounts
- **Anomalies**: any active alerts
- **Trend**: up/down vs last month, percentage change

## Step 5: Proactive recommendations

If spend is >80% of budget: warn and suggest review
If a service grew >50% month-over-month: flag it
If Bedrock is top service: mention agent economics review is available
