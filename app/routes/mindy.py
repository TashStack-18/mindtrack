from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.mindy import MindyConversation, MindyMessage
from app.services.mindy_service import generate_reply, build_context, TEMPLATES
from app.services.encryption_service import encrypt_text, decrypt_text
from datetime import datetime
import random
import logging
import hashlib

bp = Blueprint('mindy', __name__)

@bp.route('/mindy/init', methods=['POST'])
def init_conversation():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401

    # In the current implementation, we always create a new conversation
    # when opening Mindy explicitly if they don't have an active one.
    # The prompt: "When a completed conversation is ended, the next time the user opens Mindy it MUST create a completely new conversation... Do NOT automatically reopen the previous conversation."
    # If they closed the UI but didn't click End, it remains active. So we find the active one or create one.
    
    active_conv = MindyConversation.query.filter_by(user_id=g.user.id, status='active').order_by(MindyConversation.created_at.desc()).first()
    
    if not active_conv:
        active_conv = MindyConversation(user_id=g.user.id, title="New Conversation", status='active')
        db.session.add(active_conv)
        db.session.commit()
        
        # Determine welcome message
        greeting_templates = TEMPLATES['greeting']
        idx = random.randint(0, len(greeting_templates) - 1)
        greeting = greeting_templates[idx]
        
        # Save greeting as a message from mindy
        welcome_msg = MindyMessage(
            conversation_id=active_conv.id,
            sender='mindy',
            encrypted_message=encrypt_text(greeting)
        )
        db.session.add(welcome_msg)
        db.session.commit()
        
        return jsonify({
            "conversation_id": active_conv.id,
            "is_new": True,
            "messages": [{"sender": "mindy", "message": greeting}],
            "state": {"turn": 0, "last_intents": [], "last_templates": [], "context_used_turn": -99}
        }), 200
        
    else:
        # Load existing active messages
        messages = MindyMessage.query.filter_by(conversation_id=active_conv.id).order_by(MindyMessage.created_at.asc()).all()
        msg_list = []
        for msg in messages:
            try:
                decrypted = decrypt_text(msg.encrypted_message)
                msg_list.append({"sender": msg.sender, "message": decrypted})
            except:
                pass
                
        return jsonify({
            "conversation_id": active_conv.id,
            "is_new": False,
            "messages": msg_list,
            "state": {"turn": len(msg_list), "last_intents": [], "last_templates": [], "context_used_turn": -99}
        }), 200

@bp.route('/mindy/message', methods=['POST'])
def message():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
    
    data = request.get_json()
    if not data or 'message' not in data or 'conversation_id' not in data:
        return jsonify({"error": "Message and conversation_id required"}), 400
        
    conv_id = data['conversation_id']
    user_message = data['message'].strip()
    state = data.get('state')
    
    # Verify ownership
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
        
    if conv.status == 'completed':
        return jsonify({"error": "Conversation is completed"}), 400
        
    if not user_message or len(user_message) > 1000:
        return jsonify({"error": "Invalid message length"}), 400
    
    try:
        # Save user message
        user_msg_db = MindyMessage(
            conversation_id=conv.id,
            sender='user',
            encrypted_message=encrypt_text(user_message)
        )
        db.session.add(user_msg_db)
        
        # Generate reply
        context = build_context(g.user.id)
        reply, new_state = generate_reply(user_message, context, state)
        
        # Save Mindy reply
        mindy_msg_db = MindyMessage(
            conversation_id=conv.id,
            sender='mindy',
            encrypted_message=encrypt_text(reply)
        )
        db.session.add(mindy_msg_db)
        
        conv.updated_at = datetime.utcnow()
        db.session.commit()
        
        response = jsonify({
            "reply": reply,
            "state": new_state
        })
        response.headers['Cache-Control'] = 'no-store'
        return response
        
    except Exception as e:
        logging.error(f"Mindy route error: {type(e)}")
        db.session.rollback()
        response = jsonify({
            "reply": "Yeah, I'm here. Tell me a little more.",
            "state": {"turn": 1, "last_intents": [], "last_templates": [], "context_used_turn": -99}
        })
        response.headers['Cache-Control'] = 'no-store'
        return response, 200

@bp.route('/mindy/end_request', methods=['POST'])
def end_request():
    if not g.user:
        return jsonify({"error": "auth_required"}), 401
    
    data = request.get_json()
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
    
    data = request.get_json()
    conv_id = data.get('conversation_id')
    
    conv = MindyConversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not conv or conv.status == 'completed':
        return jsonify({"error": "Invalid conversation"}), 400
        
    conv.status = 'completed'
    conv.completed_at = datetime.utcnow()
    conv.title = generate_title(conv.id)
    
    db.session.commit()
    
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
        
    data = request.get_json()
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
