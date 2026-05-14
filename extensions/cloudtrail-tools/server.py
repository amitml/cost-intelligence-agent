"""
CloudTrail MCP Tools - Adds "WHY did costs change?" capability
Register these as additional tools in the AgentCore Gateway.
"""
import boto3
import json
from datetime import datetime, timezone, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cloudtrail-cost-correlation")
ct = boto3.client('cloudtrail')
cw = boto3.client('cloudwatch')


@mcp.tool()
def get_recent_changes(service_name: str, hours: int = 6) -> str:
    """Get recent API changes for a specific AWS service from CloudTrail.
    Use this to correlate cost spikes with infrastructure changes."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    response = ct.lookup_events(
        LookupAttributes=[{
            'AttributeKey': 'EventSource',
            'AttributeValue': f'{service_name}.amazonaws.com'
        }],
        StartTime=start,
        MaxResults=20
    )
    
    events = []
    for e in response.get('Events', []):
        events.append({
            'time': e['EventTime'].isoformat(),
            'event': e['EventName'],
            'user': e.get('Username', 'unknown'),
            'resources': [r.get('ResourceName', '') for r in e.get('Resources', [])][:2]
        })
    
    return json.dumps(events, default=str) if events else "No recent changes found for this service."


@mcp.tool()
def get_recent_deployments(hours: int = 24) -> str:
    """Get recent code deployments and infrastructure changes from CloudTrail.
    Useful for correlating cost increases with new deployments."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    deploy_events = [
        'UpdateFunctionCode', 'UpdateFunctionConfiguration', 'CreateFunction',
        'CreateDeployment', 'UpdateService', 'RegisterTaskDefinition',
        'PutImage', 'UpdateAgent', 'CreateAgentVersion'
    ]
    
    response = ct.lookup_events(StartTime=start, MaxResults=50)
    
    deploys = []
    for e in response.get('Events', []):
        if e['EventName'] in deploy_events:
            deploys.append({
                'time': e['EventTime'].isoformat(),
                'event': e['EventName'],
                'user': e.get('Username', 'unknown'),
                'resources': [r.get('ResourceName', '') for r in e.get('Resources', [])][:2]
            })
    
    return json.dumps(deploys, default=str) if deploys else "No recent deployments found."


@mcp.tool()
def get_resource_spike(service: str, metric_name: str, hours: int = 6) -> str:
    """Get CloudWatch metrics to identify which resources are spiking.
    Examples: service='AWS/Lambda' metric='Invocations', service='AWS/Bedrock' metric='InputTokenCount'"""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    
    response = cw.get_metric_data(
        MetricDataQueries=[{
            'Id': 'spike',
            'MetricStat': {
                'Metric': {
                    'Namespace': service,
                    'MetricName': metric_name
                },
                'Period': 3600,
                'Stat': 'Sum'
            },
            'ReturnData': True
        }],
        StartTime=start,
        EndTime=end
    )
    
    results = response.get('MetricDataResults', [])
    if results and results[0].get('Values'):
        values = results[0]['Values']
        timestamps = results[0]['Timestamps']
        data = [{'time': t.isoformat(), 'value': v} for t, v in zip(timestamps, values)]
        return json.dumps(data, default=str)
    
    return f"No metric data found for {service}/{metric_name}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
