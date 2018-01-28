# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, url_for, redirect, session
from flask_user import login_required, SQLAlchemyAdapter, UserManager, UserMixin
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
from datetime import datetime
from tasks import make_celery
from celery.schedules import crontab
from datetime import datetime, timedelta

app = Flask(__name__)


POSTGRES = {
    'user': 'postgres',
    'pw': '123456',
    'db': 'chat_db',
    'host': 'localhost',
    'port': '5432',
    'encoding': 'UTF8'

}
app.config['SECRET_KEY'] = 'jjjj'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
app.config['CSRF_ENABLED'] = True
app.config['USER_ENABLE_EMAIL'] = False
app.config['USER_AUTO_LOGIN'] = False
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'db+sqlite:///home/nastassia/PycharmProjects/chat_app/results.db'

celery = make_celery(app)

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    db.init_app(app)
    return app


socketio = SocketIO(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False, server_default=" ")
    active = db.Column(db.Boolean(), nullable=False, server_default='0')
    messages = db.relationship('Message', backref='user', lazy=True)

    def __repr__(self):
        return self.username


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    author = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    published = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FilteredWords(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String, nullable=False)


db_adapter = SQLAlchemyAdapter(db, User)
user_manager = UserManager(db_adapter, app)

db.init_app(app)


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    else:
        return redirect(url_for('/user/sign-in')) #посмотреть название вью урла


@app.route('/chat')
@login_required
def chat():
    messages = Message.query.all()
    user = User.query.filter_by(username=current_user.username).first()
    users = User.query.all()
    users_online = []
    for user in users:
        if user in session:
            users_online.append(user)
    return render_template('chat_app.html', messages=messages, user=user, users_online=users_online)


@app.route('/message/<id>')
def message_delete(id):
    message_to_delete = Message.query.get(id)
    db.session.delete(message_to_delete)
    db.session.commit()
    return redirect('chat')


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """ to check if these works"""
    sender.add_periodic_task(
        crontab(hour=14, minute=30),
        delete_old_messages(),
    )


@celery.task(name='app.delete_old_messages')
def delete_old_messages():
    since = datetime.now() - timedelta(hours=24)
    messages_to_delete = Message.query.filter_by(Message.published < since).all()
    db.session.delete(messages_to_delete)
    db.session.commit()


@socketio.on('message')
def handle_message(msg):
    user = current_user
    username = current_user.username
    message = Message(message=msg, author=user.id)
    print(type(msg))
    db.session.add(message)
    db.session.commit()
    send(username + ": " + msg, broadcast=True)


if __name__ == '__main__':
    socketio.run(app)