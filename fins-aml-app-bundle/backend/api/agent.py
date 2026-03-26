"""
MAS Agent API endpoints
"""

import os
import logging
import re
import requests
import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, AsyncGenerator

from backend.models.schemas import ChatRequestModel, ChatResponseModel, ChatMessageModel
from backend import config

router = APIRouter()
logger = logging.getLogger(__name__)

# MAS Agent endpoint configuration
MAS_ENDPOINT_URL = config.MAS_ENDPOINT_URL

# Chunk size for simulated streaming (in characters)
STREAM_CHUNK_SIZE = 80
STREAM_CHUNK_DELAY = 0.03  # seconds between chunks


def _extract_final_answer(result: dict) -> str:
    """Extract only the final assistant message from MAS response.

    The MAS output array contains multiple items: function_call,
    function_call_output, and message types.  We only want the last
    message-type item which holds the human-readable answer.
    """
    if "output" in result and isinstance(result["output"], list):
        items = result["output"]
        logger.info(f"🤖 Processing output array with {len(items)} items")

        # Walk backwards to find the last 'message' type item
        for item in reversed(items):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            role = item.get("role", "")

            # Skip tool calls and tool outputs
            if item_type in ("function_call", "function_call_output"):
                continue

            # Accept message-type items from the assistant
            if item_type == "message" and role == "assistant":
                content = item.get("content", [])
                if isinstance(content, list):
                    texts = []
                    for c in content:
                        if isinstance(c, dict) and "text" in c:
                            texts.append(c["text"])
                    if texts:
                        return "\n".join(texts).strip()
                elif isinstance(content, str) and content.strip():
                    return content.strip()

        # Fallback: grab any text from any output item
        all_texts = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # Skip function calls entirely
            if item.get("type") in ("function_call", "function_call_output"):
                continue
            content = item.get("content", [])
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        all_texts.append(c["text"])
            elif isinstance(content, str):
                all_texts.append(content)
        if all_texts:
            return "\n".join(all_texts).strip()

    # Handle simple string output
    if "output" in result and isinstance(result["output"], str):
        return result["output"].strip()

    # Other formats
    for key in ("response", "text"):
        if key in result and isinstance(result[key], str):
            return result[key].strip()

    logger.warning(f"⚠️ Could not extract answer. Keys: {list(result.keys())}")
    return ""


def _format_response(text: str) -> str:
    """Clean up and format the response text for chat display.

    - Collapse very large markdown tables to a summary
    - Trim excessive whitespace
    """
    if not text:
        return text

    # Collapse very large markdown tables (>20 rows) into a summary
    def _collapse_table(match):
        table_text = match.group(0)
        rows = [r for r in table_text.strip().split("\n") if r.strip()]
        # rows[0] = header, rows[1] = separator, rows[2:] = data
        if len(rows) <= 22:  # header + sep + 20 data rows
            return table_text

        header = rows[0]
        separator = rows[1]
        data_rows = rows[2:]
        shown = data_rows[:10]
        remaining = len(data_rows) - 10

        collapsed = "\n".join([header, separator] + shown)
        collapsed += f"\n\n*... and {remaining} more rows (showing top 10 of {len(data_rows)})*\n"
        return collapsed

    # Match markdown tables: lines starting with |
    text = re.sub(
        r'(?:^\|.+\|$\n?){4,}',
        _collapse_table,
        text,
        flags=re.MULTILINE,
    )

    return text.strip()


async def get_agent_service():
    """Get agent service with authentication (OAuth M2M preferred)"""
    try:
        token = config.get_oauth_token()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Agent authentication not configured")
    return AgentService(token)


