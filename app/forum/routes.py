from flask import render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from app import db
from app.forum import bp
from app.models import ForumPost, ForumComment, User

@bp.route('/')
def index():
    posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    return render_template('forum/index.html', posts=posts)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_type = request.form.get('post_type', 'trade')
        
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
