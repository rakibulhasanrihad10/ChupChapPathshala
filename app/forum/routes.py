from flask import render_template, flash, redirect, url_for, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.forum import bp
from app.models import ForumPost, ForumComment, User

@bp.route('/')
def index():
    q = request.args.get('q', '').strip()
    username = request.args.get('username', '').strip()
    
    query = ForumPost.query.order_by(ForumPost.created_at.desc())
    
    searched_user = None
    display_search_term = ""
    
    if username:
        # Priority 1: Specific username provided (usually from clicking a user in search results)
        searched_user = User.query.filter_by(username=username).first()
        if searched_user:
            query = query.filter_by(user_id=searched_user.id)
            display_search_term = username
        else:
            # Fallback for manual username search
            query = query.filter_by(user_id=-1)
            display_search_term = username
    elif q:
        # Priority 2: General search term
        display_search_term = q
        # Try finding a user precisely first (case-insensitive)
        precise_user = User.query.filter(User.username.ilike(q)).first()
        
        if precise_user:
            query = query.filter_by(user_id=precise_user.id)
            searched_user = precise_user
        else:
            # Otherwise search content
            query = query.filter(
                (ForumPost.title.ilike(f'%{q}%')) | 
                (ForumPost.content.ilike(f'%{q}%'))
            )
            
    posts = query.all()
    return render_template('forum/index.html', 
                           posts=posts, 
                           search_username=display_search_term, 
                           searched_user=searched_user)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_type = request.form.get('post_type', 'trade')
        
        # Check for duplicates
        existing_post = ForumPost.query.filter_by(title=title, content=content, user_id=current_user.id).first()
        if existing_post:
            flash('You have already posted this content.', 'warning')
            return redirect(url_for('forum.view_post', post_id=existing_post.id))
        
        post = ForumPost(title=title, content=content, user=current_user, post_type=post_type)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('forum.index'))
    return render_template('forum/create_post.html', title='Create Post')

@bp.route('/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('You need to login to comment.', 'warning')
            return redirect(url_for('auth.login'))
        
        content = request.form.get('content')
        if content:
            comment = ForumComment(content=content, user=current_user, post=post)
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been posted!', 'success')
        return redirect(url_for('forum.view_post', post_id=post.id))
        
    return render_template('forum/view_post.html', post=post)

@bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    if post.user != current_user:
        flash('You cannot edit this post.', 'danger')
        return redirect(url_for('forum.view_post', post_id=post.id))
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.post_type = request.form.get('post_type', 'trade')
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('forum.view_post', post_id=post.id))
        
    return render_template('forum/create_post.html', post=post, title='Edit Post')

@bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    if post.user != current_user:
        flash('You cannot delete this post.', 'danger')
        return redirect(url_for('forum.view_post', post_id=post.id))
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('forum.index'))

@bp.route('/search/forum')
def search_forum():
    """API endpoint to search for users and post titles"""
    query_text = request.args.get('q', '').strip()
    
    if not query_text or len(query_text) < 2:
        return jsonify({'users': [], 'posts': []})
    
    # Search users by username
    users = User.query.filter(
        User.username.ilike(f'%{query_text}%')
    ).limit(5).all()
    
    # Search posts by title
    posts = ForumPost.query.filter(
        ForumPost.title.ilike(f'%{query_text}%')
    ).limit(5).all()
    
    user_results = [{
        'id': user.id,
        'username': user.username,
        'profile_photo': user.profile_photo or 'https://placehold.co/150x150?text=User',
        'profile_url': url_for('main.user_profile', username=user.username),
        'post_count': len(user.forum_posts)
    } for user in users]
    
    post_results = [{
        'id': post.id,
        'title': post.title,
        'url': url_for('forum.view_post', post_id=post.id),
        'author': post.user.username,
        'created_at': post.created_at.strftime('%Y-%m-%d')
    } for post in posts]
    
    return jsonify({
        'users': user_results,
        'posts': post_results
    })
