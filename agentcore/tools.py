"""
Cost Intelligence Agent - Strands Tools
All tools the agent needs: CloudWatch, CloudTrail, Agent Economics, Pattern Memory
"""
import boto3
import json
import time
from datetime import datetime, timezone, timedelta
from strands import tool

# Clients
cw = boto3.client('cloudwatch')
ct = boto3.client('cloudtrail')
logs_client = boto3.client('logs')
ddb = boto3.resource('dynamodb')

# ============================================================
# CLOUDWATCH TOOLS - Real-time metrics and alarm status
# ============================================================

@tool
def get_alarm_status() -> str:
    """Get all CloudWatch alarms and their current state. Shows what's firing right now."""
    alarming = cw.describe_alarms(StateValue='ALARM').get('MetricAlarms', [])
    all_alarms = cw.describe_alarms(MaxRecords=10).get('MetricAlarms', [])
    
    result = []
    for a in (alarming or all_alarms):
        result.append({
            'name': a['AlarmName'],
            'state': a['StateValue'],
            'metric': f"{a['Namespace']}/{a['MetricName']}",
            'threshold': a.get('Threshold'),
            'reason': a.get('StateReason', '')[:150]
        })
    return json.dumps(result, default=str)


@tool
def get_bedrock_usage(minutes: int = 60) -> str:
    """Get current Bedrock token usage and invocation counts for the specified time window.
    Returns input tokens, output tokens, invocations, throttles, and estimated cost."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    
    metrics = ['InputTokenCount', 'OutputTokenCount', 'Invocations', 'InvocationThrottles']
    queries = [{'Id': f'm{i}', 'MetricStat': {
        'Metric': {'Namespace': 'AWS/Bedrock', 'MetricName': m},
        'Period': 300, 'Stat': 'Sum'
    }, 'ReturnData': True} for i, m in enumerate(metrics)]
    
    response = cw.get_metric_data(MetricDataQueries=queries, StartTime=start, EndTime=end)
    
    summary = {}
    for i, m in enumerate(metrics):
        values = response['MetricDataResults'][i].get('Values', [])
        summary[m] = int(sum(values)) if values else 0
    
    input_cost = summary['InputTokenCount'] * 0.003 / 1000
    output_cost = summary['OutputTokenCount'] * 0.015 / 1000
    summary['estimated_cost_usd'] = round(input_cost + output_cost, 4)
    summary['period_minutes'] = minutes
    return json.dumps(summary)


@tool
def get_metric_history(namespace: str, metric_name: str, hours: int = 6) -> str:
    """Get hourly metric values to see trends and spikes.
    Examples: namespace='AWS/Bedrock' metric_name='InputTokenCount'
              namespace='AWS/Lambda' metric_name='Invocations'"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    
    response = cw.get_metric_data(
        MetricDataQueries=[{
            'Id': 'm1',
            'MetricStat': {
                'Metric': {'Namespace': namespace, 'MetricName': metric_name},
                'Period': 3600, 'Stat': 'Sum'
            },
            'ReturnData': True
        }],
        StartTime=start, EndTime=end
    )
    
    results = response.get('MetricDataResults', [])
    if results and results[0].get('Values'):
        data = [{'time': t.strftime('%H:%M'), 'value': int(v)}
                for t, v in zip(results[0]['Timestamps'], results[0]['Values'])]
        return json.dumps(sorted(data, key=lambda x: x['time']))
    return "No data available."


# ============================================================
# CLOUDTRAIL TOOLS - What changed recently
# ============================================================

@tool
def get_recent_changes(service_name: str, hours: int = 6) -> str:
    """Get recent API changes for a service from CloudTrail. Use to correlate cost spikes with changes.
    Example service_name: 'bedrock', 'lambda', 'ec2', 'rds'"""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    response = ct.lookup_events(
        LookupAttributes=[{
            'AttributeKey': 'EventSource',
            'AttributeValue': f'{service_name}.amazonaws.com'
        }],
        StartTime=start, MaxResults=15
    )
    
    events = []
    for e in response.get('Events', []):
        events.append({
            'time': e['EventTime'].strftime('%H:%M'),
            'event': e['EventName'],
            'user': e.get('Username', 'unknown')
        })
    return json.dumps(events) if events else f"No changes found for {service_name} in last {hours}h."


