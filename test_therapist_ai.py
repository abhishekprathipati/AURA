import os
import sys
import json

# Ensure Python can find the `services` module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import predict_emotion_and_stress, generate_mental_response
from services.risk_service import predict_risk_level

def run_test():
    test_messages = [
        "I have so many assignments and I feel like I can't handle anything",
        "I want to give up everything is hopeless",
        "I am actually really excited but also quite nervous for tomorrow"
    ]

    for msg in test_messages:
        print(f"\n--- Testing message: '{msg}' ---")
        try:
            from services.ai_service import predict_emotion_and_stress, generate_mental_response
            from services.risk_service import predict_risk_level
            
            predicted_mood, calculated_stress = predict_emotion_and_stress(msg)
            risk_level = predict_risk_level(calculated_stress, msg)
            memory_context = {"average_stress": 60, "dominant_emotion": "Anxious"}
            
            response_str = generate_mental_response(
                msg, chat_history=[], kind='mental', conversation_id='test',
                predicted_mood=predicted_mood, calculated_stress=calculated_stress,
                risk_level=risk_level, memory_context=memory_context
            )
            parsed = json.loads(response_str)
            print("Mood:", parsed.get('mood'))
            print("Stress:", parsed.get('stress_score'))
            print("Risk Level:", parsed.get('risk_level'))
            print("Response:", parsed.get('aura_response')[:100] + "...")
        except Exception as e:
            print(f"Error: {e}")

    print("\nFinished Phase 3 Test.")

if __name__ == "__main__":
    print("Starting Phase 3 AI Therapist architecture test...")
    run_test()
