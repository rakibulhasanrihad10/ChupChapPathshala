from flask import render_template, request, jsonify
from app.main import bp
from app.main.search_utils import search_suggestions, full_text_search, ext_search
from app.main.admin_search_utils import admin_search_suggestions, admin_full_search
from flask_login import current_user, login_required

@bp.route('/api/suggestions')
def suggestions():
    query = request.args.get('q', '')
    results = search_suggestions(query)
    return jsonify(results)

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    results = full_text_search(query)
    return render_template('search_results.html', query=query, results=results)

@bp.route('/search/ext')
def search_ext():
    query = request.args.get('q', '')
    ext_results = ext_search(query)
    
        
    results = full_text_search(query)
    return render_template('search_results.html', query=query, results=results, ext_results =  ext_results[0], ext_error=ext_results[1])


# Admin Search Routes
@bp.route('/api/admin/suggestions')
@login_required
def admin_suggestions():
    """Admin-only autocomplete suggestions across all data types"""
    if not current_user.is_staff():
        return jsonify([]), 403
    
    query = request.args.get('q', '')
    results = admin_search_suggestions(query)
    return jsonify(results)

@bp.route('/admin/search')
@login_required
def admin_search():
    """Admin-only comprehensive search results page"""
    if not current_user.is_staff():
        return render_template('errors/403.html'), 403
    
    query = request.args.get('q', '')
    results = admin_full_search(query)
    return render_template('admin/admin_search_results.html', **results)

