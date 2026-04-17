# TODO: ARCHITECTURE #16 - No background task/queue system
#   AI response generation is synchronous and blocks the request thread.
#   For production scalability, consider:
#   - Using Celery with Redis/RabbitMQ for async task processing
#   - Implementing a job queue (RQ, Dramatiq, Huey) for long-running AI calls
#   - Adding request timeouts and circuit breakers for API calls
#   - Caching common responses to reduce API load
#   This would improve response times and prevent thread starvation under load.

# TODO #28 (SCALABILITY): Synchronous AI API Calls
#   Current implementation makes blocking HTTP calls to AI providers (Gemini, OpenAI, Groq).
#   For high-concurrency production deployments, consider:
#
#   1. Async/Await Pattern:
#      - Use `aiohttp` or `httpx` async clients instead of synchronous SDK calls
#      - Requires Flask-to-ASGI migration (e.g., Quart, FastAPI) or background workers
#      - Example: `async def generate_mental_response(...)`
#
#   2. Background Task Queue:
#      - Offload AI calls to Celery/RQ workers
#      - Return a task_id immediately, poll for results
#      - Better for long-running analysis tasks
#
#   3. Streaming Responses:
#      - Use SSE (Server-Sent Events) to stream AI responses token-by-token
#      - Improves perceived latency for users
#
#   Architectural changes needed:
#      - Migrate from Flask (WSGI) to async framework or use gevent/eventlet
#      - Update database calls to async (motor for MongoDB)
#      - Add proper async context management

# FIX #34: Model versioning — configurable via env var, logged with responses.
# FIX #28: Async migration documented in comments.

import os
import logging
import json
from typing import List, Dict, Any, Optional

# FIX #34: Model version tracking
AURA_AI_MODEL_VERSION = os.getenv('AURA_AI_MODEL_VERSION', 'v1.0.0')
from pathlib import Path

FLASK_ENV = os.getenv('FLASK_ENV', 'production').strip().lower()
ENABLE_LOCAL_EMOTION_MODEL = os.getenv(
    'AURA_ENABLE_LOCAL_EMOTION_MODEL',
    'true'
).strip().lower() == 'true'

# Use google.genai (new recommended SDK). Fallback to Groq/OpenAI if Gemini quota exhausted.
try:
    from google.genai import Client, types
except ImportError:
    Client = None
    types = None

# Advanced Local Emotion Model using HuggingFace Transformers
if ENABLE_LOCAL_EMOTION_MODEL:
    try:
        from transformers import pipeline
        # Load model lazily to avoid blocking boot time
        _emotion_model = None

        def get_emotion_model():
            global _emotion_model
            if _emotion_model is None:
                logger.info("Loading go_emotions model into memory...")
                _emotion_model = pipeline("text-classification", model="SamLowe/roberta-base-go_emotions", top_k=None)
            return _emotion_model
    except ImportError:
        pipeline = None
        _emotion_model = None

        def get_emotion_model():
            return None
else:
    pipeline = None
    _emotion_model = None

    def get_emotion_model():
        return None

# Optional OpenAI fallback
try:
    from openai import OpenAI as OpenAIClient
except ImportError:
    OpenAIClient = None

# Optional Groq (free, fast alternative)
try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
if not ENABLE_LOCAL_EMOTION_MODEL:
    logger.info("AURA local emotion model disabled (AURA_ENABLE_LOCAL_EMOTION_MODEL=false)")

GEMINI_API_KEY   = os.getenv('GEMINI_API_KEY',   '').strip()
OPENAI_API_KEY   = os.getenv('OPENAI_API_KEY',   '').strip()
GROQ_API_KEY     = os.getenv('GROQ_API_KEY',     '').strip()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '').strip()
STRUCTURED_RESPONSES = os.getenv('AURA_STRUCTURED_RESPONSES', 'true').strip().lower() == 'true'
REQUIRE_AI = os.getenv('AURA_REQUIRE_AI', 'false').strip().lower() == 'true'
RESPOND_DYNAMICALLY = os.getenv('AURA_DYNAMIC_LENGTH', 'true').strip().lower() == 'true'

