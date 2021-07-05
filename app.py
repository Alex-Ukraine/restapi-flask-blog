import datetime

from flask import Flask, jsonify, request, g, make_response
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from sqlalchemy.orm import relationship
from flask_jwt_extended import create_access_token
from datetime import timedelta
from passlib.hash import bcrypt
from config import Config

from marshmallow import fields, ValidationError, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


app = Flask(__name__)

app.config.from_object(Config)

engine = create_engine(app.config['DATABASE'])

session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = session.query_property()

jwt = JWTManager(app)


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
        expire_delta = timedelta(expire_time)
        token = create_access_token(
            identity=self.id, expires_delta=expire_delta)
        return token

    @classmethod
    def authenticate(cls, email, password):
        user = cls.query.filter(cls.email == email).one()
        if not bcrypt.verify(password, user.password):
            raise Exception('No user with this password')
        return user


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_relationships = True
        load_instance = True
        sqla_session = session

    name = fields.String(validate=validate.Regexp(r'^[A-Za-zА-Яа-я0-9\s\'`\.]{1,100}$'), required=True)
    password = fields.String(validate=validate.Regexp(r'^[^\s]{1,100}$'), required=True)
    email = fields.String(validate=validate.Regexp(r'^[A-Za-z0-9]{1,50}@[A-Za-z0-9\.]{1,50}$'), required=True)


class PostSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Post
        include_relationships = True
        load_instance = True
        sqla_session = session

    id = fields.Int(required=False)
    title = fields.String(validate=validate.Regexp(r'^[A-Za-zА-Яа-я0-9\s\'`\.]{1,100}$'), required=True)
    content = fields.String(required=True)
    liked = fields.Int(required=True)
    unliked = fields.Int(required=True)
    user_id = fields.Int(required=True)


Base.metadata.create_all(bind=engine)


@app.route('/api', methods=['GET'])
@jwt_required()
def get_list():
    post_schema = PostSchema(only=("id", "title", "content", "liked", "unliked", "user_id"))
    g.user_id = get_jwt_identity()
    posts = Post.query.all()
    return make_response(jsonify(post_schema.dump(posts, many=True)), 200)


@app.route('/api/analytics', methods=['GET'])
@jwt_required()
def get_count_likes():
    g.user_id = get_jwt_identity()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not (date_to and date_to):
        return make_response(jsonify({'Message': 'some parameters not exists'}), 400)

    try:
        date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')
    except Exception as e:
        return make_response(jsonify({'Message': f'error: {e}'}), 400)

    if date_from > date_to:
        return make_response(jsonify({'Message': 'date_from > date_to'}), 400)

    count = Association.query.filter(Association.date.between(date_from, date_to), Association.which_one=="like").count()

    return make_response(jsonify({"likes": count}), 200)


@app.route('/api/user-activity', methods=['GET'])
@jwt_required()
def get_info_user_activity():
    user_id = get_jwt_identity()
    g.user_id = user_id
    user = User.query.filter(User.id == user_id).first()
    last_login = datetime.datetime.strftime(datetime.datetime.fromtimestamp(get_jwt()['nbf']), '%Y-%m-%d %H-%M-%S')
    last_request = datetime.datetime.strftime(datetime.datetime.fromtimestamp(user.last_request), '%Y-%m-%d %H-%M-%S')
    return make_response(jsonify({"last login": last_login, "last_request": last_request}), 200)


@app.route('/api', methods=['POST'])
@jwt_required()
def create_post():
    post_schema = PostSchema(only=("id", "title", "content", "liked", "unliked", "user_id"))

    user_id = get_jwt_identity()
    g.user_id = user_id
    item = request.json
    item['liked'] = 0
    item['unliked'] = 0
    item['user_id'] = user_id

    try:
        new_one = post_schema.load(item)
    except ValidationError as e:
        return make_response(jsonify({'Message': f'error: {e}'}), 400)

    session.add(new_one)
    session.commit()
    return make_response(jsonify(post_schema.dump(new_one)), 201)


@app.route('/api/<int:post_id>', methods=['PUT'])
@jwt_required()
def like_unlike_post(post_id):
    post_schema = PostSchema(only=("id", "title", "content", "liked", "unliked", "user_id"))
    user_id = get_jwt_identity()
    g.user_id = user_id
    user = User.query.filter(
        User.id == user_id
    ).first()

    item = Post.query.filter(
        Post.id == post_id
    ).first()

    params = request.json
    if not item:
        return make_response(jsonify({'message': 'No posts with this id'}), 400)

    query = Association.query.filter(Association.post_id == post_id, Association.user_id == user_id).first()

    if params.get('liked') == "True": # хочу лайк
        if query: # уже есть лайк или дизлайк
            if not query.which_one == "like": # нет лайка
                join = query
                join.which_one = "like"
                join.user = user
                item.users.append(join)
                item.liked += 1
                item.unliked -= 1
        else:
            join = Association(which_one="like")
            join.user = user
            item.users.append(join)
            item.liked += 1

    elif params.get('unliked') == "True": # хочу дизлайк
        if query: # уже есть лайк или дизлайк
            if not query.which_one == "unlike": # нет дизлайка
                join = query
                join.which_one = "unlike"
                join.user = user
                item.users.append(join)
                item.unliked += 1
                item.liked -= 1
        else:
            join = Association(which_one="unlike")
            join.user = user
            item.users.append(join)
            item.unliked += 1

    session.add(item)
    session.commit()
    return make_response(jsonify(post_schema.dump(item)), 201)


@app.route('/register', methods=['POST'])
def register():
    user_schema = UserSchema()
    params = request.json
    try:
        user = user_schema.load(params)
    except ValidationError as e:
        return make_response(jsonify({'Message': f'error: {e}'}), 400)
    session.add(user)
    session.commit()
    token = user.get_token()
    return make_response(jsonify({'access_token': token}), 201)


@app.route('/login', methods=['POST'])
def login():
    user_schema = UserSchema(only=("email", "password"))

    params = request.json

    validation_errors = user_schema.validate(params)
    if validation_errors:
        return make_response(jsonify({'Message': f'error: {validation_errors}'}), 400)

    user = User.authenticate(**params)

    token = user.get_token()
    return make_response(jsonify({'access_token': token}), 200)


@app.after_request
def after_request_func(response):
    user_id = g.get('user_id')
    if user_id:
        last_request = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
        User.query.filter(User.id == user_id).update({"last_request": last_request})
        session.commit()
    return response


@app.teardown_appcontext
def shutdown_session(exception=None):
    session.remove()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port='5000')
