"""
Amazon Bedrock Agent Core Runtime - FinOps Agent
Uses BedrockAgentCoreApp for proper authentication and Gateway integration
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from botocore.credentials import Credentials
from streamable_http_sigv4 import streamablehttp_client_with_sigv4
from tools import (
    get_alarm_status, get_bedrock_usage, get_metric_history,
    get_recent_changes, get_recent_deployments,
    get_agent_costs, detect_agent_loops,
    save_pattern, find_similar_patterns,
    send_notification, stop_agent_invocations, check_invocation_logs, set_budget_alert,
    check_bedrock_config_changes
)
from skill_loader import select_skill
import os
import boto3
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Agent Core app
app = BedrockAgentCoreApp()

# Get configuration from environment
GATEWAY_ARN = os.environ.get('GATEWAY_ARN')
MEMORY_ID = os.environ.get('MEMORY_ID')
MODEL_ID = os.environ.get('MODEL_ID', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

logger.info(f"Gateway ARN: {GATEWAY_ARN}")
logger.info(f"Model ID: {MODEL_ID}")
logger.info(f"Memory ID: {MEMORY_ID}")
logger.info(f"AWS Region: {AWS_REGION}")

if not GATEWAY_ARN:
    logger.error("Gateway ARN not configured!")
else:
    logger.info("Gateway configured successfully")

if MEMORY_ID:
    logger.info(f"Memory enabled: {MEMORY_ID}")
else:
    logger.warning("Memory ID not configured - memory disabled")

# Initialize Bedrock model
model = BedrockModel(
    model_id=MODEL_ID,
    region_name=AWS_REGION
)

# Get AWS credentials for SigV4 signing
session = boto3.Session()
credentials = session.get_credentials()
frozen_credentials = Credentials(
    access_key=credentials.access_key,
    secret_key=credentials.secret_key,
    token=credentials.token
)

# Extract Gateway ID from ARN and construct endpoint URL
gateway_id = GATEWAY_ARN.split('/')[-1] if GATEWAY_ARN else None
gateway_endpoint = f"https://{gateway_id}.gateway.bedrock-agentcore.{AWS_REGION}.amazonaws.com/mcp" if gateway_id else None

logger.info(f"Gateway Endpoint: {gateway_endpoint}")


def get_current_date_utc() -> str:
    """Get current date and time in UTC for cost query context"""
    try:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d (%A) %H:00 UTC")
    except Exception as e:
        logger.warning(f"Failed to get current date: {e}")
        return "2026-01-24 (Friday) 12:00 UTC"


# Local Strands tools (Cost Intelligence extensions)
local_tools = [
    get_alarm_status, get_bedrock_usage, get_metric_history,
    get_recent_changes, get_recent_deployments,
    get_agent_costs, detect_agent_loops,
    save_pattern, find_similar_patterns,
    send_notification, stop_agent_invocations, check_invocation_logs, set_budget_alert,
    check_bedrock_config_changes
]

# Global MCP client to keep connection alive
mcp_client = None
agent = None
mcp_tools = []  # Store tools globally
system_prompt_template = ""  # Store system prompt template


def initialize_agent_with_gateway():
    """Initialize agent with Gateway tools using MCP Client with SigV4 auth"""
    global mcp_client, agent, mcp_tools, system_prompt_template
    
    try:
        if not gateway_endpoint:
            logger.error("Cannot initialize: Gateway endpoint not configured")
            agent = Agent(
                model=model,
                system_prompt="I'm sorry, but I'm not properly configured. Please contact support."
            )
            return
        
        logger.info("🔧 Initializing MCP Client with SigV4 authentication...")
        
        # Create MCP client with SigV4 authentication
        mcp_client = MCPClient(lambda: streamablehttp_client_with_sigv4(
            url=gateway_endpoint,
            credentials=frozen_credentials,
            service="bedrock-agentcore",
            region=AWS_REGION
        ))
        
        # Start the MCP client connection
        mcp_client.__enter__()
        
        # Get tools from Gateway
        logger.info("📋 Listing tools from Gateway...")
        mcp_tools = mcp_client.list_tools_sync()
        logger.info(f"✅ Retrieved {len(mcp_tools)} tools from Gateway")
        
        # Get current date for system prompt
        current_date = get_current_date_utc()
        
        # Store system prompt template for reuse
        # IMPORTANT: Don't list specific tool names in system prompt
        # Gateway prefixes tool names, so let the agent discover them dynamically
        system_prompt_template = f"""You are a Cost Intelligence Agent. You investigate cost anomalies in real-time.

Current date: {current_date}

CRITICAL: When investigating an alert or anomaly, ALWAYS use these tools FIRST:
1. get_alarm_status — what CloudWatch alarms are firing right now
2. get_bedrock_usage — real-time token counts and invocations (last 60 min)
3. get_metric_history — hourly trend for any metric (shows spikes)
4. get_recent_changes — CloudTrail: what API calls happened recently for a service
5. get_recent_deployments — what code was deployed in the last 24h
6. find_similar_patterns — have we seen this pattern before?
7. get_agent_costs — per-Bedrock-agent token breakdown (requires invocation logging)
8. detect_agent_loops — check for runaway agent patterns

