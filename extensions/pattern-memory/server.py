"""
Pattern Memory MCP Server - Long-term memory for cost patterns.
Agent stores investigation results here and recalls them for future incidents.
"""
import boto3
import json
import uuid
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pattern-memory")
ddb = boto3.resource('dynamodb')
table = ddb.Table('cost_patterns')


@mcp.tool()
def save_pattern(pattern_type: str, signature: str, root_cause: str, resolution: str, cost_impact: float) -> str:
    """Save a cost pattern after investigation. Call this after resolving an incident
    so you can recognize it faster next time.
    
    Args:
        pattern_type: e.g. 'bedrock-token-spike', 'lambda-loop', 'idle-resource'
        signature: what the pattern looks like in metrics, e.g. 'InputTokenCount >3x baseline'
        root_cause: what caused it, e.g. 'prompt change doubled token count'
        resolution: what fixed it, e.g. 'reverted prompt to previous version'
        cost_impact: estimated dollar impact of the incident
    """
    item = {
        'pattern_id': str(uuid.uuid4()),
        'pattern_type': pattern_type,
        'signature': signature,
        'root_cause': root_cause,
        'resolution': resolution,
        'cost_impact': str(cost_impact),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'occurrences': 1
    }
    
    table.put_item(Item=item)
    return f"Pattern saved: {pattern_type}. I'll recognize this next time."


@mcp.tool()
def find_similar_pattern(pattern_type: str) -> str:
    """Search for previously seen patterns matching this type.
    Call this FIRST when investigating a new incident to see if you've seen it before."""
    response = table.scan(
        FilterExpression='pattern_type = :pt',
        ExpressionAttributeValues={':pt': pattern_type}
    )
    
    items = response.get('Items', [])
    if items:
        return json.dumps(items, default=str)
    
    return "No similar patterns found. This appears to be a new type of incident."


@mcp.tool()
def get_all_patterns() -> str:
    """Get all stored cost patterns. Use this to show the customer what you've learned."""
    response = table.scan(Limit=20)
    items = response.get('Items', [])
    return json.dumps(items, default=str) if items else "No patterns stored yet."


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
