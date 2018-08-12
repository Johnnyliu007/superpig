# 首页左边， 点击排行的 过滤器
from flask import g
from flask import session

from info.models import User
import functools


def specify_style(paras):
    if paras == 1:
        return "first"
    elif paras == 2:
        return "second"
    elif paras == 3:
        return "third"
    else:
        return ""


# 装饰器， 判断是否登陆
def user_login_data(f):
    @functools.wraps(f)  # 保持函数名不变
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        user = None

        if user_id:
            user = User.query.get(user_id)

        g.user = user
        return f(*args, **kwargs)
    return wrapper
