"""
EventBridge → AgentCore trigger.
NOT the brain. Just translates an alarm event into an invoke call.
The agent does all thinking, investigation, and Slack posting via MCP tools.
"""
import boto3
import json
import os

agentcore = boto3.client('bedrock-agentcore', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
AGENT_RUNTIME_ARN = os.environ['AGENT_RUNTIME_ARN']


def handler(event, context):
    # Translate alarm event into a prompt for the agent
    source = event.get('source', '')
    detail = event.get('detail', {})
    
    if 'cloudwatch' in source:
        alarm = detail.get('alarmName', 'unknown')
        prompt = f"A CloudWatch alarm just fired: '{alarm}'. Investigate using your tools. Check what's spiking, what changed recently, and check if you've seen this pattern before. Post your findings to Slack."
    elif 'ce' in source:
        prompt = f"Cost Anomaly Detection alert: {json.dumps(detail, default=str)[:300]}. Investigate and post findings to Slack."
    else:
        prompt = f"Cost event received: {json.dumps(event, default=str)[:300]}. Investigate and post to Slack."
    
    # Invoke the agent - it handles everything else via MCP tools
    response = agentcore.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        payload=json.dumps({
            "prompt": prompt,
            "sessionId": f"alert-{context.aws_request_id}",
            "userId": "cost-watcher-system"
        }).encode()
    )
    
    return {'statusCode': 200}