# Initialize Gemini client
client = None
if GEMINI_API_KEY and Client:
    try:
        client = Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini AI (google.genai) configured successfully")
    except Exception as e:
        logger.error("Failed to configure Gemini: %s", e)
        client = None
else:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set - using fallback providers")
    if not Client:
        logger.warning("google-genai not installed - install with: pip install google-genai")

# Initialize OpenAI fallback if available
openai_client = None
if OPENAI_API_KEY and OpenAIClient:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
        logger.info("OpenAI configured as fallback provider")
    except Exception as e:
        logger.error("Failed to configure OpenAI: %s", e)
        openai_client = None

# Initialize Groq if available (recommended free alternative)
groq_client = None
if GROQ_API_KEY and GroqClient:
    try:
        groq_client = GroqClient(api_key=GROQ_API_KEY)
        logger.info("Groq configured (free Llama model)")
    except Exception as e:
        logger.error("Failed to configure Groq: %s", e)
        groq_client = None

# Initialize DeepSeek (free tier, OpenAI-compatible, excellent for study tasks)
# Get a free key at: https://platform.deepseek.com → API Keys
deepseek_client = None
if DEEPSEEK_API_KEY and OpenAIClient:
    try:
        deepseek_client = OpenAIClient(
            api_key=DEEPSEEK_API_KEY,
            base_url='https://api.deepseek.com'
        )
        logger.info("DeepSeek configured (free study-optimised model)")
    except Exception as e:
        logger.error("Failed to configure DeepSeek: %s", e)
        deepseek_client = None


# Eager Load Model if configured (prevents first-request latency)
if ENABLE_LOCAL_EMOTION_MODEL and os.getenv('AURA_EAGER_MODEL_LOAD', 'false').lower() == 'true':
    try:
        get_emotion_model()
        logger.info("Emotion model pre-loaded successfully (Eager Load)")
    except Exception as e:
        logger.warning("Failed to eager load emotion model: %s", e)


