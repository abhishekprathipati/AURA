import logging
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from utils.database import get_db
from models.chat import ChatModel
from services.ai_service import generate_mental_response, extract_sentiment, analyze_study_material
from flask import send_from_directory
import os

chat_bp = Blueprint('chat', __name__)
log = logging.getLogger(__name__)


def _get_db():
    """Return DB if available; fall back to None so API keeps working without Mongo."""
    try:
        db = get_db()
        return db
    except Exception as exc:
        log.warning("DB unavailable, running without persistence: %s", exc)
        return None


@chat_bp.route('/api/chat/mental', methods=['POST'])
def api_chat_mental():
    """Process user message and return AI-generated response."""
    try:
        log.info("=== Chat request received ===")
        data = request.get_json(force=True)
        user_message = (data or {}).get('message', '').strip()
        # Optional metadata from client
        conversation_id = (data or {}).get('conversation_id', '').strip()
        kind = (data or {}).get('kind', 'mental').strip() or 'mental'
        client_history = (data or {}).get('context') or (data or {}).get('conversation_history') or []
        user_email = session.get('user_email')
        
        log.info(f"Message: {user_message[:50]}... | User: {user_email}")
        
        if not user_message:
            log.warning("Empty message")
            return jsonify({'error': 'Message cannot be empty'}), 400
        if not user_email:
            log.warning("Not logged in")
            return jsonify({'error': 'Not logged in'}), 401
        
        db = _get_db()
        history = []
        chats_coll = None
        if db is not None:
            log.info("✓ Database connected")
            chats_coll = db[ChatModel.collection_name]
            # Fetch recent chat history for context
            recent = list(chats_coll.find({
                'user_email': user_email,
                'type': 'mental',
            }).sort('created_at', -1).limit(20))
            recent.reverse()  # Chronological order
            db_history = [
                {'role': 'user' if msg.get('is_user') else 'assistant', 'content': msg.get('message' if msg.get('is_user') else 'response', '')}
                for msg in recent
            ]
            history = db_history
            log.info(f"✓ Loaded {len(history)} history items")
        else:
            log.warning("✗ Database not available - running without persistence")

        # Prefer client-provided conversation history if available (memory injection)
        if isinstance(client_history, list) and len(client_history) > 0:
            try:
                # Normalize to expected schema
                normalized = []
                for turn in client_history[-10:]:
                    role = (turn.get('role') or '').strip().lower()
                    content = (turn.get('content') or turn.get('text') or '').strip()
                    if role in ('user', 'assistant') and content:
                        normalized.append({'role': role, 'content': content})
                if normalized:
                    history = normalized
                    log.info(f"✓ Using client-provided history ({len(history)})")
            except Exception as _:
                pass

        # Generate AI response
        log.info("→ Calling generate_mental_response...")
        ai_response = generate_mental_response(user_message, history, kind=kind, conversation_id=conversation_id)
        log.info(f"✓ Got response ({len(ai_response)} chars)")

        # Save to database
        chat_doc = {
            'user_email': user_email,
            'message': user_message,
            'response': ai_response,
            'type': kind or 'mental',
            'sentiment': extract_sentiment(user_message),
            'created_at': datetime.utcnow(),
            'conversation_id': conversation_id or None,
        }
        if chats_coll is not None:
            chats_coll.insert_one(chat_doc)
            log.info("✓ Saved to database")
        else:
            log.info("⊘ Not saving to DB (unavailable)")

        log.info("=== Chat request complete ===")
        return jsonify({
            'user_message': user_message,
            'ai_response': ai_response,
            'sentiment': extract_sentiment(user_message),
            'timestamp': chat_doc['created_at'].isoformat(),
        })
    
    except Exception as e:
        log.error(f"❌ Chat error: {str(e)[:300]}")
        log.exception("Full traceback:")
        return jsonify({
            'error': 'AI service error. Please try again.',
            'debug': str(e)[:200]
        }), 500


@chat_bp.route('/api/chat', methods=['POST'])
def api_chat_unified():
    """Unified chat endpoint for single-bot applications. Proxies to mental handler with kind support."""
    # Reuse the mental endpoint logic (it already accepts kind/context/conversation_id)
    return api_chat_mental()


