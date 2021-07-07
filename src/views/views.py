import datetime

from flask import g, jsonify, make_response, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError

from src import app, session
from src.models.models import Post, Association, User
from src.models.schemas import PostSchema, UserSchema


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
    if User.query.filter(User.email == params.get('email')).first():
        return make_response(jsonify({'Message': f'error: not unique email'}), 409)

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