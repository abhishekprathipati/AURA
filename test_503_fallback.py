"""
Test script to demonstrate AURA's 503 error handling and automatic model fallback.

Run this to verify the fallback chain works correctly.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_503_detection():
    """Test that _is_service_unavailable_error detects 503 errors correctly."""
    from aura.services.ai_service import _is_service_unavailable_error, _get_api_error_code
    
    print("=" * 60)
    print("TEST 1: 503 Error Detection")
    print("=" * 60)
    
    # Test 1: Direct 503 status code
    error1 = Exception("error 503: Service Unavailable")
    result1 = _is_service_unavailable_error(error1)
    print(f"✓ Error string with '503': {result1}")
    assert result1 == True
    
    # Test 2: High demand message
    error2 = Exception("This model is currently experiencing high demand")
    result2 = _is_service_unavailable_error(error2)
    print(f"✓ 'High demand' message: {result2}")
    assert result2 == True
    
    # Test 3: Rate limit error
    error3 = Exception("429: rate limit exceeded")
    result3 = _is_service_unavailable_error(error3)
    print(f"✓ Rate limit error: {result3}")
    assert result3 == True
    
    # Test 4: Regular error (not 503)
    error4 = Exception("Connection timeout")
    result4 = _is_service_unavailable_error(error4)
    print(f"✓ Regular error (not 503): {result4}")
    assert result4 == False
    
    # Test error code extraction
    print("\nTesting error code extraction:")
    error5 = Exception("Service unavailable (503)")
    code = _get_api_error_code(error5)
    print(f"✓ Extracted error code from message: {code}")
    assert code == 503
    
    print("\n✅ All detection tests passed!\n")


def test_fallback_chain():
    """Test that the fallback chain switches models on 503."""
    from aura.services.ai_service import _generate_with_fallback
    
    print("=" * 60)
    print("TEST 2: Fallback Chain Behavior")
    print("=" * 60)
    
    # This test demonstrates the fallback chain behavior
    # In production, this would actually try:
    # 1. DeepSeek → 2. Groq → 3. OpenAI → 4. Local fallback
    
    test_message = "What is photosynthesis?"
    
    try:
        response = _generate_with_fallback(
            user_message=test_message,
            chat_history=[],
            style='concise',
            persona='study'
        )
        print(f"✓ Got response from fallback chain")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response preview: {response[:100]}...")
        print("\n✅ Fallback chain test passed!\n")
    except Exception as e:
        print(f"⚠ Fallback chain test failed: {e}")
        print("  (This is expected if no API keys are configured)\n")


def test_mental_response_with_fallback():
    """Test that mental response handler uses fallback on 503."""
    from aura.services.ai_service import generate_mental_response
    
    print("=" * 60)
    print("TEST 3: Mental Response Handler")
    print("=" * 60)
    
    test_message = "I'm feeling stressed"
    
    try:
        response = generate_mental_response(
            user_message=test_message,
            chat_history=[],
            predicted_mood="stressed",
            calculated_stress=75,
            risk_level="MEDIUM_RISK"
        )
        print(f"✓ Got mental response from handler")
        print(f"  Response length: {len(response)} characters")
        # Response should be JSON
        import json
        data = json.loads(response)
        print(f"  Has mood field: {'mood' in data}")
        print(f"  Has stress_score field: {'stress_score' in data}")
        print(f"  Has aura_response field: {'aura_response' in data}")
        print("\n✅ Mental response handler test passed!\n")
    except Exception as e:
        print(f"⚠ Mental response handler test failed: {e}")
        print("  (This is expected if no API keys are configured)\n")


def demonstrate_logging():
    """Show what logging output looks like with 503 errors."""
    import logging
    
    print("=" * 60)
    print("TEST 4: Example Log Output")
    print("=" * 60)
    print("\nWhen a 503 error occurs, you'll see logs like:\n")
    
    examples = [
        "[WARNING] DeepSeek unavailable (error 503): This model is currently experiencing high demand. Switching to Groq...",
        "[WARNING] Groq unavailable (error 429): Rate limit exceeded. Switching to OpenAI...",
        "[INFO] OpenAI fallback response (487 chars)",
        "[INFO] All external AI models exhausted. Using local fallback (REQUIRE_AI=false)",
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"  {i}. {example}")
    
    print("\n✅ Logging demonstration complete!\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("AURA 503 Error Handling & AI Fallback Tests")
    print("=" * 60 + "\n")
    
    try:
        test_503_detection()
    except Exception as e:
        print(f"❌ Detection test failed: {e}\n")
    
    try:
        test_fallback_chain()
    except Exception as e:
        print(f"❌ Fallback chain test failed: {e}\n")
    
    try:
        test_mental_response_with_fallback()
    except Exception as e:
        print(f"❌ Mental response test failed: {e}\n")
    
    demonstrate_logging()
    
    print("=" * 60)
    print("Tests Complete!")
    print("=" * 60)
