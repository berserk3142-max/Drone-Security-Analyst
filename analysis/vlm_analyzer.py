"""
VLM Frame Analyzer - Analyzes drone surveillance frames using OpenAI GPT-4o-mini.

Acts as the AI "vision" component, taking frame descriptions + telemetry
and producing structured security analysis with object detection,
event classification, and risk assessment.
"""

import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


# Configure OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


ANALYSIS_SYSTEM_PROMPT = """You are an expert security analyst monitoring drone surveillance footage for a secure industrial complex. 

For each frame description provided, analyze the scene and produce a structured security assessment.

Your analysis MUST be a valid JSON object with exactly these fields:
{
    "objects": ["list of detected objects/people/vehicles"],
    "event_type": "one of: vehicle_entry, vehicle_exit, person_detected, delivery, employee_activity, maintenance, wildlife, security_patrol, suspicious_activity, perimeter_breach, unauthorized_access, parking_violation, door_anomaly, normal_operations, theft_attempt",
    "risk_level": "one of: low, medium, high, critical",
    "is_suspicious": true/false,
    "description": "Brief security assessment of the scene (1-2 sentences)",
    "recommended_action": "What action should be taken (e.g., 'Log and continue', 'Dispatch security', 'Trigger alarm')"
}

Assessment guidelines:
- Business hours are 06:00-22:00. Activity outside these hours gets elevated scrutiny.
- Known employee vehicles: White Toyota Camry, Silver Honda Civic, Black BMW X5, Blue Ford F150, Red Chevrolet Silverado
- Known delivery services: FedEx, UPS
- Any person without a badge near the perimeter is suspicious.
- Vehicles without employee stickers warrant attention.
- Repeated appearances of the same vehicle may indicate surveillance.
- Ski masks, face coverings (non-medical), and tools near restricted areas are critical threats.
- Open doors after hours are always reported.

CRITICAL: Return ONLY the JSON object. No markdown, no code blocks, no explanation."""


def analyze_frame(frame_description: str, telemetry: dict) -> dict:
    """
    Analyze a single frame using OpenAI GPT-4o-mini.

    Args:
        frame_description: Text description of what the drone camera sees
        telemetry: Dict with drone telemetry (time, location, altitude, etc.)

    Returns:
        Structured analysis dict with objects, event_type, risk_level, etc.
    """
    # Build the prompt with context
    prompt = f"""Analyze this drone surveillance frame:

TELEMETRY DATA:
- Time: {telemetry.get('time', 'unknown')}
- Location: {telemetry.get('location', 'unknown')}
- Drone ID: {telemetry.get('drone_id', 'unknown')}
- Altitude: {telemetry.get('altitude_m', 'unknown')}m
- Property: {telemetry.get('property', 'unknown')}

FRAME DESCRIPTION:
{frame_description}

Provide your security analysis as a JSON object."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )

        response_text = response.choices[0].message.content.strip()

        # Clean response — remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

        analysis = json.loads(response_text)

        # Ensure all required fields exist
        analysis.setdefault("objects", [])
        analysis.setdefault("event_type", "normal_operations")
        analysis.setdefault("risk_level", "low")
        analysis.setdefault("is_suspicious", False)
        analysis.setdefault("description", "No analysis available")
        analysis.setdefault("recommended_action", "Log and continue")

        return analysis

    except json.JSONDecodeError:
        # Fallback: try to extract JSON from the response
        return _fallback_parse(response_text, frame_description, telemetry)
    except Exception as e:
        print(f"  [VLM Error] {e}")
        return _create_fallback_analysis(frame_description, telemetry)


def _fallback_parse(response_text: str, frame_description: str, telemetry: dict) -> dict:
    """Try harder to extract JSON from a messy response."""
    import re
    json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return _create_fallback_analysis(frame_description, telemetry)


def _create_fallback_analysis(frame_description: str, telemetry: dict) -> dict:
    """Create a basic analysis when the LLM fails."""
    desc_lower = frame_description.lower()

    objects = []
    if any(v in desc_lower for v in ["car", "truck", "vehicle", "van", "sedan", "suv"]):
        objects.append("Vehicle")
    if any(p in desc_lower for p in ["person", "people", "man", "woman", "individual", "guard"]):
        objects.append("Person")

    is_suspicious = any(w in desc_lower for w in [
        "suspicious", "dark clothing", "no badge", "ski mask",
        "unauthorized", "breach", "climbing"
    ])

    return {
        "objects": objects,
        "event_type": "suspicious_activity" if is_suspicious else "normal_operations",
        "risk_level": "high" if is_suspicious else "low",
        "is_suspicious": is_suspicious,
        "description": f"Fallback analysis: {frame_description[:100]}",
        "recommended_action": "Dispatch security" if is_suspicious else "Log and continue",
    }
