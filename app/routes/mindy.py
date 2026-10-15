from flask import Blueprint, request, jsonify, g, session
from app.extensions import db
from app.models.mindy import MindyConversation, MindyMessage
from app.services.mindy_service import (generate_reply, build_context, suggestions_for, recover_state,
                                        sanitize_state, TEMPLATES)
from app.services.mindy_content import STARTER_SUGGESTIONS
from app.services.encryption_service import encrypt_text, decrypt_text
from datetime import datetime
import json
import random
import logging

bp = Blueprint('mindy', __name__)

MAX_MESSAGE_CHARS = 1000
STATE_SESSION_KEY = 'mindy_state'


# --- Conversation state ------------------------------------------------------
# Mindy's working memory (current game, topic, "just listen" preference...) is
# kept server-side in the user's session, encrypted with the app's Fernet key,
# so the browser can neither read nor tamper with it. If it's missing (new
# login, cleared cookies) it's rebuilt from the stored, encrypted messages.

def _decrypted_messages(conv_id):
    out = []
    for msg in MindyMessage.query.filter_by(conversation_id=conv_id).order_by(MindyMessage.created_at.asc(), MindyMessage.id.asc()).all():
        try:
            out.append((msg.sender, decrypt_text(msg.encrypted_message)))
        except Exception:
            continue
    return out


def _load_state(conv_id):
    blob = session.get(STATE_SESSION_KEY)
    if blob:
        try:
            saved = json.loads(decrypt_text(blob))
            if saved.get('cid') == conv_id:
                return sanitize_state(saved.get('state'))
        except Exception:
            pass
    history = _decrypted_messages(conv_id)
    return recover_state([m for s, m in history if s == 'user'], [m for s, m in history if s == 'mindy'])


def _save_state(conv_id, state):
    session[STATE_SESSION_KEY] = encrypt_text(json.dumps({'cid': conv_id, 'state': state}, separators=(',', ':')))


def _public_state(state):
    """The only state the browser sees: enough to render quick replies."""
    activity = (state or {}).get('activity') or {}
    return {'activity': activity.get('type')}


def _start_conversation():
    conv = MindyConversation(user_id=g.user.id, title="New Conversation", status='active')
    db.session.add(conv)
    db.session.commit()
    greeting = random.choice(TEMPLATES['greeting'])
    db.session.add(MindyMessage(conversation_id=conv.id, sender='mindy', encrypted_message=encrypt_text(greeting)))
    db.session.commit()
    session.pop(STATE_SESSION_KEY, None)
    return conv, greeting


@bp.route('/mindy/init', methods=['POST'])
def init_conversation():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401

    # Resume the user's active conversation, or start a fresh one.
    active_conv = MindyConversation.query.filter_by(user_id=g.user.id, status='active').order_by(MindyConversation.created_at.desc()).first()

    if not active_conv:
        active_conv, greeting = _start_conversation()
        return jsonify({
            "conversation_id": active_conv.id,
            "is_new": True,
            "messages": [{"sender": "mindy", "message": greeting}],
            "state": {"activity": None},
            "suggestions": STARTER_SUGGESTIONS,
        }), 200

    history = _decrypted_messages(active_conv.id)
    state = _load_state(active_conv.id)
    has_user_messages = any(sender == 'user' for sender, _ in history)
    return jsonify({
        "conversation_id": active_conv.id,
        "is_new": False,
        "messages": [{"sender": s, "message": m} for s, m in history],
        "state": _public_state(state),
        "suggestions": suggestions_for(state) if has_user_messages else STARTER_SUGGESTIONS,
    }), 200


@bp.route('/mindy/new', methods=['POST'])
def new_conversation():
    """Close the current conversation (saving it to history if the user said
    anything) and start a fresh one with a clean context."""
    if not g.user:
        return jsonify({"error": "auth_required"}), 401

    for conv in MindyConversation.query.filter_by(user_id=g.user.id, status='active').all():
        if MindyMessage.query.filter_by(conversation_id=conv.id, sender='user').count() == 0:
            db.session.delete(conv)  # only Mindy's greeting: nothing worth keeping
        else:
            conv.status = 'completed'
            conv.completed_at = datetime.utcnow()
            conv.title = generate_title(conv.id)
    db.session.commit()

    conv, greeting = _start_conversation()
    return jsonify({
        "conversation_id": conv.id,
        "is_new": True,
        "messages": [{"sender": "mindy", "message": greeting}],
        "state": {"activity": None},
        "suggestions": STARTER_SUGGESTIONS,
    }), 200


@bp.route('/mindy/message', methods=['POST'])
def message():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('message'), str) or 'conversation_id' not in data:
        return jsonify({"error": "Message and conversation_id required"}), 400

    try:
        conv_id = int(data['conversation_id'])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid conversation"}), 400
    user_message = data['message'].strip()

    # Ownership is checked against the logged-in user, never a client-supplied id.
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    if conv.status == 'completed':
        return jsonify({"error": "Conversation is completed"}), 400

    if not user_message or len(user_message) > MAX_MESSAGE_CHARS:
        return jsonify({"error": "Invalid message length"}), 400

    try:
        state = _load_state(conv.id)
        context = build_context(g.user.id)
        reply, new_state = generate_reply(user_message, context, state)

        db.session.add(MindyMessage(conversation_id=conv.id, sender='user', encrypted_message=encrypt_text(user_message)))
        db.session.add(MindyMessage(conversation_id=conv.id, sender='mindy', encrypted_message=encrypt_text(reply)))
        conv.updated_at = datetime.utcnow()
        db.session.commit()
        _save_state(conv.id, new_state)

        response = jsonify({
            "reply": reply,
            "state": _public_state(new_state),
            "suggestions": suggestions_for(new_state),
        })
        response.headers['Cache-Control'] = 'no-store'
        return response

    except Exception as e:
        # Log the error type only, never the message contents.
        logging.error(f"Mindy route error: {type(e).__name__}")
        db.session.rollback()
        response = jsonify({"error": "reply_failed"})
        response.headers['Cache-Control'] = 'no-store'
        return response, 500

