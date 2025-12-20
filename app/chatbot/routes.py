from flask import request, jsonify
from flask_login import current_user
from app.chatbot import bp
from app.chatbot.chatbot_service import chatbot_service
from app.models import ChatMessage
from app.extensions import db
import uuid

@bp.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages from users"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Get user info
        user_id = current_user.id if current_user.is_authenticated else None
        is_staff = current_user.is_staff() if current_user.is_authenticated else False
        
        # Get conversation history for this session
        history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        conversation_history = [
            {'message': msg.message, 'response': msg.response}
            for msg in history[-5:]  # Last 5 messages for context
        ]
        
        # Process message with chatbot service
        result = chatbot_service.process_message(
            user_message=user_message,
            user_id=user_id,
            is_staff=is_staff,
            conversation_history=conversation_history if conversation_history else None
        )
        
        # Save to database
        chat_message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            message=user_message,
            response=result['response'],
            intent=result.get('intent'),
            function_data=result.get('metadata')
        )
        db.session.add(chat_message)
        db.session.commit()
        
        return jsonify({
            'response': result['response'],
            'session_id': session_id,
            'intent': result.get('intent'),
            'timestamp': chat_message.timestamp.isoformat()
        })
        
    except Exception as e:
        import traceback
        print("Chatbot Error:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Get conversation history for a session"""
    try:
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        
        return jsonify({
            'session_id': session_id,
            'count': len(messages),
            'messages': [
                {
                    'message': msg.message,
                    'response': msg.response,
                    'intent': msg.intent,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat/session/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """Clear conversation history for a session"""
    try:
        ChatMessage.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        
        return jsonify({'message': 'Session cleared successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
