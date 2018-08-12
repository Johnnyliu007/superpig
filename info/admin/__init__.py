from flask import Blueprint
from flask import redirect
from flask import request
from flask import session

blue_admin = Blueprint("admin", __name__, url_prefix="/admin")
from . import view

# 后台页面权限管理，只准访问登陆页面，防止其他用户直接访问后台登陆页面外的其他页面
@blue_admin.before_request
def check_admin():
    is_admin = session.get("is_admin")
    if not is_admin and not request.url.endswith("/admin/login"):
        return redirect('/')