@bp.route('/mindy/end_request', methods=['POST'])
def end_request():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
    
    data = request.get_json(silent=True) or {}
    conv_id = data.get('conversation_id')
    
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv or conv.status == 'completed':
        return jsonify({"error": "Invalid conversation"}), 400
        
    # Get random end message
    end_templates = TEMPLATES['end_conversation']
    idx = random.randint(0, len(end_templates) - 1)
    reply = end_templates[idx]
    
    # Do NOT save this message to DB yet, or save it?
    # "When clicked, Mindy should first respond with a warm closing message."
    # Yes, we save it as a mindy message so it shows in the history.
    
    mindy_msg_db = MindyMessage(
        conversation_id=conv.id,
        sender='mindy',
        encrypted_message=encrypt_text(reply)
    )
    db.session.add(mindy_msg_db)
    db.session.commit()
    
    return jsonify({"reply": reply}), 200

def generate_title(conversation_id):
    # Deterministic simple title generator based on messages
    messages = MindyMessage.query.filter_by(conversation_id=conversation_id, sender='user').order_by(MindyMessage.created_at.asc()).all()
    if not messages:
        return "Just Needed to Talk"
        
    text_content = ""
    for msg in messages:
        try:
            text_content += decrypt_text(msg.encrypted_message).lower() + " "
        except:
            pass
            
    from app.services.theme_service import THEME_CATEGORIES
    
    if "exam" in text_content or "study" in text_content or "grades" in text_content:
        return "Exam Stress"
    if "sleep" in text_content or "tired" in text_content or "exhausted" in text_content:
        return "Late Night Thoughts"
    if "friend" in text_content or "fight" in text_content or "ignored" in text_content:
        return "Friendship Things"
    if "work" in text_content or "boss" in text_content or "shift" in text_content:
        return "Work Stuff"
    if "family" in text_content or "dad" in text_content or "mom" in text_content or "parents" in text_content:
        return "Family Things"
    if "good" in text_content or "excited" in text_content or "great" in text_content or "happy" in text_content:
        return "Good News"
    if "sad" in text_content or "upset" in text_content or "rough" in text_content:
        return "Rough Day"
        
    return "Something on My Mind"

@bp.route('/mindy/end_confirm', methods=['POST'])
def end_confirm():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
    
    data = request.get_json(silent=True) or {}
    conv_id = data.get('conversation_id')
    
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv or conv.status == 'completed':
        return jsonify({"error": "Invalid conversation"}), 400
        
    conv.status = 'completed'
    conv.completed_at = datetime.utcnow()
    conv.title = generate_title(conv.id)

    db.session.commit()
    session.pop(STATE_SESSION_KEY, None)
    
    return jsonify({"success": True}), 200

@bp.route('/mindy/history', methods=['GET'])
def history():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
        
    convs = MindyConversation.query.filter_by(user_id=g.user.id, status='completed').order_by(MindyConversation.completed_at.desc()).all()
    
    history_list = []
    for c in convs:
        # Get count
        msg_count = MindyMessage.query.filter_by(conversation_id=c.id).count()
        # Preview
        last_msg = MindyMessage.query.filter_by(conversation_id=c.id, sender='user').order_by(MindyMessage.created_at.desc()).first()
        preview = "No messages"
        if last_msg:
            try:
                dec = decrypt_text(last_msg.encrypted_message)
                preview = dec[:40] + ("..." if len(dec) > 40 else "")
            except:
                pass
                
        history_list.append({
            "id": c.id,
            "title": c.title,
            "date": c.completed_at.strftime("%b %d, %Y") if c.completed_at else "",
            "time": c.completed_at.strftime("%I:%M %p") if c.completed_at else "",
            "preview": preview,
            "message_count": msg_count
        })
        
    return jsonify({"history": history_list}), 200

@bp.route('/mindy/conversation/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
        
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
        
    messages = MindyMessage.query.filter_by(conversation_id=conv.id).order_by(MindyMessage.created_at.asc()).all()
    msg_list = []
    for msg in messages:
        try:
            decrypted = decrypt_text(msg.encrypted_message)
            msg_list.append({
                "sender": msg.sender, 
                "message": decrypted,
                "time": msg.created_at.strftime("%I:%M %p")
            })
        except:
            pass
            
    return jsonify({
        "id": conv.id,
        "title": conv.title,
        "date": conv.completed_at.strftime("%b %d, %Y") if conv.completed_at else conv.created_at.strftime("%b %d, %Y"),
        "messages": msg_list,
        "status": conv.status
    }), 200

@bp.route('/mindy/conversation/<int:conv_id>/title', methods=['PUT'])
def rename_conversation(conv_id):
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
        
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
        
    data = request.get_json(silent=True) or {}
    new_title = data.get('title', '').strip()
    if not new_title or len(new_title) > 100:
        return jsonify({"error": "Invalid title"}), 400
        
    conv.title = new_title
    db.session.commit()
    return jsonify({"success": True, "title": new_title}), 200

@bp.route('/mindy/conversation/<int:conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
        
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv:
        return jsonify({"error": "Not found"}), 404
        
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"success": True}), 200
