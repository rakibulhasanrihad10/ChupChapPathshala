from app.main import bp

@bp.route('/')
def index():
    return "<h1>Library System is LIVE and Connected to the Cloud!</h1>"
