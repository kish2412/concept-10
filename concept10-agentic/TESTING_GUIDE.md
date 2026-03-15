# Postman Testing Guide: Agentic Triage API

## Overview
This guide provides step-by-step instructions to test the `/specialist/triage/summarise` endpoint using Postman.

---

## 1. Environment Setup

### Create Postman Environment Variables

1. **Open Postman** → Click **Environments** (left sidebar)
2. **Create New** → Name it `Agentic-Local`
3. **Add these variables**:

| Variable Name | Initial Value | Current Value |
|---|---|---|
| `base_url` | `http://localhost:8001` | `http://localhost:8001` |
| `service_token` | `CeTxtXofSGKwZkJyJ4V1wGjbqArpXYZabpjCJoqaQvh6vM8KNUgFfFe2BhynSwg2NZcDkvlN0e6n24lb6x7__g` | `CeTxtXofSGKwZkJyJ4V1wGjbqArpXYZabpjCJoqaQvh6vM8KNUgFfFe2BhynSwg2NZcDkvlN0e6n24lb6x7__g` |
| `user_role` | `nurse` | `nurse` |
| `api_key` | (your OpenAI API key) | (your OpenAI API key) |

4. **Save** this environment and select it as active.

---

## 2. Create a New Request

1. **Click + Tab** → **New Request**
2. **Name it**: `Triage Summary - Generate`
3. **Method**: `POST`
4. **URL**: `{{base_url}}/specialist/triage/summarise`

---

## 3. Configure HTTP Headers

Click **Headers** tab and add:

| Key | Value | Description |
|---|---|---|
| `Authorization` | `Bearer {{service_token}}` | Authentication token |
| `X-User-Role` | `{{user_role}}` | User role (nurse, reception, doctor, admin) |
| `Content-Type` | `application/json` | Request body type |
| `Accept` | `application/json` | Response format |

---

## 4. Prepare Request Body

Click **Body** tab → Select **raw** → Select **JSON**

### Paste this complete TriageInput:

```json
{
  "visit_id": "visit_12345",
  "patient_id": "patient_67890",
  "request_id": "req_abcdef123456",
  "vitals": {
    "heart_rate": 95,
    "respiratory_rate": 20,
    "systolic_bp": 140,
    "diastolic_bp": 90,
    "temperature": 37.5,
    "oxygen_saturation": 98
  },
  "chief_complaint": "Severe chest pain radiating to left arm, started 1 hour ago",
  "patient_context": {
    "age": 58,
    "gender": "M",
    "medical_history": [
      "Hypertension",
      "Type 2 Diabetes",
      "Family history of MI"
    ]
  },
  "nurse_notes": "Patient appears anxious, diaphoretic. Pain level 8/10. No recent trauma.",
  "triage_start_timestamp": "2026-03-13T14:30:00Z"
}
```

---

## 5. Expected Success Response (200 OK)

When the request succeeds, you'll receive:

```json
{
  "request_id": "req_abcdef123456",
  "patient_id": "patient_67890",
  "visit_id": "visit_12345",
  "triage_summary": "58-year-old male with acute onset chest pain radiating to left arm. Elevated vitals (HR 95, BP 140/90), fever (37.5°C). Risk factors: HTN, DM2, positive family history. Clinical impression: Possible acute coronary syndrome requiring urgent evaluation.",
  "acuity_level": "HIGH",
  "emergency_flags": [
    "possible_acute_coronary_syndrome",
    "chest_pain_evaluation_urgent"
  ],
  "special_handling_flags": [
    "diabetes_screening_flag",
    "cardiac_monitoring_required"
  ],
  "recommended_disposition": "Immediate physician evaluation in resuscitation area",
  "specialist_recommendation": "EMERGENCY",
  "timestamp": "2026-03-13T14:31:00Z"
}
```

---

## 6. Common Error Responses & Fixes

