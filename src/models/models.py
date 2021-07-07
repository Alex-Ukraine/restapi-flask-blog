import datetime
import sqlalchemy as db
from passlib.hash import bcrypt
from flask_jwt_extended import create_access_token
from sqlalchemy.orm import relationship

from src import Base


class Association(Base):
    __tablename__ = 'association'
    post_id = db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
    which_one = db.Column('which_one', db.String)
    date = db.Column('date', db.Date)

    user = relationship("User", back_populates="posts")
    post = relationship("Post", back_populates="users")

    def __init__(self, post_id=None, user_id=None, which_one=None, date=None):
        self.post_id = post_id
        self.user_id = user_id
        self.which_one = which_one
        self.date = datetime.datetime.utcnow()

    def __repr__(self):
        return f"{self.post_id} {self.user_id} {self.which_one} {self.date}"


class Post(Base):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(250), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    liked = db.Column(db.Integer)
    unliked = db.Column(db.Integer)
    users = relationship(
        'Association', back_populates='post', lazy=True
    )


class User(Base):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    last_request = db.Column(db.Integer)

    posts = relationship(
        'Association', back_populates='user', lazy=True
    )

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.email = kwargs.get('email')
        self.password = bcrypt.hash(kwargs.get('password'))
        self.last_request = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))

    def get_token(self, expire_time=24):
        expire_delta = datetime.timedelta(expire_time)
        return create_access_token(
            identity=self.id, expires_delta=expire_delta)

    @classmethod
    def authenticate(cls, email, password):
        user = cls.query.filter(cls.email == email).one()
        if not bcrypt.verify(password, user.password):
            raise Exception('No user with this password')
        return user