import logging
import json
import mimetypes
import os
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from flask import send_from_directory
from werkzeug.utils import secure_filename
from utils.database import get_db
from models.chat import ChatModel
from services.ai_service import generate_mental_response, generate_study_response, extract_sentiment, analyze_study_material, predict_emotion_and_stress
from services.stress_service import calculate_dynamic_stress
from services.risk_service import predict_risk_level
from services.memory_service import update_emotion_memory, get_emotion_memory
from utils.auth_helpers import demo_restricted, demo_chat_limited
from utils.helpers import safe_error

chat_bp = Blueprint('chat', __name__)
log = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def _save_and_track_file(file):
    """Persist an uploaded study file and record it in the user's session."""
    filename = (file.filename or '').strip()
    if not filename:
        raise ValueError('No file selected')

    lower_name = filename.lower()
    if not any(lower_name.endswith('.' + ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError('File type not allowed')

    upload_dir = os.path.join('static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{int(time.time())}_{secure_filename(filename)}"
    save_path = os.path.join(upload_dir, unique_filename)
    file.save(save_path)

    mime = file.mimetype or mimetypes.guess_type(save_path)[0] or 'application/octet-stream'
    files = session.get('study_files', {}) or {}
    files[unique_filename] = {
        'path': save_path,
        'mime': mime,
        'original_filename': filename,
    }
    session['study_files'] = files
    session['study_last_file'] = unique_filename
    session.modified = True

    return {
        'file_id': unique_filename,
        'path': save_path,
        'mime': mime,
        'original_filename': filename,
    }


def _resolve_file_from_session(file_id: str = None):
    files = session.get('study_files') or {}
    active_id = file_id or session.get('study_last_file')
    if not active_id:
        return None

    meta = files.get(active_id)
    if not meta:
        return None

    path = meta.get('path')
    if not path or not os.path.exists(path):
        return None

    mime = meta.get('mime') or mimetypes.guess_type(path)[0] or 'application/octet-stream'
    return {
        'file_id': active_id,
        'path': path,
        'mime': mime,
        'original_filename': meta.get('original_filename', active_id),
    }


def _get_db():
    """Return DB if available; fall back to None so API keeps working without Mongo."""
    try:
        db = get_db()
        return db
    except Exception as exc:
        log.warning("DB unavailable, running without persistence: %s", exc)
        return None


@chat_bp.route('/api/chat/mental', methods=['POST'])
@demo_chat_limited
def api_chat_mental():
    """Process user message and return AI-generated response."""
    try:
        log.info("=== Chat request received ===")
        from utils.schemas import ChatMessageRequest, ValidationError
        try:
            req = ChatMessageRequest.model_validate(request.get_json(force=True) or {})
        except ValidationError as exc:
            return jsonify({'error': exc.errors()[0]['msg']}), 400

        user_message = req.message
        # Optional metadata from client
        data = request.get_json(force=True) or {}
        conversation_id = (data).get('conversation_id', '').strip()
        kind = (data).get('kind', 'mental').strip() or 'mental'
        client_history = (data).get('context') or (data).get('conversation_history') or []
        user_email = session.get('user_email')
        
        log.info(f"Message received | User: {(user_email or '')[:3]}***")
        
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
            log.info("âœ“ Database connected")
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
            log.info(f"âœ“ Loaded {len(history)} history items")
        else:
            log.warning("âœ— Database not available - running without persistence")

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
                    log.info(f"âœ“ Using client-provided history ({len(history)})")
            except Exception as _:
                pass

        # Phase 3 Orchestration
        log.info("→ Running ML analysis...")
        predicted_mood, calculated_stress = predict_emotion_and_stress(user_message)
        risk_level = predict_risk_level(calculated_stress, user_message)
        memory_context = get_emotion_memory(user_email)
        
        # Log stress event
        if db is not None:
            db['stress_logs'].insert_one({
                'user_email': user_email,
                'timestamp': datetime.utcnow(),
                'mood': predicted_mood,
                'stress_score': calculated_stress,
                'risk_level': risk_level
            })

        # Generate AI response (which is now a JSON string)
        log.info("→ Calling generate_mental_response...")
        raw_ai_response = generate_mental_response(
            user_message, history, kind=kind, conversation_id=conversation_id,
            predicted_mood=predicted_mood, calculated_stress=calculated_stress,
            risk_level=risk_level, memory_context=memory_context
        )
        
        # Parse the structured response
        try:
            parsed_resp = json.loads(raw_ai_response)
            ai_response_text = parsed_resp.get("aura_response", raw_ai_response)
            mental_indicators = parsed_resp.get("mental_indicators", ["None"])
            if isinstance(mental_indicators, list):
                mental_indicators = ", ".join(mental_indicators)
        except Exception as json_err:
            log.warning(f"Could not parse AI response as JSON: {json_err}. Using as raw text.")
            ai_response_text = raw_ai_response
            mental_indicators = "None"

        log.info(f"✓ Got response ({len(ai_response_text)} chars). Mood: {predicted_mood}, Stress: {calculated_stress}")

        # Save to database
        chat_doc = {
            'user_email': user_email,
            'message': user_message,
            'response': ai_response_text,
            'type': kind or 'mental',
            'sentiment': predicted_mood, # Using advanced mood prediction instead of basic sentiment
            'stress_score': calculated_stress, # New field
            'mental_indicators': mental_indicators, # New field
            'risk_level': risk_level, # New field
            'created_at': datetime.utcnow(),
            'conversation_id': conversation_id or None,
        }
        if chats_coll is not None:
            chats_coll.insert_one(chat_doc)
            log.info("✓ Saved to database")
            
            # Update memory asynchronously or after save
            update_emotion_memory(user_email)
        else:
            log.info("⊘ Not saving to DB (unavailable)")

        # Trigger stress recalculation for mental chats (non-blocking)
        stress_update = None
        if (kind or 'mental') == 'mental' and user_email:
            try:
                result = calculate_dynamic_stress(user_email)
                stress_update = {
                    'score': result['score'],
                    'label': result['label'],
                    'trend': result['trend'],
                }
            except Exception as se:
                log.warning(f"Stress recalc after chat failed: {se}")

        log.info("=== Chat request complete ===")
        resp = {
            'user_message': user_message,
            'ai_response': ai_response_text,
            'sentiment': predicted_mood,
            'stress_score': calculated_stress,
            'mental_indicators': mental_indicators,
            'risk_level': risk_level,
            'timestamp': chat_doc['created_at'].isoformat(),
        }
        if stress_update:
            resp['stress'] = stress_update
        return jsonify(resp)
    
    except Exception as e:
        log.error(f"✗ Chat error: {safe_error(e, 'chat')}")
        log.exception("Full traceback:")
        return jsonify({
            'error': 'AI service error. Please try again.',
        }), 500


@chat_bp.route('/api/chat', methods=['POST'])
@demo_chat_limited
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
        
        # Fetch mental chats (paginated — max 200)
        cursor = chats_coll.find({
            'user_email': user_email,
            'type': 'mental',
        }).sort('created_at', -1).limit(200)
        
        history = [
            {
                'message': msg.get('message', ''),
                'response': msg.get('response', ''),
                'timestamp': msg.get('created_at').isoformat() if msg.get('created_at') else None,
                'sentiment': msg.get('sentiment', 'neutral'),
            }
            for msg in cursor
        ]
        history.reverse()  # oldest first
        
        return jsonify({'history': history})
    
    except Exception as e:
        log.error(f"Chat history error: {e}")
        return jsonify({'error': 'Could not load history'}), 500

@chat_bp.route('/api/stress-trend', methods=['GET'])
def api_stress_trend():
    """Returns the last 7 days of stress data for chart rendering."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401
            
        db = get_db()
        if db is None:
            return jsonify({'dates': [], 'stress_scores': []})
            
        # Group by day and average
        import collections
        
        cutoff = datetime.utcnow() - timedelta(days=7)
        logs = db['stress_logs'].find({
            'user_email': user_email,
            'timestamp': {'$gte': cutoff}
        }).sort('timestamp', 1)
        
        daily_stress = collections.defaultdict(list)
        for log_entry in logs:
            day_str = log_entry['timestamp'].strftime('%Y-%m-%d')
            daily_stress[day_str].append(log_entry.get('stress_score', 50))
            
        dates = []
        scores = []
        for d in sorted(daily_stress.keys()):
            dates.append(d)
            avg = int(sum(daily_stress[d]) / len(daily_stress[d]))
            scores.append(avg)
            
        return jsonify({'dates': dates, 'stress_scores': scores})
        
    except Exception as e:
        log.error(f"Stress trend error: {e}")
        return jsonify({'dates': [], 'stress_scores': []})


@chat_bp.route('/api/chat/clear', methods=['POST'])
@demo_restricted
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
        return jsonify({"error": f"Clear error: {safe_error(e, 'chat')}"}), 500


@chat_bp.route('/upload_study_file', methods=['POST'])
@demo_restricted
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

        meta = _save_and_track_file(file)
        log.info(f"âœ“ File uploaded: {meta['file_id']} by {user_email}")

        return jsonify({
            'ok': True,
            'file_id': meta['file_id'],
            'filename': meta['file_id'],
            'original_filename': meta['original_filename'],
            'size': os.path.getsize(meta['path'])
        }), 200

    except Exception as e:
        log.error(f"Upload error: {str(e)}")
        return jsonify({"error": f"Upload failed: {safe_error(e, 'chat')}"}), 500


@chat_bp.route('/study/upload', methods=['POST'])
@demo_restricted
def study_upload():
    """Preferred upload route for Study Assistant UI."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        meta = _save_and_track_file(request.files['file'])
        log.info(f"âœ“ Study upload via /study/upload: {meta['file_id']} by {user_email}")
        return jsonify({
            'ok': True,
            'file_id': meta['file_id'],
            'filename': meta['file_id'],
            'original_filename': meta['original_filename'],
        })
    except Exception as e:
        log.error(f"Study upload error: {str(e)}")
        return jsonify({'error': safe_error(e, 'chat')}), 500


@chat_bp.route('/study/summarize', methods=['POST'])
@demo_chat_limited
def study_summarize():
    """Summarize the most recent uploaded study file."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        req_data = request.get_json(silent=True) or {}
        meta = _resolve_file_from_session(req_data.get('file_id'))
        if not meta:
            return jsonify({'error': 'Upload a file first'}), 400

        prompt = (
            "Summarize the uploaded document for a student. "
            "Highlight key sections, definitions, formulas (use $...$), and 3-5 actionable next steps."
        )
        summary = analyze_study_material(prompt, meta['path'], meta['mime'])
        return jsonify({'summary': summary, 'file_id': meta['file_id'], 'file_name': meta['original_filename']})
    except Exception as e:
        log.error(f"Study summarize error: {str(e)}")
        return jsonify({'error': safe_error(e, 'chat')}), 500


@chat_bp.route('/study/quiz', methods=['POST'])
@demo_chat_limited
def study_quiz():
    """Generate a quiz from the most recent uploaded study file."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        req_data = request.get_json(silent=True) or {}
        meta = _resolve_file_from_session(req_data.get('file_id'))
        if not meta:
            return jsonify({'error': 'Upload a file first'}), 400

        prompt = (
            "Generate 5 multiple-choice questions based on this document. "
            "Return Markdown with numbered questions, options A-D, and indicate the correct answer after each question."
        )
        quiz = analyze_study_material(prompt, meta['path'], meta['mime'])
        return jsonify({'quiz': quiz, 'file_id': meta['file_id'], 'file_name': meta['original_filename']})
    except Exception as e:
        log.error(f"Study quiz error: {str(e)}")
        return jsonify({'error': safe_error(e, 'chat')}), 500


@chat_bp.route('/api/study/analyze', methods=['POST'])
@demo_chat_limited
def api_study_analyze():
    """Analyze study query with optional file upload."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401

        prompt = request.form.get('prompt', '').strip()
        conversation_history = request.form.get('conversation_history', '[]')
        conversation_id = request.form.get('conversation_id', '').strip()
        file_id = request.form.get('file_id', '').strip()
        file_meta = None
        # Try to parse client-provided history
        history = []
        try:
            raw = json.loads(conversation_history or '[]')
            if isinstance(raw, list):
                for turn in raw[-10:]:
                    role = (turn.get('role') or '').strip().lower()
                    content = (turn.get('content') or turn.get('text') or '').strip()
                    if role in ('user', 'assistant') and content:
                        history.append({'role': role, 'content': content})
        except Exception:
            history = []
        
        # Check if user provided either a prompt or a file
        has_file = 'file' in request.files and request.files['file'].filename
        
        if not prompt and not has_file:
            return jsonify({'error': 'Please provide a prompt or upload a file'}), 400

        # Resolve uploaded file either from direct upload or stored session file
        if has_file:
            file_meta = _save_and_track_file(request.files['file'])
        elif file_id:
            file_meta = _resolve_file_from_session(file_id)
            if file_meta is None:
                return jsonify({'error': 'Uploaded file not found. Please upload again.'}), 400

        # If file but no prompt, create a generic prompt to summarize
        if file_meta and not prompt:
            prompt = "Please analyze and summarize this document, highlighting key concepts and important points."

        answer = None
        if file_meta:
            answer = analyze_study_material(prompt, file_meta['path'], file_meta['mime'], history=history, conversation_id=conversation_id)
        else:
            # Text-only study query — use dedicated study provider chain
            answer = generate_study_response(prompt, history, conversation_id=conversation_id)

        return jsonify({'answer': answer, 'file_id': file_meta['file_id'] if file_meta else None})

    except Exception as e:
        log.error(f"Study analyze error: {e}")
        return jsonify({'error': 'Study analysis failed. Please try again.'}), 500


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
            db['feedback'].insert_one({
                'user_email': user_email,
                'action': action,
                'text': text[:500],
                'timestamp': datetime.utcnow()
            })

        return jsonify({'ok': True})
    except Exception as e:
        # Do not break UX; return 200 with error info for observability
        return jsonify({'ok': False, 'error': safe_error(e, 'chat')}), 200
