from .auth import auth_bp
from .student import student_bp
from .proctor import proctor_bp
from .chat import chat_bp
from .parent import parent_bp

def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(proctor_bp, url_prefix='/proctor')
    app.register_blueprint(chat_bp)
    app.register_blueprint(parent_bp, url_prefix='/parent')