def _local_fallback(user_message: str, style: str = 'concise') -> str:
    """Provide contextual, varied responses when APIs are unavailable.

    Honors `style` to keep replies brief for short inputs.
    """
    import random
    
    msg_lower = user_message.lower().strip()
    
    # Greetings
    if msg_lower in ['hi', 'hello', 'hey', 'hi there', 'sup', 'yo', 'hi!', 'hello!']:
        if style == 'ultra_brief':
            return random.choice([
                "Hi! How are you feeling today?",
                "Hello! How can I support you right now?",
                "Hey—what’s on your mind?"
            ])
        return random.choice([
            "Hello! I'm AURA, your mental wellness companion. How are you feeling today?",
            "Hey there! Thanks for reaching out. What's on your mind?",
            "Hi! I'm here to listen and support you. How can I help today?"
        ])
    
    # Questions about the bot
    if any(phrase in msg_lower for phrase in ['who are you', 'what are you', 'who r u', 'what r u', 'who are u']):
        return (
            "I'm AURA—your AI-powered mental wellness assistant for students in India.\n\n"
            "I'm here to:\n"
            "• Listen without judgment\n"
            "• Help with stress, anxiety, and academic pressure (like boards, JEE, NEET, or university exams)\n"
            "• Suggest practical coping strategies\n"
            "• Track your mood and wellbeing over time\n\n"
            "Think of me as your 24/7 mental health companion. How can I support you today?"
        )
    
    # How are you
    if any(phrase in msg_lower for phrase in ['how are you', 'how r u', 'how are u', 'hows it going']):
        return (
            "Thanks for asking! I'm here and ready to support you.\n\n"
            "But more importantly—how are *you* doing? What's on your mind today?"
        )
    
    # Stress/anxiety keywords
    if any(w in msg_lower for w in ['stress', 'anxious', 'worried', 'overwhelm', 'panic']):
        return (
            f"I hear you're feeling stressed. That's completely valid, and I'm here with you.\n\n"
            "Try this quick grounding technique:\n"
            "• 5-4-3-2-1: Name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste\n"
            "• Box breathing: Inhale 4 counts, hold 4, exhale 4, hold 4\n"
            "• Write down your top worry—just putting it on paper can help\n\n"
            "What aspect feels most overwhelming right now?"
        )
    
    # Exam/study stress
    if any(w in msg_lower for w in ['exam', 'test', 'study', 'assignment', 'deadline']):
        return (
            "Academic pressure is real, and it's okay to feel stressed about it.\n\n"
            "Here's a quick action plan:\n"
            "• Break study into 25-min focused sessions (Pomodoro)\n"
            "• Prioritize: What's due soonest? Start there\n"
            "• Take real breaks—walk, stretch, hydrate\n"
            "• Remember: One step at a time is still progress\n\n"
            "What subject or task feels most challenging?"
        )
    
    # Math/technical questions
    if any(char in user_message for char in ['=', '+', '-', '*', '/', '^']) or 'calculate' in msg_lower:
        return (
            "I see you're asking about math or calculations!\n\n"
            "While I'm focused on mental wellness support, I notice you might be working on something academic. "
            "If you're feeling stressed about your studies, I'm here to help with that!\n\n"
            "Are you feeling overwhelmed by your workload? Let's talk about managing study stress."
        )
    
    # General knowledge/trivia questions
    if msg_lower.endswith('?') and len(msg_lower) < 100:
        return (
            "That's an interesting question!\n\n"
            "I'm AURA, specialized in mental health and wellness support for students. "
            "For general questions, you might want to try a search engine or academic resource.\n\n"
            "However, if you're curious because of academic stress or need help managing your studies, "
            "I'm absolutely here for that! How are you feeling about your coursework?"
        )
    
    # General fallback
    if style == 'ultra_brief':
        return "I'm here for you. Want to share what's on your mind?"
    if style == 'concise':
        return (
            "I'm here to support your mental wellness. If you're feeling off, we can start small—"
            "take a 30‑second breath, name the feeling, and pick one tiny next step. What would help right now?"
        )
    return (
        "I'm here to support your mental wellness.\n\n"
        "I specialize in:\n"
        "• Managing stress and anxiety\n"
        "• Study/exam pressure\n"
        "• Mood tracking and emotional support\n"
        "• Practical coping strategies\n\n"
        "What's on your mind today? How can I help you feel better?"
    )


def _format_history(chat_history: List[Dict[str, str]]) -> str:
    """Format the last few turns to give the model context."""
    if not chat_history:
        return "No prior conversation."
    formatted = []
    for turn in chat_history[-8:]:
        role = turn.get('role', 'user')
        content = turn.get('content', '')
        formatted.append(f"{role.title()}: {content}")
    return "\n".join(formatted)


def _classify_request(user_message: str, chat_history: Optional[List[Dict[str, str]]], kind: str) -> str:
    """Classify desired response style: 'ultra_brief' | 'concise' | 'structured'.

    Heuristics prioritize brevity for greetings/small talk and short queries.
    """
    try:
        msg = (user_message or '').strip()
        ml = msg.lower()
        words = [w for w in ml.replace('\n', ' ').split(' ') if w]
        word_count = len(words)
        greetings = {"hi", "hello", "hey", "yo", "hiya", "sup", "hi!", "hello!", "hey!"}

        if not RESPOND_DYNAMICALLY:
            # Respect global toggle: fall back to configured STRUCTURED/concise behavior
            return 'structured' if STRUCTURED_RESPONSES else 'concise'

        # Elaborate / detail trigger words → always structured regardless of length
        detail_triggers = {
            'elaborate', 'explain more', 'tell me more', 'expand', 'in detail',
            'more detail', 'detailed', 'comprehensive', 'full', 'complete', 'thorough',
            'deep dive', 'breakdown', 'everything about', 'give more', 'more info',
        }
        if any(t in ml for t in detail_triggers):
            return 'structured'

        # If trivial greeting or very short text, keep it ultra brief
        if ml in greetings or word_count <= 2:
            return 'ultra_brief'

        # If short statement or simple question, do a concise single paragraph
        if word_count <= 15 and not any(ch in msg for ch in ['\n', ';', ':']) and kind == 'mental':
            return 'concise'

        # If there is prior history and user message is short, still concise
        if (chat_history or []) and word_count <= 10:
            return 'concise'

        # Default to structured for richer prompts
        return 'structured'
    except Exception:
        # In case of any issues, default to concise to avoid verbosity
        return 'concise'


