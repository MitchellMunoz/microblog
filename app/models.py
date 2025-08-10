from flask import url_for
import pytz
from datetime import datetime, timezone
from typing import Optional
from hashlib import md5
import json
import sqlalchemy as sa
import sqlalchemy.orm as so
import jwt
from time import time
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from app.search import add_to_index, remove_from_index, query_index

guatemala_tz = pytz.timezone('America/Guatemala')


class SearchableMixin:
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = sa.select(cls).where(cls.id.in_(ids)).order_by(
            db.case(*when, value=cls.id))
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True)
)


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    photo: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256), default='default.jpg')
    last_seen: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    last_message_read_time: so.Mapped[Optional[datetime]] = so.mapped_column()
    token: so.Mapped[Optional[str]] = so.mapped_column(sa.String(32), index=True, unique=True)
    token_expiration: so.Mapped[Optional[datetime]] = so.mapped_column()
    notifications: so.WriteOnlyMapped['Notification'] = so.relationship(
        back_populates='user')

    posts: so.WriteOnlyMapped['Post'] = so.relationship(
        back_populates='author')
    tasks_created: so.WriteOnlyMapped['Task'] = so.relationship(
        foreign_keys='Task.created_by', back_populates='creator')
    tasks_completed: so.WriteOnlyMapped['Task'] = so.relationship(
        foreign_keys='Task.completed_by', back_populates='completer')

    messages_sent: so.WriteOnlyMapped['Message'] = so.relationship(
        foreign_keys='Message.sender_id', back_populates='author')

    messages_received: so.Mapped[list['Message']] = so.relationship(
        foreign_keys='Message.recipient_id', back_populates='recipient', lazy='select')


    following: so.Mapped[list['User']] = so.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates='followers',
        lazy='dynamic'
    )

    followers: so.Mapped[list['User']] = so.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following',
        lazy='dynamic'
    )

    def get_task_in_progress(self, task_name: Optional[str] = None) -> Optional['Task']:
        query = db.session.query(Task).filter_by(created_by=self.id, completed=False)

        if task_name:
            query = query.filter_by(text=task_name)

        return query.first()

    def set_password(self, password: str):
        self.password_hash = password

    def check_password(self, password: str) -> bool:
        return self.password_hash == password



    def avatar(self, size):
        if self.photo and self.photo != 'default.jpg':
            return url_for('static', filename='profile_pics/' + self.photo)
        else:
            digest = md5(self.email.lower().encode('utf-8')).hexdigest()
            return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def follow(self, user):
        if not self.is_following(user):
            self.following.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        stmt = sa.select(followers).where(
            followers.c.follower_id == self.id,
            followers.c.followed_id == user.id
        )
        return db.session.execute(stmt).first() is not None

    def followers_count(self):
        stmt = sa.select(sa.func.count()).select_from(followers).where(
            followers.c.followed_id == self.id
        )
        return db.session.scalar(stmt)

    def following_count(self):
        stmt = sa.select(sa.func.count()).select_from(followers).where(
            followers.c.follower_id == self.id
        )
        return db.session.scalar(stmt)

    def add_notification(self, name, data):
        stmt = sa.delete(Notification).where(
            Notification.user_id == self.id,
            Notification.name == name
        )
        db.session.execute(stmt)
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

    def unread_message_count(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter(
            Message.recipient_id == self.id,
            Message.timestamp > last_read_time
        ).count()

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class Group(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False, unique=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, index=True, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Group {self.name}>'


class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)


class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    sender_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    recipient_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, index=True, default=lambda: datetime.now(timezone.utc))

    author: so.Mapped['User'] = so.relationship(
        'User', foreign_keys=[sender_id], back_populates='messages_sent')
    recipient: so.Mapped['User'] = so.relationship(
        'User', foreign_keys=[recipient_id], back_populates='messages_received')


class Notification(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    timestamp: so.Mapped[float] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc).timestamp())
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)

    user: so.Mapped['User'] = so.relationship(back_populates='notifications')

    def get_data(self):
        return json.loads(self.payload_json)

class Task(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    created_by: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    completed_by: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id'), nullable=True, index=True)
    text: so.Mapped[str] = so.mapped_column(sa.String(140))
    completed: so.Mapped[bool] = so.mapped_column(default=False)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, index=True, default=lambda: datetime.now(guatemala_tz))
    completion_date: so.Mapped[Optional[datetime]] = so.mapped_column(sa.DateTime, nullable=True)

    creator: so.Mapped['User'] = so.relationship(
        'User', foreign_keys=[created_by], back_populates='tasks_created')
    completer: so.Mapped[Optional['User']] = so.relationship(
        'User', foreign_keys=[completed_by], back_populates='tasks_completed')

    def complete(self, user_id: int):
        self.completed = True
        self.completed_by = user_id
        self.completion_date = datetime.now(guatemala_tz)

    def __repr__(self):
        return f'<Task {self.text}>'

    def get_task_in_progress(self):
        return Task.query.filter_by(created_by=self.created_by, completed=False).first()
