from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.extensions import socketio, db
from app.models import Message, User
from datetime import datetime

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle user connection to Socket.IO"""
    if current_user.is_authenticated:
        # Join user's personal room for receiving messages
        room = f'user_{current_user.id}'
        join_room(room)
        
        # Store socket ID for tracking active connections
        current_user.socket_id = request.sid
        db.session.commit()
        
        # Notify user's contacts that they're online
        emit('user_status', {
            'user_id': current_user.id,
            'status': 'online',
            'username': current_user.username
        }, broadcast=True)
        
        print(f"User {current_user.username} connected with socket {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection from Socket.IO"""
    if current_user.is_authenticated:
        # Leave user's personal room
        room = f'user_{current_user.id}'
        leave_room(room)
        
        # Clear socket ID
        current_user.socket_id = None
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Notify user's contacts that they're offline
        emit('user_status', {
            'user_id': current_user.id,
            'status': 'offline',
            'username': current_user.username,
            'last_seen': current_user.last_seen.isoformat()
        }, broadcast=True)
        
        print(f"User {current_user.username} disconnected")

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message in real-time"""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    
    recipient_id = data.get('recipient_id')
    message_body = data.get('message')
    
    if not recipient_id or not message_body:
        return {'error': 'Missing recipient_id or message'}, 400
    
    # Create and save message to database
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        body=message_body,
        timestamp=datetime.utcnow()
    )
    db.session.add(message)
    db.session.commit()
    
    # Prepare message data
    message_data = {
        'id': message.id,
        'sender_id': current_user.id,
        'sender_username': current_user.username,
        'sender_photo': current_user.profile_photo,
        'recipient_id': recipient_id,
        'body': message.body,
        'timestamp': message.timestamp.isoformat(),
        'is_read': False
    }
    
    # Emit to recipient's room
    recipient_room = f'user_{recipient_id}'
    emit('receive_message', message_data, room=recipient_room)
    
    # Also emit back to sender for confirmation
    emit('message_sent', message_data)
    
    return {'success': True, 'message_id': message.id}

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    if not current_user.is_authenticated:
        return
    
    recipient_id = data.get('recipient_id')
    is_typing = data.get('is_typing', False)
    
    if recipient_id:
        recipient_room = f'user_{recipient_id}'
        emit('typing_indicator', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_typing': is_typing
        }, room=recipient_room)

@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read in real-time"""
    if not current_user.is_authenticated:
        return
    
    message_ids = data.get('message_ids', [])
    
    if message_ids:
        # Update messages in database
        Message.query.filter(
            Message.id.in_(message_ids),
            Message.recipient_id == current_user.id
        ).update({'is_read': True}, synchronize_session=False)
        db.session.commit()
        
        # Notify sender that messages were read
        for msg_id in message_ids:
            message = Message.query.get(msg_id)
            if message:
                sender_room = f'user_{message.sender_id}'
                emit('message_read', {
                    'message_id': msg_id,
                    'read_by': current_user.id
                }, room=sender_room)

@socketio.on('user_online')
def handle_user_online():
    """Update user's last_seen timestamp"""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@socketio.on('edit_message')
def handle_edit_message(data):
    """Handle message editing in real-time"""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    
    message_id = data.get('message_id')
    new_body = data.get('new_body')
    
    if not message_id or not new_body:
        return {'error': 'Missing message_id or new_body'}, 400
    
    # Find and update message
    message = Message.query.get(message_id)
    if not message or message.sender_id != current_user.id:
        return {'error': 'Message not found or unauthorized'}, 404
    
    message.body = new_body
    message.edited_at = datetime.utcnow()
    db.session.commit()
    
    # Notify recipient
    recipient_room = f'user_{message.recipient_id}'
    emit('message_edited', {
        'message_id': message.id,
        'new_body': message.body,
        'edited_at': message.edited_at.isoformat()
    }, room=recipient_room)
    
    return {'success': True}

@socketio.on('delete_message')
def handle_delete_message(data):
    """Handle message deletion in real-time"""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    
    message_id = data.get('message_id')
    
    if not message_id:
        return {'error': 'Missing message_id'}, 400
    
    # Find and mark message as deleted
    message = Message.query.get(message_id)
    if not message or message.sender_id != current_user.id:
        return {'error': 'Message not found or unauthorized'}, 404
    
    message.is_deleted = True
    message.deleted_at = datetime.utcnow()
    db.session.commit()
    
    # Notify recipient
    recipient_room = f'user_{message.recipient_id}'
    emit('message_deleted', {
        'message_id': message.id,
        'deleted_at': message.deleted_at.isoformat()
    }, room=recipient_room)
    
    return {'success': True}
