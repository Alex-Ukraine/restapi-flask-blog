from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from src import session
from src.models.models import User, Post


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