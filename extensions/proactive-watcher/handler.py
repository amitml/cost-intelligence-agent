"""
Proactive Cost Watcher - Triggered by CloudWatch Alarms and Cost Anomaly Detection.
Asks the SAME FinOps agent to investigate, then posts the answer to SNS/Slack.
"""
import boto3
import json
import os

agentcore = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
sns = boto3.client('sns')

AGENT_RUNTIME_ARN = os.environ['AGENT_RUNTIME_ARN']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']


def handler(event, context):
    source = event.get('source', '')
    detail = event.get('detail', {})
    
    # Build investigation query based on trigger type
    if 'cloudwatch' in source:
        alarm_name = detail.get('alarmName', 'Unknown')
        metric = detail.get('configuration', {}).get('metrics', [{}])[0]
        query = (
            f"URGENT: CloudWatch alarm '{alarm_name}' just fired. "
            f"Investigate what's causing this spike. Check recent deployments, "
            f"identify the specific resources involved, and estimate the cost impact. "
            f"Provide a specific recommendation."
        )
        subject = f"⚠️ Cost Alert: {alarm_name}"
        
    elif 'ce' in source or 'Cost Anomaly' in event.get('detail-type', ''):
        anomaly = json.dumps(detail, default=str)[:500]
        query = (
            f"Cost Anomaly Detection found an issue: {anomaly}. "
            f"Investigate: what service is affected, what changed recently "
            f"(check deployments), and what should we do about it?"
        )
        subject = "⚠️ Cost Anomaly Detected"
    else:
        query = f"Investigate this cost event: {json.dumps(detail, default=str)[:500]}"
        subject = "⚠️ Cost Event"

    # Ask the FinOps agent to investigate
    try:
        response = agentcore.invoke_agent_runtime(
            agentRuntimeIdentifier=AGENT_RUNTIME_ARN,
            payload=json.dumps({
                "prompt": query,
                "sessionId": f"proactive-{context.aws_request_id}",
                "userId": "cost-watcher"
            })
        )
        
        explanation = response.get('output', {}).get('text', 'Investigation completed but no explanation generated.')
    except Exception as e:
        explanation = f"Could not complete investigation: {str(e)}\n\nOriginal alert: {query}"

    # Publish to SNS (goes to Slack/Email/PagerDuty)
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=explanation
    )
    
    return {'statusCode': 200, 'body': 'Alert sent'}