@chat_bp.route('/api/chat/history', methods=['GET'])
def api_chat_history():
    """Get chat history for current user."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401
        
        db = _get_db()
        chats_coll = db[ChatModel.collection_name]
        
        # Fetch mental chats
        cursor = chats_coll.find({
            'user_email': user_email,
            'type': 'mental',
        }).sort('created_at', 1)
        
        history = [
            {
                'message': msg.get('message', ''),
                'response': msg.get('response', ''),
                'timestamp': msg.get('created_at').isoformat() if msg.get('created_at') else None,
                'sentiment': msg.get('sentiment', 'neutral'),
            }
            for msg in cursor
        ]
        
        return jsonify({'history': history})
    
    except Exception as e:
        return jsonify({'error': f'History error: {str(e)[:100]}'}), 500


@chat_bp.route('/api/chat/clear', methods=['POST'])
def api_chat_clear():
    """Clear chat history for current user."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401
        
        db = _get_db()
        chats_coll = db[ChatModel.collection_name]
        
        result = chats_coll.delete_many({
            'user_email': user_email,
            'type': 'mental',
        })
        
        return jsonify({'deleted': result.deleted_count})
    
    except Exception as e:
        return jsonify({'error': f'Clear error: {str(e)[:100]}'}), 500


@chat_bp.route('/upload_study_file', methods=['POST'])
def upload_study_file():
    """Handle file upload for study assistant with validation."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        allowed_extensions = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
        filename = file.filename.lower()
        if not any(filename.endswith('.' + ext) for ext in allowed_extensions):
            return jsonify({'error': 'File type not allowed'}), 400

        # Save to static/uploads
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Use unique filename to avoid conflicts
        import time
        unique_filename = f"{int(time.time())}_{file.filename}"
        save_path = os.path.join(upload_dir, unique_filename)
        
        file.save(save_path)
        log.info(f"✓ File uploaded: {unique_filename} by {user_email}")
        
        return jsonify({
            'ok': True,
            'filename': unique_filename,
            'original_filename': file.filename,
            'size': os.path.getsize(save_path)
        }), 200

    except Exception as e:
        log.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)[:180]}'}), 500


@chat_bp.route('/api/study/analyze', methods=['POST'])
def api_study_analyze():
    """Analyze study query with optional file upload."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        prompt = request.form.get('prompt', '').strip()
        conversation_history = request.form.get('conversation_history', '[]')
        conversation_id = request.form.get('conversation_id', '').strip()
        # Try to parse client-provided history
        history = []
        try:
            import json
            raw = json.loads(conversation_history or '[]')
            if isinstance(raw, list):
                for turn in raw[-10:]:
                    role = (turn.get('role') or '').strip().lower()
                    content = (turn.get('content') or turn.get('text') or '').strip()
                    if role in ('user', 'assistant') and content:
                        history.append({'role': role, 'content': content})
        except Exception:
            history = []
        
        debug_info = {
            'files_present': list(request.files.keys()),
            'form_prompt': prompt,
        }

        # Check if user provided either a prompt or a file
        has_file = 'file' in request.files and request.files['file'].filename
        
        if not prompt and not has_file:
            return jsonify({'error': 'Please provide a prompt or upload a file', 'debug': debug_info}), 400
        
        # If file but no prompt, create a generic prompt to summarize
        if has_file and not prompt:
            prompt = "Please analyze and summarize this document, highlighting key concepts and important points."

        answer = None
        if has_file:
            f = request.files['file']
            # Save to static/uploads for short-term processing
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, f.filename)
            f.save(save_path)
            mime = f.mimetype or ''
            answer = analyze_study_material(prompt, save_path, mime, history=history, conversation_id=conversation_id)
        else:
            # Text-only query using Gemini
            answer = generate_mental_response(prompt, history, kind='study', conversation_id=conversation_id)

        return jsonify({'answer': answer, 'debug': debug_info})

    except Exception as e:
        return jsonify({'error': f'Study analyze error: {str(e)[:180]}'}), 500


@chat_bp.route('/api/chat/feedback', methods=['POST'])
def api_chat_feedback():
    """Capture thumbs/copy feedback; lightweight log for telemetry."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        data = request.get_json(force=True) or {}
        action = data.get('action', '').strip()
        text = (data.get('text') or '').strip()
        if not action:
            return jsonify({'error': 'Missing action'}), 400

        # Minimal log into database if available, otherwise noop
        db = get_db()
        if db is not None:
            db.execute(
                "INSERT INTO feedback (user_email, action, text) VALUES (?, ?, ?)",
                (user_email, action, text[:500])
            )
            db.commit()

        return jsonify({'ok': True})
    except Exception as e:
        # Do not break UX; return 200 with error info for observability
        return jsonify({'ok': False, 'error': str(e)[:180]}), 200