class AgentService:
    """Service for interacting with MAS Agent endpoint"""

    def __init__(self, token: str):
        self.token = token
        self.endpoint_url = MAS_ENDPOINT_URL

    def _build_payload(self, message: str, context: Dict[str, Any],
                       chat_history: List[ChatMessageModel] = None) -> dict:
        """Build the request payload for the MAS endpoint."""
        conversation = []
        if chat_history:
            logger.info(f"🤖 Including {len(chat_history)} messages from chat history")
            for msg in chat_history[-5:]:
                conversation.append({"role": msg.role, "content": msg.content})
        conversation.append({"role": "user", "content": message})

        conversation_id = f"alert_{context.get('alert_id', 'unknown')}_{context.get('customer_id', 'unknown')}"
        logger.info(f"🤖 Conversation ID: {conversation_id}")

        return {
            "input": conversation,
            "databricks_options": {
                "conversation_id": conversation_id,
                "return_trace": True,
            },
            "context": {
                "conversation_id": conversation_id,
                "user_id": "analyst",
            },
        }

    def _call_endpoint(self, payload: dict) -> dict:
        """Make the synchronous HTTP call to the MAS endpoint."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        logger.info(f"🤖 Sending request to MAS endpoint: {self.endpoint_url}")
        logger.info(f"🤖 Payload size: {len(json.dumps(payload))} bytes")

        response = requests.post(
            self.endpoint_url, json=payload, headers=headers, timeout=120,
        )

        if response.status_code != 200:
            logger.error(f"❌ MAS Agent error: {response.status_code} - {response.text[:500]}")
            raise HTTPException(status_code=503, detail="Agent service error")

        logger.info("✅ MAS Agent Response received - Status: 200")
        return response.json()

    async def send_message(self, message: str, context: Dict[str, Any],
                           chat_history: List[ChatMessageModel] = None) -> Dict[str, Any]:
        """Send message to MAS agent endpoint and return final answer."""
        try:
            logger.info(f"🤖 MAS Agent Request - Message: {message[:100]}...")
            logger.info(f"🤖 Context: alert_id={context.get('alert_id')}, customer_id={context.get('customer_id')}")

            payload = self._build_payload(message, context, chat_history)

            # Run blocking HTTP call in a separate thread so the event loop
            # stays free for asyncio.sleep() in the streaming generator.
            result = await asyncio.to_thread(self._call_endpoint, payload)

            logger.info(f"🤖 Response structure keys: {list(result.keys())}")
            response_text = _extract_final_answer(result)
            response_text = _format_response(response_text)

            logger.info(f"✅ Final response length: {len(response_text)} characters")

            return {
                "response": response_text or "I received your request but couldn't generate a response.",
                "confidence_score": 0.9,
                "recommendation": None,
                "evidence": [],
            }

        except requests.exceptions.Timeout:
            logger.error(f"❌ MAS Agent request timeout after 120 seconds")
            raise HTTPException(
                status_code=504,
                detail="Agent response timeout - The request took too long. Please try a simpler question or try again later.",
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ MAS Agent connection error: {e}")
            raise HTTPException(status_code=503, detail="Unable to connect to agent service")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error calling MAS agent: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            raise HTTPException(status_code=500, detail=f"Internal agent service error: {str(e)[:100]}")

    async def stream_message(self, message: str, context: Dict[str, Any],
                             chat_history: List[ChatMessageModel] = None) -> AsyncGenerator[str, None]:
        """Stream the response in small chunks for a typewriter effect."""
        try:
            logger.info(f"🔄 Starting stream for message: {message[:100]}...")

            # Get the full response first
            result = await self.send_message(message, context, chat_history)
            response_content = result.get("response", "")

            if not response_content:
                logger.warning("⚠️ No response content to stream")
                yield f"data: {json.dumps({'done': True})}\n\n"
                return

            logger.info(f"🔄 Streaming {len(response_content)} characters in chunks")

            # Stream in word-aware chunks for natural reading
            pos = 0
            total = len(response_content)
            while pos < total:
                # Find a good break point (end of word or line)
                end = min(pos + STREAM_CHUNK_SIZE, total)
                if end < total:
                    # Try to break at a word boundary
                    space_idx = response_content.rfind(" ", pos, end + 20)
                    newline_idx = response_content.rfind("\n", pos, end + 10)
                    break_at = max(space_idx, newline_idx)
                    if break_at > pos:
                        end = break_at + 1

                chunk = response_content[pos:end]
                yield f"data: {json.dumps({'content': chunk})}\n\n"
                pos = end
                await asyncio.sleep(STREAM_CHUNK_DELAY)

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
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
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