### Error 1: 422 Unprocessable Entity
**Response**: Missing required fields
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "triage_start_timestamp"],
      "msg": "Field required"
    }
  ]
}
```
**Fix**: Verify all 8 required fields are in request body (see Section 4)

---

### Error 2: 403 Forbidden
**Response**: Insufficient role
```json
{
  "detail": "Insufficient role. Nurse or reception role minimum."
}
```
**Fix**: Verify `X-User-Role` header is set to `nurse`, `reception`, `doctor`, or `admin`

---

### Error 3: 401 Unauthorized
**Response**: Invalid or missing token
```json
{
  "detail": "Unauthorized"
}
```
**Fix**: Check that `Authorization: Bearer {{service_token}}` header is present and token matches `.env` `AGENTIC_SERVICE_TOKEN`

---

### Error 4: 500 Internal Server Error (Governance)
**Response**: Governance validation failed
```json
{
  "detail": "governance_validation_failed"
}
```
**Fix**: 
- Check agentic service logs for governance errors
- Verify `ENABLE_GOVERNANCE_VALIDATION=true` in `.env`
- If persistent, temporarily set `GOVERNANCE_FAIL_CLOSED=false`

---

### Error 5: 503 Service Unavailable
**Response**: Missing LLM dependency
```json
{
  "detail": "langchain_anthropic is required for triage llm_call_node"
}
```
**Fix**: Run in agentic service directory:
```bash
pip install langchain_anthropic
```

---

## 7. Test Scenarios

### Scenario A: Low Acuity Case
**Request Body** (Low-risk patient):
```json
{
  "visit_id": "visit_54321",
  "patient_id": "patient_11111",
  "request_id": "req_xyz789",
  "vitals": {
    "heart_rate": 72,
    "respiratory_rate": 16,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "temperature": 36.8,
    "oxygen_saturation": 99
  },
  "chief_complaint": "Minor ankle sprain from yesterday, mild swelling",
  "patient_context": {
    "age": 32,
    "gender": "F",
    "medical_history": []
  },
  "nurse_notes": "Patient able to bear weight with discomfort. RICE applied at home.",
  "triage_start_timestamp": "2026-03-13T15:00:00Z"
}
```
**Expected acuity_level**: `LOW`

---

### Scenario B: High Acuity Case
**Request Body** (High-risk patient):
```json
{
  "visit_id": "visit_98765",
  "patient_id": "patient_22222",
  "request_id": "req_urgent001",
  "vitals": {
    "heart_rate": 128,
    "respiratory_rate": 28,
    "systolic_bp": 92,
    "diastolic_bp": 55,
    "temperature": 39.2,
    "oxygen_saturation": 91
  },
  "chief_complaint": "Difficulty breathing, confusion, persistent cough",
  "patient_context": {
    "age": 72,
    "gender": "M",
    "medical_history": [
      "COPD",
      "Heart failure",
      "Pneumonia 2 months ago"
    ]
  },
  "nurse_notes": "Patient confused, uses supplemental O2 at home. Short of breath at rest. Productive cough with green sputum.",
  "triage_start_timestamp": "2026-03-13T15:30:00Z"
}
```
**Expected acuity_level**: `CRITICAL` or `HIGH`

---

## 8. Pre-Request Script (Automation)

Click **Pre-request Script** tab and paste this to auto-generate a unique request_id:

```javascript
// Generate unique request ID
const timestamp = Date.now();
const randomId = Math.random().toString(36).substring(2, 8);
pm.environment.set("request_id", `req_${timestamp}_${randomId}`);

// Log for debugging
console.log(`Request ID: ${pm.environment.get("request_id")}`);
```

Then update your JSON body to use `"request_id": "{{request_id}}"` instead of hardcoding.

---

## 9. Validation Checklist

Before sending request, verify:

- [ ] Environment `Agentic-Local` is selected
- [ ] URL is `{{base_url}}/specialist/triage/summarise`
- [ ] Method is `POST`
- [ ] Header `Authorization: Bearer {{service_token}}` present
- [ ] Header `X-User-Role: {{user_role}}` present
- [ ] Header `Content-Type: application/json` present
- [ ] All 8 required fields in request body:
  - [ ] `visit_id` (string, non-empty)
  - [ ] `patient_id` (string, non-empty)
  - [ ] `request_id` (string, non-empty)
  - [ ] `vitals` (object with 6 numeric fields)
  - [ ] `chief_complaint` (string, 10-500 chars)
  - [ ] `patient_context` (object with age: int, gender: M/F/Other, medical_history: array)
  - [ ] `nurse_notes` (string, 10-500 chars)
  - [ ] `triage_start_timestamp` (ISO 8601 datetime)
- [ ] Agentic service is running: `uvicorn api.app:app --reload --port 8001`
- [ ] OpenAI API key is valid (set in `.env` `OPENAI_API_KEY`)

---

## 10. cURL Alternative

If using cURL instead of Postman:

```bash
curl -X POST http://localhost:8001/specialist/triage/summarise \
  -H "Authorization: Bearer CeTxtXofSGKwZkJyJ4V1wGjbqArpXYZabpjCJoqaQvh6vM8KNUgFfFe2BhynSwg2NZcDkvlN0e6n24lb6x7__g" \
  -H "X-User-Role: nurse" \
  -H "Content-Type: application/json" \
  -d '{
    "visit_id": "visit_12345",
    "patient_id": "patient_67890",
    "request_id": "req_abcdef123456",
    "vitals": {
      "heart_rate": 95,
      "respiratory_rate": 20,
      "systolic_bp": 140,
      "diastolic_bp": 90,
      "temperature": 37.5,
      "oxygen_saturation": 98
    },
    "chief_complaint": "Severe chest pain radiating to left arm, started 1 hour ago",
    "patient_context": {
      "age": 58,
      "gender": "M",
      "medical_history": ["Hypertension", "Type 2 Diabetes", "Family history of MI"]
    },
    "nurse_notes": "Patient appears anxious, diaphoretic. Pain level 8/10. No recent trauma.",
    "triage_start_timestamp": "2026-03-13T14:30:00Z"
  }'
```

---

## 11. Debugging Tips

1. **Check agentic service logs**: Look for governance errors, LLM call failures, or parsing issues
2. **Verify `.env` variables**: Ensure `OPENAI_API_KEY`, `AGENTIC_SERVICE_TOKEN`, and `ENABLE_GOVERNANCE_VALIDATION` are set
3. **Check LangSmith traces**: Visit https://smith.langchain.com → Concept-10-dev project for request traces
4. **Enable verbose logging**: Set `LOG_LEVEL=DEBUG` in `.env` for detailed execution traces
5. **Inspect response headers**: Postman shows response headers; look for `X-Request-ID` matching your input

---

## 12. Next Steps

After successful testing:

1. Run the full frontend → backend → agentic service flow
2. Verify summary appears in frontend UI
3. Confirm LangSmith traces appear for each request
4. Run comprehensive test suite: `pytest tests/ -v`
