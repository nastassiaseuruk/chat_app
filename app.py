from flask import Flask, render_template, request, url_for, redirect, session
from flask_user import login_required, SQLAlchemyAdapter, UserManager, UserMixin
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user

app = Flask(__name__)


POSTGRES = {
    'user': 'postgres',
    'pw': '123456',
    'db': 'chat_db',
    'host': 'localhost',
    'port': '5432'

}
app.config['SECRET_KEY'] = 'jjjj'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
app.config['CSRF_ENABLED'] = True
app.config['USER_ENABLE_EMAIL'] = False
app.config['USER_AUTO_LOGIN'] = False

db = SQLAlchemy()
socketio = SocketIO(app)


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False, server_default=" ")
    active = db.Column(db.Boolean(), nullable=False, server_default='0')


db_adapter = SQLAlchemyAdapter(db, User)
user_manager = UserManager(db_adapter, app)

db.init_app(app)


@app.route('/')
def index():
    # if current_user.is_authenticated:
    #     return redirect(url_for('user.logout'))

    return render_template('chat_app.html')


@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

# @app.route('/profile')
# @login_required
# def profile():
#     return "ololoo"


if __name__ == '__main__':
    socketio.run(app)