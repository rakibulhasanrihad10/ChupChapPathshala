from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.messages import bp
from app.models import User, Message
from datetime import datetime
from sqlalchemy import or_, and_, func
from app.extensions import socketio
from flask_socketio import emit

@bp.route('/send/<int:recipient_id>', methods=['POST'])
@login_required
def send_message(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    data = request.get_json()
    body = data.get('body')
    
    if not body:
        return jsonify({'error': 'Message body is required'}), 400
        
    msg = Message(sender_id=current_user.id, recipient_id=recipient.id, body=body)
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': {
            'id': msg.id,
            'body': msg.body,
            'timestamp': msg.timestamp.isoformat(),
            'sender_id': msg.sender_id,
            'recipient_id': msg.recipient_id
        }
    })

@bp.route('/history/<int:user_id>')
@login_required
def get_history(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Get all messages between current_user and other_user
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    
    # Mark received messages as read
    unread_messages = Message.query.filter_by(sender_id=user_id, recipient_id=current_user.id, is_read=False).all()
    for msg in unread_messages:
        msg.is_read = True
    db.session.commit()
    
    result = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        
        # Show placeholder for deleted messages
        message_body = "This message was deleted" if msg.is_deleted else msg.body
        
        result.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_photo': sender.profile_photo if sender else 'https://placehold.co/150x150',
            'sender_name': sender.username if sender else 'User',
            'body': message_body,
            'timestamp': msg.timestamp.strftime('%H:%M' if msg.timestamp.date() == datetime.today().date() else '%b %d'),
            'is_mine': msg.sender_id == current_user.id,
            'is_deleted': msg.is_deleted,
            'edited_at': msg.edited_at.isoformat() if msg.edited_at else None
        })
    
    # Include other user's online status
    response = {
        'messages': result,
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'is_online': other_user.is_online(),
            'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None
        }
    }
        
    return jsonify(response)

@bp.route('/conversations')
@login_required
def get_conversations():
    pass
    recent_messages = Message.query.filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).order_by(Message.timestamp.desc()).limit(100).all()
    
    conversations = {}
    for msg in recent_messages:
        other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
        if other_id not in conversations:
            other_user = User.query.get(other_id)
            conversations[other_id] = {
                'user': {
                    'id': other_user.id,
                    'username': other_user.username,
                    'profile_photo': other_user.profile_photo
                },
                'last_message': {
                    'body': msg.body,
                    'timestamp': msg.timestamp,
                    'is_read': msg.is_read or msg.sender_id == current_user.id
                }
            }
            
    # Convert to list and sort
    conv_list = list(conversations.values())
    conv_list.sort(key=lambda x: x['last_message']['timestamp'], reverse=True)
    
    # Format timestamp for JSON
    for c in conv_list:
        c['last_message']['timestamp'] = c['last_message']['timestamp'].strftime('%b %d, %H:%M')
        
    return jsonify(conv_list)

@bp.route('/unread-count')
@login_required
def get_unread_count():
    """Get the count of unread messages for the current user"""
    count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@bp.route('/unread-list')
@login_required
def get_unread_list():
    """Get a list of recent conversations with unread message indicators"""
    # Get all messages involving the current user (sent or received)
    recent_messages = Message.query.filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).order_by(Message.timestamp.desc()).limit(100).all()
    
    # Group by conversation partner to get latest message from each
    conversations = {}
    for msg in recent_messages:
        other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
        
        if other_id not in conversations:
            other_user = User.query.get(other_id)
            
            # Count unread messages from this person
            unread_count = Message.query.filter_by(
                sender_id=other_id,
                recipient_id=current_user.id,
                is_read=False
            ).count()
            
            conversations[other_id] = {
                'sender_id': other_id,
                'sender_name': other_user.username if other_user else 'Unknown',
                'sender_photo': other_user.profile_photo if other_user else 'https://placehold.co/150x150',
                'message_preview': msg.body[:50] + ('...' if len(msg.body) > 50 else ''),
                'timestamp': msg.timestamp.strftime('%H:%M' if msg.timestamp.date() == datetime.today().date() else '%b %d'),
                'unread_count': unread_count,
                'is_online': other_user.is_online() if other_user else False,
                'last_message_time': msg.timestamp
            }
    
    # Convert to list and sort by most recent
    result = list(conversations.values())
    result.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    # Remove the timestamp object (not JSON serializable)
    for conv in result:
        del conv['last_message_time']
    
    # Get total unread count
    total_unread = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    
    return jsonify({'messages': result[:10], 'total_count': total_unread})

@bp.route('/edit/<int:message_id>', methods=['PUT'])
@login_required
def edit_message(message_id):
    """Edit a message (only by sender)"""
    msg = Message.query.get_or_404(message_id)
    
    # Check if current user is the sender
    if msg.sender_id != current_user.id:
        return jsonify({'error': 'You can only edit your own messages'}), 403
    
    # Check if message is deleted
    if msg.is_deleted:
        return jsonify({'error': 'Cannot edit a deleted message'}), 400
    
    data = request.get_json()
    new_body = data.get('body')
    
    if not new_body or not new_body.strip():
        return jsonify({'error': 'Message body cannot be empty'}), 400
    
    # Update message
    msg.body = new_body.strip()
    msg.edited_at = datetime.utcnow()
    db.session.commit()
    
    # Emit Socket.IO event to recipient
    recipient_room = f'user_{msg.recipient_id}'
    socketio.emit('message_edited', {
        'message_id': msg.id,
        'new_body': msg.body,
        'edited_at': msg.edited_at.isoformat()
    }, room=recipient_room)
    
    return jsonify({
        'status': 'success',
        'message': {
            'id': msg.id,
            'body': msg.body,
            'edited_at': msg.edited_at.isoformat()
        }
    })

@bp.route('/delete/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Soft delete a message (only by sender)"""
    msg = Message.query.get_or_404(message_id)
    
    # Check if current user is the sender
    if msg.sender_id != current_user.id:
        return jsonify({'error': 'You can only delete your own messages'}), 403
    
    # Check if already deleted
    if msg.is_deleted:
        return jsonify({'error': 'Message already deleted'}), 400
    
    # Soft delete
    msg.is_deleted = True
    msg.deleted_at = datetime.utcnow()
    db.session.commit()
    
    # Emit Socket.IO event to recipient
    recipient_room = f'user_{msg.recipient_id}'
    socketio.emit('message_deleted', {
        'message_id': msg.id,
        'deleted_at': msg.deleted_at.isoformat()
    }, room=recipient_room)
    
    return jsonify({
        'status': 'success',
        'message': {
            'id': msg.id,
            'is_deleted': True,
            'deleted_at': msg.deleted_at.isoformat()
        }
    })