def predict_emotion_and_stress(user_message: str) -> tuple:
    """Run the local GoEmotions model and compute probability-weighted stress."""
    emotion_pipeline = get_emotion_model() if 'pipeline' in globals() and pipeline else None
    
    if not emotion_pipeline:
        return "Unknown", 50, {}
        
    try:
        scores = emotion_pipeline(user_message)[0]
        best_emotion = max(scores, key=lambda x: x['score'])
        emo_name = best_emotion['label']
        
        # FIX #33: Configurable emotion→stress mapping.
        # Loaded from AURA_EMOTION_STRESS_MAP env var (JSON) or defaults below.
        _default_stress_map = {
            "admiration": 10, "amusement": 10, "anger": 85, "annoyance": 65,
            "approval": 20, "caring": 20, "confusion": 60, "curiosity": 30,
            "desire": 40, "disappointment": 70, "disapproval": 60, "disgust": 75,
            "embarrassment": 65, "excitement": 15, "fear": 90, "gratitude": 10,
            "grief": 95, "joy": 10, "love": 10, "nervousness": 80,
            "optimism": 15, "pride": 15, "realization": 40, "relief": 20,
            "remorse": 75, "sadness": 85, "surprise": 50, "neutral": 35
        }
        try:
            custom_map = os.getenv('AURA_EMOTION_STRESS_MAP')
            stress_map = json.loads(custom_map) if custom_map else _default_stress_map
        except (json.JSONDecodeError, TypeError):
            stress_map = _default_stress_map
        mood_map = {
            "admiration": "Inspired", "amusement": "Happy", "anger": "Angry",
            "annoyance": "Frustrated", "approval": "Satisfied", "caring": "Compassionate",
            "confusion": "Confused", "curiosity": "Curious", "desire": "Motivated",
            "disappointment": "Disappointed", "disapproval": "Critical", "disgust": "Disgusted",
            "embarrassment": "Embarrassed", "excitement": "Excited", "fear": "Anxious",
            "gratitude": "Grateful", "grief": "Devastated", "joy": "Happy", "love": "Affectionate",
            "nervousness": "Nervous", "optimism": "Hopeful", "pride": "Proud",
            "realization": "Enlightened", "relief": "Relieved", "remorse": "Guilty",
            "sadness": "Sad", "surprise": "Surprised", "neutral": "Neutral"
        }
        
        predicted_mood = mood_map.get(emo_name, "Neutral")
        
        weighted_stress = 0.0
        # Sort scores by probability and take top 8 for the radar chart
        sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
        top_emotions = {s['label']: round(s['score'], 4) for s in sorted_scores[:8]}
        
        for emo in scores:
            weighted_stress += emo['score'] * stress_map.get(emo['label'], 50)
            
        return predicted_mood, min(100, max(0, int(round(weighted_stress)))), top_emotions
    except Exception as e:
        logger.error("Failed to run local emotion model: %s", e)
        return "Unknown", 50, {}


