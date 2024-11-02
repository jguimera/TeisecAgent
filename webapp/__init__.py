from flask import Flask
from flask_socketio import SocketIO
from app.TeisecAgent  import TeisecAgent
  
socketio = SocketIO()
teisecAgent=TeisecAgent(None)
def create_app(debug=False):
    """Create an application."""
    app = Flask(__name__)
    app.debug = debug
    app.config['SECRET_KEY'] = 'gg65gjr39dkjn344_!67#'
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    socketio.init_app(app)
    return app
def auth_app(auth_type='interactive'):
    print('DEBUG: Loading Auth After App creation')
    teisecAgent.launch_auth(auth_type)
