from flask import render_template, request, jsonify
from app.main import bp
from app.main.search_utils import search_suggestions, full_text_search

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