def generate_mental_response(
    user_message: str, 
    chat_history: List[Dict[str, str]] = None, 
    kind: str = 'mental', 
    conversation_id: str = '',
    predicted_mood: str = "Unknown",
    calculated_stress: int = 50,
    risk_level: str = "LOW_RISK",
    memory_context: dict = None
) -> str:
    """Generate a structured, compassionate response using Gemini AI via google.genai SDK.

    Returns JSON containing the therapist response and metadata.
    """
    
    style = _classify_request(user_message, chat_history, kind)

    # Crisis Interceptor: Prevent safety filters from abruptly terminating the connection on high-risk keywords
    # FIX #45: Uses shared crisis keywords from utils.crisis_keywords
    from aura.utils.crisis_keywords import CRISIS_PLAIN_KEYWORDS
    msg_lower = user_message.lower()
    if any(k in msg_lower for k in CRISIS_PLAIN_KEYWORDS) or risk_level == "CRITICAL_RISK":
        return json.dumps({
            "mood": "Depressed",
            "stress_score": 95,
            "risk_level": "CRITICAL_RISK",
            "mental_indicators": ["High Mental Risk: Crisis/Severe Distress"],
            "aura_response": "I hear how incredibly difficult things are right now. Your feelings are real and valid. Please reach out to someone who can help — you don't have to face this alone.\n\n🆘 Free & Confidential Indian Helplines:\n• iCall (TISS): 9152987821 (Mon–Sat, 8am–10pm)\n• Vandrevala Foundation: 9999 666 555 (24/7)\n• AASRA: 9820466626\n• National Emergency: 112\n\nPlease talk to your proctor, a counsellor, or call one of these numbers right now. You matter. 💙"

        })

    if not client:
        logger.warning("Gemini client not available - using basic response")
        return json.dumps({
            "mood": predicted_mood,
            "stress_score": calculated_stress,
            "risk_level": risk_level,
            "mental_indicators": ["System degraded"],
            "aura_response": _generate_with_fallback(user_message, chat_history, style)
        })

    try:
        history_block = _format_history(chat_history or [])
        mem_text = ""
        if memory_context:
            mem_text = f"\nUser's Emotional Memory (Last 20 messages):\n- Average Stress: {memory_context.get('average_stress')}\n- Dominant Feeling: {memory_context.get('dominant_emotion')}\n"
        
        # AURA AI Therapist Architecture System Prompt
        system_prompt = f"""You are AURA, an advanced emotional intelligence AI designed to support students in India by understanding their emotional and mental state during conversation.
You understand Indian cultural, academic (e.g., CBSE, ICSE, JEE, NEET, university exams), and social contexts deeply.

Your primary responsibility is to analyze the user's message and determine their emotional condition using natural language understanding.

For every message, perform the following tasks:
1. Detect possible mental state indicators (e.g. Academic stress, Burnout, Loneliness, Low motivation, Exam anxiety)
2. Respond with empathetic and supportive conversation tailored to their psychological state, using culturally relevant context where appropriate.

Response rules:
- Be supportive and calm. Never sound robotic. Never judge the user.
- LOW_RISK: Provide a normal, friendly conversation.
- MODERATE_RISK: Encourage short breaks and self-care.
- HIGH_RISK: Suggest active relaxation strategies (e.g. breathing, grounding techniques).
- CRITICAL_RISK: Provide a strong supportive message emphasizing that they are not alone. ALWAYS include Indian crisis helplines such as iCall (9152987821), Vandrevala Foundation (9999 666 555), AASRA (9820466626), or National Emergency (112).
- If mood is positive, reinforce motivation and encouragement.

Context from local model inference & memory:
Suggested Mood: {predicted_mood}
Base Stress: {calculated_stress}
Risk Level: {risk_level}{mem_text}

Output must ALWAYS follow this exact JSON structure (only output valid JSON, no markdown blocks, no other text):
{{
  "mood": "{predicted_mood}",
  "stress_score": {calculated_stress},
  "risk_level": "{risk_level}",
  "mental_indicators": ["<detected factor 1>", "<detected factor 2>"],
  "aura_response": "<empathetic and supportive message>"
}}"""

        prompt = f"""{system_prompt}

Conversation ID: {conversation_id or 'local'}
Recent conversation (last turns):
{history_block}

Student: "{user_message}"
"""

        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=32,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        if response and hasattr(response, 'text') and response.text:
            text = response.text.strip()
            logger.info("Generated therapist response (%d chars)", len(text))
            return text
        else:
            logger.warning("Empty response from Gemini")
            return json.dumps({
                "mood": predicted_mood,
                "stress_score": calculated_stress,
                "risk_level": risk_level,
                "mental_indicators": ["System degraded"],
                "aura_response": _generate_with_fallback(user_message, chat_history, style)
            })

    except Exception as e:
        logger.error("Gemini API error: %s", str(e)[:300])
        logger.exception("Full traceback:")
        return json.dumps({
            "mood": predicted_mood,
            "stress_score": calculated_stress,
            "risk_level": risk_level,
            "mental_indicators": ["API Error"],
            "aura_response": _generate_with_fallback(user_message, chat_history, style)
        })


