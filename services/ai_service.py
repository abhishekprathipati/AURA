import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use google.genai (new recommended SDK). Fallback to Groq/OpenAI if Gemini quota exhausted.
try:
    from google.genai import Client, types
except ImportError:
    Client = None
    types = None

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

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
STRUCTURED_RESPONSES = os.getenv('AURA_STRUCTURED_RESPONSES', 'true').strip().lower() == 'true'
REQUIRE_AI = os.getenv('AURA_REQUIRE_AI', 'false').strip().lower() == 'true'
RESPOND_DYNAMically = os.getenv('AURA_DYNAMIC_LENGTH', 'true').strip().lower() == 'true'

# Initialize Gemini client
client = None
if GEMINI_API_KEY and Client:
    try:
        client = Client(api_key=GEMINI_API_KEY)
        logger.info("✓ Gemini AI (google.genai) configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")
        client = None
else:
    if not GEMINI_API_KEY:
        logger.warning("⚠ GEMINI_API_KEY not set - using fallback providers")
    if not Client:
        logger.warning("⚠ google-genai not installed - install with: pip install google-genai")

# Initialize OpenAI fallback if available
openai_client = None
if OPENAI_API_KEY and OpenAIClient:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
        logger.info("✓ OpenAI configured as fallback provider")
    except Exception as e:
        logger.error(f"Failed to configure OpenAI: {e}")
        openai_client = None

# Initialize Groq if available (recommended free alternative)
groq_client = None
if GROQ_API_KEY and GroqClient:
    try:
        groq_client = GroqClient(api_key=GROQ_API_KEY)
        logger.info("✓ Groq configured (free Llama model)")
    except Exception as e:
        logger.error(f"Failed to configure Groq: {e}")
        groq_client = None


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
            "I'm AURA—your AI-powered mental wellness assistant for students.\n\n"
            "I'm here to:\n"
            "• Listen without judgment\n"
            "• Help with stress, anxiety, and academic pressure\n"
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

        if not RESPOND_DYNAMically:
            # Respect global toggle: fall back to configured STRUCTURED/concise behavior
            return 'structured' if STRUCTURED_RESPONSES else 'concise'

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


def generate_mental_response(user_message: str, chat_history: List[Dict[str, str]] = None, kind: str = 'mental', conversation_id: str = '') -> str:
    """Generate a structured, compassionate response using Gemini AI via google.genai SDK.

    Returns Markdown with sections: Thought, Main Response, Quick Actions, Next Step.
    """
    
    style = _classify_request(user_message, chat_history, kind)

    if not client:
        logger.warning("Gemini client not available - trying fallback providers")
        return _generate_with_fallback(user_message, chat_history, style)

    try:
        history_block = _format_history(chat_history or [])
        persona = 'Mental wellness coach for students' if kind == 'mental' else 'Study coach for students'
        if style == 'ultra_brief':
            prompt = f"""
    You are AURA — a warm, empathetic {persona}. Keep it extremely brief.

    Conversation ID: {conversation_id or 'local'}
    Recent conversation (last turns):
    {history_block}

    Student: "{user_message}"

    Respond in 1–2 short sentences, empathetic and human. End with ONE gentle question if appropriate. No headings.
    """
        elif style == 'concise' or not STRUCTURED_RESPONSES:
            prompt = f"""
    You are AURA — an empathetic, expert {persona}. Keep continuity to prior messages and reply clearly.

    Conversation ID: {conversation_id or 'local'}
    Recent conversation:
    {history_block}

    Student: "{user_message}"

    Reply in a single concise paragraph (60–120 words), include 1–2 practical tips inline.
    End with one short follow-up question. Use plain Markdown, avoid headings.
    """
        else:
            prompt = f"""
    You are AURA — an empathetic, expert {persona}. Maintain continuity by linking to prior messages.

    Conversation ID: {conversation_id or 'local'}
    Conversation so far (last turns):
    {history_block}

    Student now says: "{user_message}"

    Respond ONLY in Markdown using this exact structure:

    ### Thought
    - Briefly acknowledge their situation and reference prior context.
    - One short paragraph (2–3 sentences), no sensitive or private data.

    ### Main Response
    - 2–3 concise, practical suggestions with brief explanations.
    - Use bullet points. Bold the key action at the start of each bullet.

    ### Quick Actions
    - Provide 2–4 short action items as a bulleted list (imperative tone).

    ### Next Step
    - End with ONE clear question or a suggested action to move forward.

    Style: warm, supportive, professional. 150–200 words total. Use simple language.
    """

        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=32,
                max_output_tokens=1024,
            )
        )
        
        if response and hasattr(response, 'text') and response.text:
            text = response.text.strip()
            logger.info(f"✓ Generated response ({len(text)} chars)")
            return text
        else:
            logger.warning("Empty response from Gemini")
            return _generate_with_fallback(user_message, chat_history, style)
            
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)[:300]}")
        logger.exception("Full traceback:")
        return _generate_with_fallback(user_message, chat_history, style)


