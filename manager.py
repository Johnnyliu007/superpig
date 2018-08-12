# encoding: utf-8
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from info import create_app, db
from info import  models

app = create_app("develop")

manager = Manager(app)

migrate = Migrate(app, db)

manager.add_command("mysql", MigrateCommand)

# 添加用户(管理员)
from info.models import User
@manager.option('-n','--name',dest="name")
@manager.option('-p','--password',dest="password")
def create_super_user(name, password):
    user = User()
    user.nick_name = name
    user.password = password
    user.mobile = name
    user.is_admin = True
    db.session.add(user)
    db.session.commit()


# 主页蓝图注册
from info.index import blue_index
app.register_blueprint(blue_index)

# 登陆注册蓝图注册
from info.passport import blue_passport
app.register_blueprint(blue_passport)

# 新闻详情蓝图注册
from info.news import blue_news
app.register_blueprint(blue_news)

# 个人中心蓝图注册
from info.user import blue_user
app.register_blueprint(blue_user)

# 后台蓝图注册
from info.admin import blue_admin
app.register_blueprint(blue_admin)

if __name__ == '__main__':
    manager.run()


