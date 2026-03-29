from .auth import auth_bp
from .student import student_bp
from .proctor import proctor_bp
from .chat import chat_bp
from .parent import parent_bp
from .connect_hub import connect_bp
from .account import account_bp  # FIX #48: password change

def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(proctor_bp, url_prefix='/proctor')
    app.register_blueprint(chat_bp)
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(connect_bp, url_prefix='/student')
    app.register_blueprint(account_bp)  # FIX #48

    # FIX #14: API versioning — register versioned aliases for backwards compatibility
    # New clients should use /api/v1/student/..., old URLs still work
    app.register_blueprint(student_bp, url_prefix='/api/v1/student', name='student_v1')
    app.register_blueprint(chat_bp, url_prefix='/api/v1', name='chat_v1')