def _generate_with_fallback(user_message: str, chat_history: List[Dict[str, str]] = None, style: str = 'concise') -> str:
    """Try Groq first (free), then OpenAI, then local fallback."""
    
    # Try Groq first (free and fast)
    if groq_client:
        try:
            messages = _build_chat_messages(user_message, chat_history, style)
            resp = groq_client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            text = (resp.choices[0].message.content or '').strip()
            if text:
                logger.info(f"✓ Groq (Llama) response ({len(text)} chars)")
                return text
        except Exception as ge:
            logger.warning(f"Groq error: {str(ge)[:150]}")
    
    # Fallback to OpenAI
    if openai_client:
        try:
            messages = _build_chat_messages(user_message, chat_history, style)
            resp = openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            text = (resp.choices[0].message.content or '').strip()
            if text:
                logger.info(f"✓ OpenAI fallback response ({len(text)} chars)")
                return text
        except Exception as oe:
            logger.error(f"OpenAI error: {str(oe)[:300]}")
    
    # Final fallback
    if REQUIRE_AI:
        return "AI is temporarily unavailable. Please try again shortly."
    return _local_fallback(user_message, style)


def _build_chat_messages(user_message: str, chat_history: List[Dict[str, str]] = None, style: str = 'concise') -> List[Dict[str, str]]:
    """Build messages array for OpenAI/Groq APIs."""
    if style == 'ultra_brief':
        system = (
            "You are AURA, a compassionate assistant for students. "
            "Reply in 1–2 short sentences, empathetic, with an optional single gentle question. No lists or headings."
        )
    elif style == 'concise':
        system = (
            "You are AURA, a compassionate assistant for students. "
            "Reply as one concise paragraph (60–120 words) with 1–2 practical tips inline and a short follow-up question."
        )
    else:
        system = (
            "You are AURA, a compassionate mental health assistant for students. "
            "Respond with: 1) validation (2–3 sentences), 2) 2–3 practical, specific suggestions with brief explanations, "
            "3) a gentle follow-up question, 4) encouragement. Be warm, supportive, and practical. Aim for ~180 words."
        )

    messages = [{ 'role': 'system', 'content': system }]
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


def analyze_study_material(prompt: str, file_path: str, mime_type: str = '', history: List[Dict[str, str]] = None, conversation_id: str = '') -> str:
    """Analyze study materials with Gemini (images, PDFs, or text) and return structured Markdown.

    Uses AURA Advanced Study Assistant system prompt for professional-grade analysis.
    """
    if not client:
        return "AI study assistant not configured. Please set GEMINI_API_KEY or GROQ_API_KEY."

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
            contents = [
                types.Part(text=instruction),
                types.Part.from_bytes(data=open(file_path, 'rb').read(), mime_type=mime),
            ]
        else:
            contents = [types.Part(text=instruction)]

        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=contents
        )

        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        return "Could not analyze the material. Please try again."

    except Exception as e:
        logger.error(f"Study analysis error: {str(e)[:200]}")
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
