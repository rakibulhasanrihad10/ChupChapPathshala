import os
import time
from werkzeug.utils import secure_filename
from flask import request, jsonify, current_app, url_for
from app import db
from app.main import bp
from app.models import Book
from app.decorators import staff_required
from flask_login import login_required

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_cover/<int:book_id>', methods=['POST'])
@login_required
@staff_required
def upload_cover(book_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        book = Book.query.get_or_404(book_id)
        
        # Secure filename and add timestamp to prevent caching/collisions
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        new_filename = f"book_{book_id}_{int(time.time())}.{extension}"
        
        # Ensure directory exists
        if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
            os.makedirs(current_app.config['UPLOAD_FOLDER'])
            
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename))
        image_path = url_for('static', filename=f'uploads/covers/{new_filename}')
        book.image_url = image_path
        db.session.commit()
        
        return jsonify({'success': True, 'image_url': image_path})
        
    return jsonify({'error': 'File type not allowed'}), 400
