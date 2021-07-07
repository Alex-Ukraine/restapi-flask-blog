from flask import Flask

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from flask_jwt_extended import JWTManager
from config import Config

app = Flask(__name__)

app.config.from_object(Config)

engine = create_engine(app.config['DATABASE'])

session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = session.query_property()

jwt = JWTManager(app)

from src.models import models
from src.models import schemas
from src.views import views


Base.metadata.create_all(bind=engine)