@tool
def get_recent_deployments(hours: int = 24) -> str:
    """Get recent code deployments and infrastructure changes. Useful for correlating cost spikes."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    deploy_events = [
        'UpdateFunctionCode', 'UpdateFunctionConfiguration', 'CreateFunction',
        'CreateDeployment', 'UpdateService', 'RegisterTaskDefinition',
        'UpdateAgent', 'CreateAgentVersion', 'PutImage'
    ]
    
    response = ct.lookup_events(StartTime=start, MaxResults=50)
    
    deploys = []
    for e in response.get('Events', []):
        if e['EventName'] in deploy_events:
            deploys.append({
                'time': e['EventTime'].strftime('%Y-%m-%d %H:%M'),
                'event': e['EventName'],
                'user': e.get('Username', 'unknown')
            })
    return json.dumps(deploys) if deploys else "No deployments found."


# ============================================================
# AGENT ECONOMICS - Per-agent cost tracking
# ============================================================

@tool
def get_agent_costs(hours: int = 24) -> str:
    """Get per-Bedrock-agent token usage and estimated costs.
    Requires Bedrock model invocation logging to be enabled.
    Shows which AI agents cost the most."""
    start = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    end = int(datetime.now(timezone.utc).timestamp())
    
    query = """
    fields @timestamp, modelId, input.inputTokenCount, output.outputTokenCount
    | stats sum(input.inputTokenCount) as input_tokens,
            sum(output.outputTokenCount) as output_tokens,
            count(*) as invocations
      by coalesce(requestMetadata.agentId, 'direct-invoke') as agent_id
    | sort input_tokens desc
    """
    
    try:
        response = logs_client.start_query(
            logGroupName='/aws/bedrock/modelinvocations',
            startTime=start, endTime=end, queryString=query
        )
        query_id = response['queryId']
        for _ in range(30):
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)
        
        agents = []
        for row in result.get('results', []):
            fields = {f['field']: f['value'] for f in row}
            input_tok = int(fields.get('input_tokens', 0))
            output_tok = int(fields.get('output_tokens', 0))
            cost = (input_tok * 0.003 + output_tok * 0.015) / 1000
            agents.append({
                'agent_id': fields.get('agent_id', 'unknown'),
                'invocations': int(fields.get('invocations', 0)),
                'input_tokens': input_tok,
                'output_tokens': output_tok,
                'estimated_cost_usd': round(cost, 4)
            })
        return json.dumps(agents) if agents else "No invocation data found."
    except logs_client.exceptions.ResourceNotFoundException:
        return "Bedrock model invocation logging not enabled. Enable it in Bedrock console → Settings."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def detect_agent_loops(minutes: int = 30) -> str:
    """Detect potential runaway agent loops by looking for abnormal invocation patterns in recent minutes."""
    start = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
    end = int(datetime.now(timezone.utc).timestamp())
    
    query = """
    fields @timestamp, modelId, input.inputTokenCount
    | stats count(*) as calls, sum(input.inputTokenCount) as tokens
      by bin(5m) as time_bucket,
         coalesce(requestMetadata.agentId, 'direct') as agent_id
    | filter calls > 50
    | sort calls desc
    """
    
    try:
        response = logs_client.start_query(
            logGroupName='/aws/bedrock/modelinvocations',
            startTime=start, endTime=end, queryString=query
        )
        query_id = response['queryId']
        for _ in range(30):
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)
        
        if result.get('results'):
            alerts = []
            for row in result['results']:
                fields = {f['field']: f['value'] for f in row}
                alerts.append({
                    'agent_id': fields.get('agent_id'),
                    'calls_in_5min': int(fields.get('calls', 0)),
                    'tokens': int(fields.get('tokens', 0))
                })
            return json.dumps({'status': 'POTENTIAL_LOOPS', 'alerts': alerts})
        return json.dumps({'status': 'OK', 'message': 'No abnormal patterns detected.'})
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# PATTERN MEMORY - Long-term learning
# ============================================================

@tool
def save_pattern(pattern_type: str, root_cause: str, resolution: str, cost_impact: str) -> str:
    """Save a cost pattern after investigation so you recognize it faster next time.
    pattern_type: e.g. 'bedrock-token-spike', 'lambda-loop'
    root_cause: what caused it
    resolution: what fixed it
    cost_impact: dollar amount"""
    try:
        table = ddb.Table('cost_patterns')
        import uuid
        table.put_item(Item={
            'pattern_id': str(uuid.uuid4()),
            'pattern_type': pattern_type,
            'root_cause': root_cause,
            'resolution': resolution,
            'cost_impact': cost_impact,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        return f"Pattern saved: {pattern_type}. Will recognize this next time."
    except Exception as e:
        return f"Could not save pattern: {str(e)}"


@tool
def find_similar_patterns(pattern_type: str) -> str:
    """Search for previously seen patterns. Call this FIRST when investigating to check if you've seen it before."""
    try:
        table = ddb.Table('cost_patterns')
        response = table.scan(
            FilterExpression='pattern_type = :pt',
            ExpressionAttributeValues={':pt': pattern_type}
        )
        items = response.get('Items', [])
        return json.dumps(items, default=str) if items else "No similar patterns found. This is new."
    except Exception as e:
        return f"Error: {str(e)}"
