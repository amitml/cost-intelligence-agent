"""
CloudWatch MCP Server - Real-time metrics and alarm status.
Gives the agent eyes on what's happening RIGHT NOW.
"""
import boto3
import json
from datetime import datetime, timezone, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cloudwatch-realtime")
cw = boto3.client('cloudwatch')


@mcp.tool()
def get_alarm_status() -> str:
    """Get all CloudWatch alarms and their current state. Use this to see what's firing."""
    response = cw.describe_alarms(StateValue='ALARM')
    alarms = response.get('MetricAlarms', [])
    
    if not alarms:
        response = cw.describe_alarms(MaxRecords=10)
        alarms = response.get('MetricAlarms', [])
    
    result = []
    for a in alarms:
        result.append({
            'name': a['AlarmName'],
            'state': a['StateValue'],
            'metric': f"{a['Namespace']}/{a['MetricName']}",
            'threshold': a.get('Threshold'),
            'reason': a.get('StateReason', '')[:200]
        })
    
    return json.dumps(result, default=str)


@mcp.tool()
def get_metric_spike(namespace: str, metric_name: str, minutes: int = 30) -> str:
    """Get recent metric values to see spikes. 
    Examples: namespace='AWS/Bedrock' metric_name='InputTokenCount'
              namespace='AWS/Lambda' metric_name='Invocations'"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    
    response = cw.get_metric_data(
        MetricDataQueries=[{
            'Id': 'm1',
            'MetricStat': {
                'Metric': {'Namespace': namespace, 'MetricName': metric_name},
                'Period': 300,
                'Stat': 'Sum'
            },
            'ReturnData': True
        }],
        StartTime=start,
        EndTime=end
    )
    
    results = response.get('MetricDataResults', [])
    if results and results[0].get('Values'):
        data = [{'time': t.isoformat(), 'value': v} 
                for t, v in zip(results[0]['Timestamps'], results[0]['Values'])]
        return json.dumps(sorted(data, key=lambda x: x['time']), default=str)
    
    return "No data available for this metric in the specified timeframe."


@mcp.tool()
def get_bedrock_usage_now(minutes: int = 60) -> str:
    """Get current Bedrock token usage and invocation counts. 
    Use this to see real-time cost drivers."""
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
        summary[m] = sum(values) if values else 0
    
    # Estimate cost
    input_cost = summary['InputTokenCount'] * 0.003 / 1000  # Sonnet pricing
    output_cost = summary['OutputTokenCount'] * 0.015 / 1000
    summary['estimated_cost_usd'] = round(input_cost + output_cost, 4)
    summary['period_minutes'] = minutes
    
    return json.dumps(summary)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
