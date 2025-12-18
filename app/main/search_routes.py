from flask import render_template, request, jsonify
from app.main import bp
from app.main.search_utils import search_suggestions, full_text_search, ext_search

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



# Force reload