def _generate_with_fallback(user_message: str, chat_history: List[Dict[str, str]] = None, style: str = 'concise', persona: str = 'mental') -> str:
    """Try DeepSeek → Groq → OpenAI → local fallback. DeepSeek is free and excellent for study tasks."""

    # 1. DeepSeek (free tier, best for study/reasoning tasks)
    if deepseek_client:
        try:
            messages = _build_chat_messages(user_message, chat_history, style, persona)
            # Use deepseek-reasoner for study tasks (chain-of-thought), deepseek-chat for mental/general
            model = 'deepseek-reasoner' if persona == 'study' else 'deepseek-chat'
            resp = deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            text = (resp.choices[0].message.content or '').strip()
            if text:
                logger.info("DeepSeek (%s) response (%d chars)", model, len(text))
                return text
        except Exception as de:
            logger.warning("DeepSeek error: %s", str(de)[:150])

    # 2. Groq — free, fast, Llama 3.3 70B
    if groq_client:
        try:
            messages = _build_chat_messages(user_message, chat_history, style, persona)
            resp = groq_client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            text = (resp.choices[0].message.content or '').strip()
            if text:
                logger.info("Groq (Llama) response (%d chars)", len(text))
                return text
        except Exception as ge:
            logger.warning("Groq error: %s", str(ge)[:150])

    # 3. OpenAI fallback
    if openai_client:
        try:
            messages = _build_chat_messages(user_message, chat_history, style, persona)
            resp = openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            text = (resp.choices[0].message.content or '').strip()
            if text:
                logger.info("OpenAI fallback response (%d chars)", len(text))
                return text
        except Exception as oe:
            logger.error("OpenAI error: %s", str(oe)[:300])

    # 4. Final local fallback
    if REQUIRE_AI:
        return "AI is temporarily unavailable. Please try again shortly."
    return _local_fallback(user_message, style)


def _build_chat_messages(user_message: str, chat_history: List[Dict[str, str]] = None, style: str = 'concise', persona: str = 'mental') -> List[Dict[str, str]]:
    """Build messages array for OpenAI/Groq/DeepSeek APIs.

    persona='study'  → academic / study-coach system prompt
    persona='mental' → mental wellness / AURA compassion prompt (default)
    """
    if persona == 'study':
        if style == 'ultra_brief':
            system = (
                "You are the AURA Study Assistant. Answer study questions precisely and briefly — "
                "1–3 sentences max. Provide the direct answer or formula first."
            )
        elif style == 'concise':
            system = (
                "You are the AURA Study Assistant, expert across all academic subjects. "
                "Give clear, accurate answers (80–150 words). Include key formulas or definitions inline. "
                "Use LaTeX for maths ($...$). End with one concise check-in question."
            )
        else:
            system = (
                "You are the AURA Advanced Study Assistant. Maximize student comprehension with: "
                "1) a concept overview scaled to required depth, 2) step-by-step breakdown where needed, "
                "3) key formulas/facts in LaTeX ($...$ for inline, $$...$$ for display), "
                "4) a practice suggestion or example problem. "
                "Scale length to the complexity of the request — brief for simple questions, "
                "comprehensive for detailed topics, timelines, notes, mind maps, or elaboration requests. "
                "Never truncate mid-sentence. Be encouraging, precise, and well-organized."
            )
    else:
        # Mental wellness persona
        if style == 'ultra_brief':
            system = (
                "You are AURA, a compassionate assistant for students in India. "
                "Reply in 1–2 short sentences, empathetic, with an optional single gentle question. No lists or headings."
            )
        elif style == 'concise':
            system = (
                "You are AURA, a compassionate mental wellness assistant for students in India. "
                "Reply as one concise paragraph (60–120 words) with 1–2 practical tips inline and a short follow-up question. "
                "Understand Indian academic and cultural contexts."
            )
        else:
            system = (
                "You are AURA, a compassionate mental health assistant for students in India. "
                "Respond with: 1) validation (2–3 sentences), 2) 2–3 practical, specific suggestions with brief explanations, "
                "3) a gentle follow-up question, 4) encouragement. Be warm, supportive, and practical. "
                "Understand Indian academic stress and cultural contexts. "
                "If indicating crisis, always provide Indian helplines: iCall (9152987821), Vandrevala Foundation (9999 666 555), AASRA. "
                "Expand depth when the user is sharing complex emotions or asking for more. Never cut off mid-thought."
            )

    messages = [{'role': 'system', 'content': system}]
    for turn in (chat_history or [])[-8:]:
        role = 'user' if turn.get('role') == 'user' else 'assistant'
        content = turn.get('content', '')
        messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': user_message})
    return messages