Only use billingMcp tools (Cost Explorer) for dollar amounts and historical cost trends.
Do NOT use billingMcp for real-time investigation — it has 12-hour delay.

Investigation workflow:
1. Check real-time metrics (get_bedrock_usage, get_alarm_status)
2. Check what changed (get_recent_changes, get_recent_deployments)
3. Check patterns (find_similar_patterns)
4. Get dollar context (billingMcp___cost-explorer)
5. Explain root cause + recommend action
6. Save pattern (save_pattern) if this is new

For pricing lookups, use pricingMcp__ tools.
Be concise. Use bullet points. Show specific numbers."""
        
        # Create agent with Gateway tools (memory will be added per-request)
        # Note: We don't add session_manager here because it's request-specific
        agent = Agent(
            model=model,
            tools=mcp_tools + local_tools,
            system_prompt=system_prompt_template
        )
        
        logger.info("✅ Agent created successfully with Gateway tools - connection kept alive")
            
    except Exception as e:
        logger.error(f"❌ Error initializing agent with Gateway: {e}", exc_info=True)
        # Create a fallback agent without tools
        agent = Agent(
            model=model,
            system_prompt="I'm sorry, but I'm having trouble accessing my tools right now. Please try again later."
        )


# Initialize agent with Gateway
logger.info("🚀 Initializing agent with Gateway-backed MCP tools using IAM SigV4 authentication")
initialize_agent_with_gateway()


@app.entrypoint
def invoke(payload):
    """
    Process user input and return FinOps analysis
    """
    global agent

    user_message = payload.get("prompt", "")
    session_id = payload.get("sessionId", "default_session")
    user_id = payload.get("userId", "default_user")

    if not user_message:
        logger.error("No prompt provided in payload")
        return {
            "error": "No prompt provided",
            "message": "Please provide a 'prompt' key in the input"
        }

    logger.info(f"📨 Processing request - Session: {session_id}")

    # Select skill based on query
    skill_instructions = select_skill(user_message)
    request_prompt = f"""{system_prompt_template}

## ACTIVE SKILL (follow these steps exactly):

{skill_instructions}
"""

    # Create agent with memory session manager if memory is configured
    agent_with_memory = agent  # Default to base agent

    if MEMORY_ID and mcp_tools:  # Only configure memory if we have tools
        try:
            logger.info(f"💾 Configuring memory - Memory ID: {MEMORY_ID}, Session: {session_id}")

            memory_config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=user_id
            )

            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=memory_config,
                region_name=AWS_REGION
            )

            # Create agent with session manager (memory handled automatically)
            agent_with_memory = Agent(
                model=model,
                tools=mcp_tools + local_tools,  # Use globally stored tools + local tools
                system_prompt=request_prompt,  # Skill-enhanced prompt
                session_manager=session_manager  # This handles memory automatically!
            )

            logger.info("✅ Agent configured with memory session manager")

        except Exception as e:
            logger.warning(f"⚠️ Could not configure memory, using agent without memory: {e}")
            agent_with_memory = agent
    else:
        if not MEMORY_ID:
            logger.info("ℹ️ Memory not configured, using agent without memory")
        else:
            logger.warning("⚠️ Tools not available, using agent without memory")

    # Invoke agent - memory is handled automatically by session_manager
    try:
        logger.info("🤖 Invoking agent...")
        result = agent_with_memory(user_message)

        # Extract the final message from the result
        if hasattr(result, 'message'):
            final_message = result.message
        elif hasattr(result, 'content'):
            final_message = result.content
        elif isinstance(result, str):
            final_message = result
        else:
            final_message = str(result)

        # If final_message is a dict with role/content structure, extract the text
        if isinstance(final_message, dict):
            if 'content' in final_message and isinstance(final_message['content'], list):
                final_message = ''.join([item.get('text', '') for item in final_message['content'] if 'text' in item])
            elif 'text' in final_message:
                final_message = final_message['text']

        logger.info("✅ Request processed successfully")

        response = {
            "result": final_message,
            "sessionId": session_id,
            "userId": user_id
        }

        return response

    except Exception as e:
        logger.error(f"❌ Agent invocation error: {e}", exc_info=True)
        return {
            "error": "Agent processing failed",
            "message": str(e),
            "sessionId": session_id
        }


if __name__ == "__main__":
    logger.info("🚀 Starting FinOps Agent Runtime with BedrockAgentCoreApp")
    logger.info(f"📊 Model: {MODEL_ID}")
    logger.info(f"🌐 Gateway: {gateway_endpoint}")
    logger.info(f"💾 Memory: {MEMORY_ID if MEMORY_ID else 'Disabled'}")
    app.run()
