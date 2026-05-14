"""
Agent Economics MCP Tool - Per-Bedrock-agent cost tracking.
Prerequisite: Enable Bedrock model invocation logging to CloudWatch Logs.
"""
import boto3
import json
import time
from datetime import datetime, timezone, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-economics")
logs = boto3.client('logs')

LOG_GROUP = '/aws/bedrock/modelinvocations'


@mcp.tool()
def get_agent_costs(hours: int = 24) -> str:
    """Get per-Bedrock-agent token usage and estimated costs.
    Shows which AI agents cost the most and their efficiency."""
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
        response = logs.start_query(
            logGroupName=LOG_GROUP,
            startTime=start,
            endTime=end,
            queryString=query
        )
        
        query_id = response['queryId']
        for _ in range(30):
            result = logs.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)
        
        agents = []
        for row in result.get('results', []):
            fields = {f['field']: f['value'] for f in row}
            input_tok = int(fields.get('input_tokens', 0))
            output_tok = int(fields.get('output_tokens', 0))
            # Haiku pricing as default estimate
            cost = (input_tok * 0.00025 + output_tok * 0.00125) / 1000
            agents.append({
                'agent_id': fields.get('agent_id', 'unknown'),
                'invocations': int(fields.get('invocations', 0)),
                'input_tokens': input_tok,
                'output_tokens': output_tok,
                'estimated_cost_usd': round(cost, 4)
            })
        
        return json.dumps(agents) if agents else "No invocation data found. Ensure Bedrock model invocation logging is enabled."
    
    except logs.exceptions.ResourceNotFoundException:
        return f"Log group '{LOG_GROUP}' not found. Enable Bedrock model invocation logging in the Bedrock console."
    except Exception as e:
        return f"Error querying agent costs: {str(e)}"


@mcp.tool()
def detect_agent_loops(hours: int = 1) -> str:
    """Detect potential runaway agent loops by looking for abnormal invocation patterns."""
    start = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
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
        response = logs.start_query(
            logGroupName=LOG_GROUP, startTime=start, endTime=end, queryString=query
        )
        
        query_id = response['queryId']
        for _ in range(30):
            result = logs.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)
        
        alerts = []
        for row in result.get('results', []):
            fields = {f['field']: f['value'] for f in row}
            alerts.append({
                'agent_id': fields.get('agent_id'),
                'time_window': fields.get('time_bucket'),
                'calls_in_5min': int(fields.get('calls', 0)),
                'tokens_consumed': int(fields.get('tokens', 0))
            })
        
        if alerts:
            return json.dumps({'status': 'POTENTIAL_LOOPS_DETECTED', 'alerts': alerts})
        return json.dumps({'status': 'OK', 'message': 'No abnormal patterns detected in the last hour.'})
    
    except Exception as e:
        return f"Error checking for loops: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
