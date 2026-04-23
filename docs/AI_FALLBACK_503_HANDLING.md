# AURA AI Fallback & 503 Error Handling

## Overview
When the AURA system encounters a **503 Service Unavailable** or similar error from AI models, it now intelligently switches to the next available model with detailed logging.

## Implementation Details

### Helper Functions Added

#### 1. `_is_service_unavailable_error(error)`
Detects if an error represents service unavailability:
- Checks for HTTP status code 503
- Looks for common error phrases: "service unavailable", "high demand", "rate limit", "quota", etc.
- Returns `True` if service is unavailable, `False` for other errors

#### 2. `_get_api_error_code(error)`
Extracts the HTTP status code from an error:
- Checks `.status_code` attribute
- Parses error message for common codes (503, 429, 500)
- Returns the numeric code or 0 if not found

### Model Fallback Chain

The system now tries AI providers in this order:

```
1. Gemini (Google AI)
   ↓ (if 503 or unavailable)
2. DeepSeek (free tier)
   ↓ (if 503 or unavailable)
3. Groq (Llama 3.3 70B)
   ↓ (if 503 or unavailable)
4. OpenAI (gpt-4o-mini)
   ↓ (if 503 or unavailable)
5. Local Fallback (context-aware responses)
```

### Enhanced Error Logging

When a model fails with a 503 error, the logs now show:

```
WARNING: DeepSeek unavailable (error 503): This model is currently experiencing high demand. Switching to Groq...
WARNING: Groq unavailable (error 503): Service temporarily overloaded. Switching to OpenAI...
ERROR: OpenAI unavailable (error 503): Too many requests. Using local fallback...
INFO: All external AI models exhausted. Using local fallback (REQUIRE_AI=false)
```

### User-Facing Error Messages

**When 503 is detected:**
```
"AI is temporarily unavailable. Our models are experiencing high demand. Please try again in a few moments."
```

**For immediate fallback response:**
- The system automatically generates a contextual response using the local fallback function
- Maintains conversation coherence even when external APIs are busy

## Files Modified

- **[aura/services/ai_service.py](aura/services/ai_service.py)**
  - Added `import time` for potential retry logic
  - Added `_is_service_unavailable_error()` function
  - Added `_get_api_error_code()` function
  - Updated `_generate_with_fallback()` with 503-specific logging
  - Updated `generate_study_response()` with 503 detection
  - Updated `generate_mental_response()` with 503 detection and fallback chain

## Usage Example

```python
from aura.services.ai_service import generate_mental_response

# This automatically handles 503 errors and switches models
response = generate_mental_response(
    user_message="I'm feeling stressed about exams",
    chat_history=[],
    predicted_mood="anxious",
    calculated_stress=75,
    risk_level="MEDIUM_RISK"
)

# If Gemini returns 503:
# → Tries DeepSeek
# If DeepSeek returns 503:
# → Tries Groq
# If Groq returns 503:
# → Tries OpenAI
# If OpenAI returns 503:
# → Uses local fallback (always works)
```

## Log Output

You'll see logs like this in your application logs:

```
[WARNING] DeepSeek unavailable (error 503): This model is currently experiencing high demand. Switching to Groq...
[INFO] Groq (Llama) response (487 chars)
```

Or:

```
[WARNING] Gemini mental API unavailable (error 503): ... Using fallback AI chain...
[WARNING] DeepSeek unavailable (error 503): ... Switching to Groq...
[WARNING] Groq unavailable (error 429): ... Switching to OpenAI...
[INFO] OpenAI fallback response (524 chars)
```

## Benefits

✅ **User Experience**: Seamless fallback without visible errors  
✅ **Observability**: Detailed logging of which models fail and why  
✅ **Reliability**: Multiple fallbacks ensure service continuity  
✅ **Cost Optimization**: Uses free tier models (DeepSeek, Groq) before paid (OpenAI)  
✅ **Graceful Degradation**: Local fallback always available as last resort  

## Environment Variables

No new environment variables required, but existing ones control behavior:

- `REQUIRE_AI=false` (default) → Uses local fallback if all APIs fail
- `REQUIRE_AI=true` → Returns error message if all APIs fail
- `GEMINI_API_KEY` → Gemini primary model
- `DEEPSEEK_API_KEY` → First fallback
- `GROQ_API_KEY` → Second fallback
- `OPENAI_API_KEY` → Third fallback

## Testing

To test the 503 handling locally:

```python
# Simulate a 503 error by temporarily disabling an API key
os.environ['GEMINI_API_KEY'] = ''

# This will skip Gemini and move to DeepSeek automatically
response = generate_study_response("What is calculus?")
```

## Monitoring

Monitor your logs for:
- Frequency of 503 errors from each provider
- Which fallback is being used most often
- Average response time when falling back

This helps identify which API providers are most stable and cost-effective for your use case.