def extract_sentiment(text: str) -> str:
    """Simple sentiment extraction to help track mood."""
    neg_words = {'stressed', 'anxious', 'overwhelmed', 'depressed', 'sad', 'tired', 'panic', 'worry', 'scared'}
    pos_words = {'happy', 'good', 'better', 'grateful', 'confident', 'optimistic', 'calm', 'proud'}
    anx_words = {'anxious', 'nervous', 'worried', 'panic', 'fear', 'scary', 'dread'}
    
    text_lower = text.lower()
    
    if any(word in text_lower for word in anx_words):
        return 'anxious'
    elif any(word in text_lower for word in neg_words):
        return 'negative'
    elif any(word in text_lower for word in pos_words):
        return 'positive'
    else:
        return 'neutral'


def generate_study_response(user_message: str, chat_history: List[Dict[str, str]] = None, conversation_id: str = '') -> str:
    """Generate a study-assistant response for text-only queries.

    Provider chain: Gemini → DeepSeek → Groq → OpenAI → local fallback.
    Use this for all study chat messages that do not involve file uploads.
    """
    style = _classify_request(user_message, chat_history, 'study')

    # 1. Gemini — multimodal but works for text too; use a study-tuned prompt
    if client:
        try:
            history_block = _format_history(chat_history or [])
            study_system = (
                "You are the AURA Advanced Study Assistant — expert across all academic subjects. "
                "Your goal is to maximize student understanding and productivity."
            )
            if style == 'ultra_brief':
                prompt_text = (
                    f"{study_system}\n\n"
                    f"Conversation: {history_block}\n\n"
                    f'Student: "{user_message}"\n\n'
                    "Answer in 1–3 precise sentences. Give the direct answer first."
                )
            elif style == 'concise':
                prompt_text = (
                    f"{study_system}\n\n"
                    f"Conversation ID: {conversation_id or 'local'}\n"
                    f"Recent context:\n{history_block}\n\n"
                    f'Student: "{user_message}"\n\n'
                    "Reply in 1 concise paragraph (80–150 words). Include key formulas or steps inline. "
                    "Use LaTeX for maths ($...$). End with one short check-in question."
                )
            else:
                prompt_text = (
                    f"{study_system}\n\n"
                    f"Conversation ID: {conversation_id or 'local'}\n"
                    f"Recent context:\n{history_block}\n\n"
                    f'Student: "{user_message}"\n\n'
                    "Respond in clear Markdown:\n"
                    "1. **Overview** — concept explanation with necessary depth\n"
                    "2. **Breakdown** — numbered steps or bullet points (expand fully for complex topics)\n"
                    "3. **Key Points** — formulas/definitions in LaTeX ($...$ inline, $$...$$ display)\n"
                    "4. **Practice** — example problem or study tip\n"
                    "Scale response length to the complexity of the request — concise for simple questions, "
                    "comprehensive and thorough for detailed topics, timelines, notes, mind maps, or elaboration requests. "
                    "Never cut off mid-sentence or mid-section. Be precise, encouraging, and well-organized."
                )

            response = client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    top_p=0.9,
                    max_output_tokens=4096,
                )
            )
            if response and hasattr(response, 'text') and response.text:
                text = response.text.strip()
                logger.info("Gemini study response (%d chars)", len(text))
                return text
        except Exception as e:
            logger.warning("Gemini study error: %s", str(e)[:150])

    # 2–4. DeepSeek → Groq → OpenAI → local
    return _generate_with_fallback(user_message, chat_history, style, persona='study')


