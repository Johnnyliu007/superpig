import logging
from logging.handlers import RotatingFileHandler

import redis
from flask import Flask
from flask import g
from flask import make_response
from flask import render_template
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

from config import Config,DevelopConfig,ProcutionConfig,config_map


logging.basicConfig(level=logging.DEBUG) # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

db = SQLAlchemy()

# 设置日志的记录等级
from info.utils.common import specify_style

redis_store = None # type:redis.StrictRedis

def create_app(config_name):
    app = Flask(__name__)

    nowConfig = config_map.get(config_name)

    app.config.from_object(nowConfig)

    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host=nowConfig.REDIS_HOST, port=nowConfig.REDIS_PORT, decode_responses=True)

    Session(app)

    app.add_template_filter(specify_style, "specify_style")

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @user_login_data
    def page_not_found(response):
        user = g.user
        data = {"user_info": user.to_dict() if user else None}
        return render_template('news/404.html', data=data)

    CSRFProtect(app)

    return app