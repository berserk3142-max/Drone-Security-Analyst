"""
Security Agent — LangGraph-based AI agent for drone security analysis.

Orchestrates frame analysis using custom tools, maintains conversation memory
for cross-frame pattern recognition, and produces intelligent security assessments.
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import OPENAI_API_KEY, OPENAI_MODEL
from agent.prompts import SECURITY_AGENT_SYSTEM_PROMPT
from agent.tools import log_event, check_alert_rules, query_past_events, generate_summary, init_tools
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager


class SecurityAgent:
    """LangGraph-based security analyst agent with memory and custom tools."""

    def __init__(self, sqlite_store: SQLiteStore = None,
                 chroma_store: ChromaStore = None,
                 alert_manager: AlertManager = None):
        """
        Initialize the security agent.

        Args:
            sqlite_store: SQLiteStore instance for structured storage
            chroma_store: ChromaStore instance for semantic search
            alert_manager: AlertManager instance for alert evaluation
        """
        # Initialize stores
        self.sqlite_store = sqlite_store or SQLiteStore()
        self.chroma_store = chroma_store or ChromaStore()
        self.alert_manager = alert_manager or AlertManager()

        # Initialize tool dependencies
        init_tools(self.sqlite_store, self.chroma_store, self.alert_manager)

        # Define tools
        self.tools = [log_event, check_alert_rules, query_past_events, generate_summary]

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.1,
        )

        # Create LangGraph react agent
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=SECURITY_AGENT_SYSTEM_PROMPT,
        )

        # Store message history for cross-frame context
        self.message_history = []

    def process_frame(self, frame: dict, analysis: dict, telemetry: dict) -> dict:
        """
        Process a single frame through the agent.

        Args:
            frame: Raw frame dict (frame_id, time, location, description)
            analysis: VLM analysis result dict
            telemetry: Telemetry data dict

        Returns:
            Dict with agent_response, alerts, and actions taken
        """
        # Build the input prompt for the agent
        input_text = self._build_frame_input(frame, analysis, telemetry)

        try:
            # Add the new message to history
            messages = self.message_history + [{"role": "user", "content": input_text}]

            result = self.agent.invoke(
                {"messages": messages},
                config={"recursion_limit": 15},
            )

            # Extract the final AI message
            output_messages = result.get("messages", [])
            agent_response = "No response generated"
            if output_messages:
                # Get the last AI message
                for msg in reversed(output_messages):
                    if hasattr(msg, 'content') and msg.content and hasattr(msg, 'type') and msg.type == 'ai':
                        agent_response = msg.content
                        break

            # Update message history with the user message and final AI response
            # Keep history manageable (last 10 exchanges)
            self.message_history.append({"role": "user", "content": input_text})
            self.message_history.append({"role": "assistant", "content": agent_response})
            if len(self.message_history) > 20:
                self.message_history = self.message_history[-20:]

            # Extract alerts from the response
            alerts = self.alert_manager.fired_alerts[-5:]  # Last 5 alerts

            return {
                "agent_response": agent_response,
                "alerts": alerts,
                "steps": len([m for m in output_messages if hasattr(m, 'type') and m.type == 'tool']),
                "success": True,
            }

        except Exception as e:
            error_msg = f"Agent error processing frame {frame.get('frame_id', '?')}: {str(e)}"
            # Still try to log the event directly
            try:
                self._direct_log(frame, analysis)
            except Exception:
                pass

            return {
                "agent_response": error_msg,
                "alerts": [],
                "steps": 0,
                "success": False,
            }

    def _build_frame_input(self, frame: dict, analysis: dict, telemetry: dict) -> str:
        """Build a comprehensive input string for the agent."""
        import json

        # Merge frame and analysis info for tool calls
        tool_data = {
            "frame_id": frame.get("frame_id", 0),
            "timestamp": frame.get("time", ""),
            "time": frame.get("time", ""),
            "location": frame.get("location", ""),
            "objects": analysis.get("objects", []),
            "event_type": analysis.get("event_type", ""),
            "risk_level": analysis.get("risk_level", ""),
            "is_suspicious": analysis.get("is_suspicious", False),
            "description": analysis.get("description", ""),
            "raw_description": frame.get("description", ""),
            "recommended_action": analysis.get("recommended_action", ""),
        }
        tool_json = json.dumps(tool_data)

        return f"""NEW FRAME FOR ANALYSIS:

Frame ID: {frame.get('frame_id')}
Time: {frame.get('time')}
Location: {frame.get('location')}
Drone Altitude: {telemetry.get('altitude_m', 'N/A')}m | Battery: {telemetry.get('battery_pct', 'N/A')}%

VLM Analysis Result:
- Objects Detected: {', '.join(analysis.get('objects', ['None']))}
- Event Type: {analysis.get('event_type', 'unknown')}
- Risk Level: {analysis.get('risk_level', 'unknown')}
- Suspicious: {analysis.get('is_suspicious', False)}
- Assessment: {analysis.get('description', 'N/A')}
- Recommended Action: {analysis.get('recommended_action', 'N/A')}

Raw Frame Description: {frame.get('description', 'N/A')}

INSTRUCTIONS:
1. Use the log_event tool to log this event. Pass this JSON: {tool_json}
2. Use the check_alert_rules tool to evaluate alerts. Pass the same JSON.
3. Based on your memory of previous frames, note any patterns (repeat vehicles, escalating threats, etc.)
4. Provide your security assessment."""

    def _direct_log(self, frame: dict, analysis: dict):
        """Fallback: directly log to stores without going through the agent."""
        self.sqlite_store.insert_frame(
            frame_id=frame.get("frame_id", 0),
            timestamp=frame.get("time", ""),
            location=frame.get("location", ""),
            objects_detected=analysis.get("objects", []),
            event_type=analysis.get("event_type", ""),
            risk_level=analysis.get("risk_level", ""),
            is_suspicious=analysis.get("is_suspicious", False),
            raw_description=frame.get("description", ""),
            analysis_summary=analysis.get("description", ""),
        )
        self.chroma_store.add_frame(
            frame_id=frame.get("frame_id", 0),
            timestamp=frame.get("time", ""),
            location=frame.get("location", ""),
            description=frame.get("description", ""),
            event_type=analysis.get("event_type", ""),
            risk_level=analysis.get("risk_level", ""),
        )

    def get_summary(self) -> str:
        """Ask the agent to generate a session summary."""
        try:
            result = self.agent.invoke({
                "messages": [
                    {"role": "user", "content": "Generate a comprehensive security summary for this monitoring session using the generate_summary tool."}
                ]
            })
            output_messages = result.get("messages", [])
            for msg in reversed(output_messages):
                if hasattr(msg, 'content') and msg.content and hasattr(msg, 'type') and msg.type == 'ai':
                    return msg.content
            return "Summary generation failed."
        except Exception as e:
            return f"Error generating summary: {e}"

    def reset(self):
        """Reset the agent's memory and stores for a new session."""
        self.message_history.clear()
        self.alert_manager.reset()
