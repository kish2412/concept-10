#!/usr/bin/env python3
"""Quick test of agentic endpoint"""
import asyncio
import httpx
from datetime import datetime

async def test_endpoint():
    # Create a properly-formatted TriageInput
    payload = {
        "visit_id": "test-visit-123",
        "patient_id": "patient-456",
        "request_id": "req-789",
        "vitals": {
            "temperature_celsius": 37.0,
            "heart_rate_bpm": 72,
            "respiratory_rate_rpm": 16,
            "systolic_bp_mmhg": 120,
            "diastolic_bp_mmhg": 80,
            "spo2_percent": 98.0,
            "gcs_score": None,
            "pain_score": 5,
            "weight_kg": 70.0,
            "height_cm": 175.0,
        },
        "chief_complaint": {
            "primary_complaint": "Headache",
            "onset_description": "Sudden",
            "duration_minutes": 120,
            "severity": "moderate",
            "associated_symptoms": ["Nausea", "Sensitivity to light"],
        },
        "patient_context": {
            "age_years": 35,
            "sex": "M",
            "is_pregnant": False,
            "gestational_weeks": None,
            "known_allergies": ["Penicillin"],
            "current_medications": ["Aspirin"],
            "relevant_history": ["Migraine history"],
            "mobility_status": "ambulatory",
            "communication_barrier": False,
            "preferred_language": "en",
            "arrived_by": "walk_in",
        },
        "nurse_notes": {
            "free_text": "Patient presents with severe headache. Vitals stable.",
            "nurse_initial_concern": "routine",
            "nurse_id": "nurse-001",
            "assessment_timestamp": datetime.now().isoformat(),
        },
        "triage_start_timestamp": datetime.now().isoformat(),
    }
    
    print("Testing agentic service endpoint...")
    print(f"Sending properly-formatted TriageInput...")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "http://localhost:8001/specialist/triage/summarise",
                json=payload,
                headers={
                    "Authorization": "Bearer CeTxtXofSGKwZkJyJ4V1wGjbqArpXYZabpjCJoqaQvh6vM8KNUgFfFe2BhynSwg2NZcDkvlN0e6n24lb6x7__g",
                    "X-User-Role": "nurse"
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: X-Request-ID={response.headers.get('X-Request-ID')}, X-Trace-ID={response.headers.get('X-Trace-ID')}")
            if response.status_code == 200:
                print(f"Response Summary:")
                try:
                    data = response.json()
                    print(f"  - Acuity Level: {data.get('acuity_level')}")
                    print(f"  - Immediate Action Required: {data.get('immediate_action_required')}")
                    print(f"  - Clinical Summary Exists: {bool(data.get('clinical_summary'))}")
                except:
                    print(f"  < Could not parse JSON >")
            else:
                print(f"Response Body (first 500 chars): {response.text[:500]}")
            
            if response.status_code == 200:
                print("\n✓ SUCCESS")
            else:
                print(f"\n✗ FAILED with status {response.status_code}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint())