def analyze_study_material(prompt: str, file_path: str, mime_type: str = '', history: List[Dict[str, str]] = None, conversation_id: str = '') -> str:
    """Analyze study materials with Gemini (images, PDFs, or text) and return structured Markdown.

    Uses AURA Advanced Study Assistant system prompt for professional-grade analysis.
    """
    if not client:
        # For text-only queries, fall through to DeepSeek/Groq/OpenAI chain
        p = Path(file_path) if file_path else None
        has_file = p and p.exists() and p.stat().st_size > 0
        if has_file:
            return (
                "File analysis requires Gemini AI (multimodal). "
                "Please set GEMINI_API_KEY, or paste the text content directly in the chat."
            )
        # Text-only — use full provider chain
        return generate_study_response(
            prompt or "Help me with my studies.",
            history,
            conversation_id
        )

    try:
        p = Path(file_path)
        mime = mime_type or _guess_mime(p.suffix)

        history_block = _format_history(history or [])
        user_prompt = prompt or "Please analyze this material and explain it clearly."

        # AURA Advanced Study Assistant System Prompt
        system_prompt = """You are the AURA Advanced Study Assistant. Your goal is to maximize student productivity through deep analysis and interactive learning.

**PDF/Image Analysis:** When a file is provided, extract key concepts, definitions, and formulas. Provide a structured summary with bullet points organized by topic.

**Quiz Generation:** On request, generate 5 multiple-choice questions based on the current context or uploaded file to test comprehension. Format each with clear options (A, B, C, D) and indicate the correct answer.

**Step-by-Step Solutions:** For complex diagrams or problems, break the solution into logical, numbered steps. Use clear formatting with subsections where appropriate.

**Tone:** Be encouraging, professional, and concise. Use LaTeX notation for mathematical formulas: wrap inline formulas in $ $ and display formulas in $$ $$.

**Response Format:**
- Start with a brief overview/summary
- Break down key concepts with clear headings
- Use numbered lists for steps and multiple-choice questions
- Bold important terms on first mention
- End with actionable next steps or practice suggestions"""

        if STRUCTURED_RESPONSES:
            instruction = (
                f"{system_prompt}\n\n"
                f"Conversation ID: {conversation_id or 'local'}\n"
                f"Recent conversation context:\n{history_block}\n\n"
                f"Student request: {user_prompt}\n\n"
                "Respond with clear, well-organized Markdown that maximizes learning value."
            )
        else:
            instruction = (
                f"{system_prompt}\n\n"
                f"Conversation ID: {conversation_id or 'local'}\n"
                f"Recent context:\n{history_block}\n\n"
                f"Request: {user_prompt}\n\n"
                "Provide a concise, well-structured response in Markdown."
            )

        if mime.startswith('image/'):
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            contents = [
                types.Part(text=instruction),
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
            ]
        elif mime == 'application/pdf' or p.suffix.lower() == '.pdf':
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            contents = [
                types.Part(text=instruction),
                types.Part.from_bytes(data=pdf_bytes, mime_type=mime),
            ]
        else:
            contents = [types.Part(text=instruction)]

        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.5,
                top_p=0.9,
                max_output_tokens=8192,
            )
        )

        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        return "Could not analyze the material. Please try again."

    except Exception as e:
        logger.error("Study analysis error: %s", str(e)[:200])
        # If no file was involved, fall back to text-only provider chain
        p_check = Path(file_path) if file_path else None
        if not p_check or not p_check.exists():
            return generate_study_response(
                prompt or "Help me with my studies.",
                history,
                conversation_id
            )
        return f"Error analyzing material: {str(e)[:100]}"


def _guess_mime(ext: str) -> str:
    """Guess MIME type from file extension."""
    ext = (ext or '').lower()
    return {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
    }.get(ext, 'application/octet-stream')
