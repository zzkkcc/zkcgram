# -*- encoding= UTF-8 -*-
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# define an application
app = Flask(__name__)
# jinjia is used for html coding work
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.config.from_pyfile('app.conf')
app.secret_key = 'Zkc007'
# difine database db from sqlalchemy
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = '/regloginpage/'

from zkcgram import views, models
