"""
MAS Agent API endpoints
"""

import os
import logging
import requests
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, AsyncGenerator

from backend.models.schemas import ChatRequestModel, ChatResponseModel, ChatMessageModel
from backend import config

router = APIRouter()
logger = logging.getLogger(__name__)

# MAS Agent endpoint configuration
MAS_ENDPOINT_URL = config.MAS_ENDPOINT_URL

async def get_agent_service():
    """Get agent service with authentication"""
    token = config.DATABRICKS_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="Agent authentication not configured")
    return AgentService(token)

class AgentService:
    """Service for interacting with MAS Agent endpoint"""

    def __init__(self, token: str):
        self.token = token
        self.endpoint_url = MAS_ENDPOINT_URL

    async def send_message(self, message: str, context: Dict[str, Any], chat_history: List[ChatMessageModel] = None) -> Dict[str, Any]:
        """Send message to MAS agent endpoint"""
        try:
            # Log the incoming request
            logger.info(f"🤖 MAS Agent Request - Message: {message[:100]}...")
            logger.info(f"🤖 Context: alert_id={context.get('alert_id')}, customer_id={context.get('customer_id')}")

            # Prepare conversation input
            conversation = []

            # Add chat history if provided
            if chat_history:
                logger.info(f"🤖 Including {len(chat_history)} messages from chat history")
                for msg in chat_history[-5:]:  # Last 5 messages for context
                    conversation.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Add current message
            conversation.append({
                "role": "user",
                "content": message
            })

            # Generate conversation ID
            conversation_id = f"alert_{context.get('alert_id', 'unknown')}_{context.get('customer_id', 'unknown')}"
            logger.info(f"🤖 Conversation ID: {conversation_id}")

            # Simple payload
            payload = {
                "input": conversation,
                "databricks_options": {
                    "conversation_id": conversation_id,
                    "return_trace": True
                },
                "context": {
                    "conversation_id": conversation_id,
                    "user_id": "analyst"
                }
            }

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            logger.info(f"🤖 Sending request to MAS endpoint: {self.endpoint_url}")
            logger.info(f"🤖 Payload size: {len(json.dumps(payload))} bytes")

            # Increase timeout to 120 seconds
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=120  # Increased from 60 to 120 seconds
            )

            if response.status_code == 200:
                logger.info(f"✅ MAS Agent Response received - Status: 200")
                result = response.json()
                logger.info(f"🤖 Response structure keys: {list(result.keys())}")

                # Extract text from MAS response structure
                response_text = ""

                # Handle MAS response format with output array
                if "output" in result and isinstance(result["output"], list):
                    logger.info(f"🤖 Processing output array with {len(result['output'])} items")
                    # Extract text from each message in output array
                    for item in result["output"]:
                        if isinstance(item, dict):
                            # Look for content array with text
                            content = item.get("content", [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and "text" in content_item:
                                        response_text += content_item["text"] + "\n"
                            elif isinstance(content, str):
                                response_text += content + "\n"
                elif "output" in result and isinstance(result["output"], str):
                    logger.info(f"🤖 Processing output string")
                    response_text = result["output"]
                elif "response" in result:
                    logger.info(f"🤖 Processing response field")
                    response_text = result["response"]
                elif "text" in result:
                    logger.info(f"🤖 Processing text field")
                    response_text = result["text"]
                else:
                    logger.warning(f"⚠️ Unknown response format. Keys: {list(result.keys())}")
                    logger.warning(f"⚠️ Full response: {json.dumps(result)[:500]}...")

                # Clean up response
                response_text = response_text.strip()
                logger.info(f"✅ Final response length: {len(response_text)} characters")

                return {
                    "response": response_text if response_text else "I received your request but couldn't generate a response.",
                    "confidence_score": 0.9,
                    "recommendation": None,
                    "evidence": []
                }
            else:
                logger.error(f"❌ MAS Agent error: {response.status_code} - {response.text[:500]}")
                raise HTTPException(status_code=503, detail="Agent service error")

        except requests.exceptions.Timeout:
            logger.error(f"❌ MAS Agent request timeout after 120 seconds")
            logger.error(f"❌ Message was: {message[:100]}...")
            raise HTTPException(status_code=504, detail="Agent response timeout - The request took too long. Please try a simpler question or try again later.")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ MAS Agent connection error: {e}")
            raise HTTPException(status_code=503, detail="Unable to connect to agent service")
        except Exception as e:
            logger.error(f"❌ Unexpected error calling MAS agent: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            raise HTTPException(status_code=500, detail=f"Internal agent service error: {str(e)[:100]}")

    async def stream_message(self, message: str, context: Dict[str, Any], chat_history: List[ChatMessageModel] = None) -> AsyncGenerator[str, None]:
        """Simple streaming - just get response and return it"""
        try:
            logger.info(f"🔄 Starting stream for message: {message[:100]}...")

            # Get the regular response
            result = await self.send_message(message, context, chat_history)

            # Return it as a stream
            response_content = result.get("response", "")
            if response_content:
                logger.info(f"🔄 Streaming response with {len(response_content)} characters")
                yield f"data: {json.dumps({'content': response_content})}\n\n"
            else:
                logger.warning(f"⚠️ No response content to stream")

            yield f"data: {json.dumps({'done': True})}\n\n"

        except HTTPException as e:
            logger.error(f"❌ HTTP error in stream_message: {e.detail}")
            yield f"data: {json.dumps({'error': e.detail})}\n\n"
        except Exception as e:
            logger.error(f"❌ Error in stream_message: {e}")
            yield f"data: {json.dumps({'error': f'Failed to get response: {str(e)[:100]}'})}\n\n"

@router.post("/chat", response_model=ChatResponseModel)
async def agent_chat(
    request: ChatRequestModel,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Chat with MAS agent"""
    try:
        result = await agent_service.send_message(
            message=request.message,
            context=request.context,
            chat_history=request.chat_history
        )

        return ChatResponseModel(
            response=result["response"],
            confidence_score=result.get("confidence_score"),
            recommendation=result.get("recommendation"),
            evidence=result.get("evidence")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in agent chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process agent chat")

@router.post("/chat/stream")
async def agent_chat_stream(
    request: ChatRequestModel,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Simple streaming chat"""
    try:
        async def generate_stream():
            try:
                async for chunk in agent_service.stream_message(
                    message=request.message,
                    context=request.context,
                    chat_history=request.chat_history
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield f"data: {json.dumps({'error': 'Streaming error'})}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in streaming endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process streaming chat")

@router.get("/test")
async def test_agent_endpoint(agent_service: AgentService = Depends(get_agent_service)):
    """Test agent endpoint"""
    try:
        test_context = {
            "alert_id": "TEST-001",
            "customer_id": "test_customer"
        }

        result = await agent_service.send_message(
            message="Hello, this is a test.",
            context=test_context,
            chat_history=[]
        )

        return {
            "status": "success",
            "response": result["response"][:200] + "..." if len(result["response"]) > 200 else result["response"]
        }

    except HTTPException as e:
        return {"status": "error", "error": e.detail}
    except Exception as e:
        return {"status": "error", "error": str(e)}