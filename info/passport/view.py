import random
from datetime import datetime

from flask import current_app, jsonify
from flask import make_response
from flask import request
from flask import session

from info import constants, redis_store, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import blue_passport
import re


"""
1. 获取参数和判断是否有值
2. 从数据库查询出指定的用户
3. 校验密码
4. 保存用户登录状态
5. 返回结果
:return:
"""
@blue_passport.route("/login", methods = ["GET", "POST"])
def login():
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    print(mobile, password)
    if not all([mobile, password]):
        return jsonify(errno = RET.PARAMERR, errmsg = "请输入完整数据")
    try:
        user = User.query.filter(User.mobile == mobile)  # 得到的是一个查询结果对象
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg = "查询数据错误")
    # print(user)
    user = user.first()  # 得到的是一个查询结果对象
    # print(user)
    if not user:
        return jsonify(errno = RET.PARAMERR, errmsg = "用户名不存在")
    if not user.check_password(password):
        return jsonify(errno=RET.PARAMERR, errmsg = "请输入正确的密码")

    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name

    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg= "数据保存错误")
    return jsonify(errno=RET.OK, errmsg= "登陆成功")


"""
1. 获取参数和判断是否有值
2. 从redis中获取指定手机号对应的短信验证码的
3. 校验验证码
4. 初始化 user 模型，并设置数据并添加到数据库
5. 保存当前用户的状态
6. 返回注册的结果
:return:
"""
@blue_passport.route("/register", methods=["GET", "POST"])
def register():
    mobile = request.json.get("mobile")
    smscode = request.json.get("smscode")
    password = request.json.get("password")
    if not all([mobile, smscode, password]):
        return jsonify(errno = RET.PARAMERR, errmsg = "请不全数据")
    try:
        local_sms_code = redis_store.get("sms_code_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="获取短信验证码失败")

    if not local_sms_code:
        return jsonify(errno=RET.PARAMERR, errmsg="短信验证码过期")

    if local_sms_code != smscode:
        return jsonify(errno=RET.PARAMERR, errmsg="请输入正确的短信验证码")
    try:
        redis_store.delete("sms_code_" + mobile)
    except Exception as e:
        current_app.logger.error(e)

    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        # 数据保存错误
        return jsonify(errno=RET.DATAERR, errmsg="数据保存错误")
    # 保存用户登陆状态, 每个用户的数据作为一组数据存贮（hset），在redis里只的键是session开头随机值， 里面的值是加密的
    # 删除是用pop（“key1”， None）
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile

    return jsonify(errno = RET.OK, errmsg = "注册成功")



"""
    接收前端发送过来的请求参数
    检查参数是否已经全部传过来
    判断手机号格式是否正确
    检查图片验证码是否正确，若不正确，则返回
    删除图片验证码
    生成随机的短信验证码
    使用第三方SDK发送短信验证码
"""
@blue_passport.route("/sms_code", methods=["GET", "POST"])
def sms_code():
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    print(mobile, image_code_id)
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno = RET.PARAMERR, errmsg = "请输入完整数据")

    if not re.match(r"1[3456789]\d{9}", mobile):
        return jsonify(errno = RET.PARAMERR, errmsg = "请输入正确的手机号")
    try:
        real_image_code = redis_store.get("image_code_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="获取验证码失败")

    if not real_image_code:
        return jsonify(errno=RET.PARAMERR, errmsg="验证码已过期")

    if real_image_code.lower() != image_code.lower():
        return jsonify(errno = RET.PARAMERR, errmsg = "请输入正确的验证码")

    redis_store.delete("image_code_" + image_code_id)  # 删除验证码

    generate_sms_code = "%06d" % random.randint(1, 999999)
    redis_store.set("sms_code_" + mobile, generate_sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    print("短信验证码：", generate_sms_code)
    # result = CCP().send_template_sms(mobile, [generate_sms_code, 5], 1)
    # if result != 0:
    #     return jsonify(errno=RET.PARAMERR, errmsg="第三方错误")
    print("短信验证码发送成功")
    return jsonify(errno=RET.OK, errmsg="短信验证码发送成功")


"""
    前端页生成验证码编号，并将编号并提交到后台去请求验证码图片
    后台生成图片验证码，并把验证码文字内容当作值，验证码编号当作key存储在 redis 中
    后台把验证码图片当作响应返回给前端
    前端申请发送短信验证码的时候带上第1步验证码编号和用户输入的验证码内容
    后台取出验证码编号对应的验证码内容与前端传过来的验证码内容进行对比
    如果一样，则向指定手机发送验证码，如果不一样，则返回验证码错误
"""
@blue_passport.route("/image_code")
def image_code():
    code_id = request.args.get("code_id")
    name, code_val, code_pic = captcha.generate_captcha()
    print("图片验证码", code_val)
    try:
        redis_store.set("image_code_" + code_id, code_val,constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno = RET.DATAERR, errmsg = "图片验证码保存失败")
    resp = make_response(code_pic)
    resp.headers["Content-Type"] = "image/jpg"
    return resp


@blue_passport.route("/logout", methods = ["GET", "POST"])
def logout():
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    # session.pop("")

    return jsonify(errno=RET.OK, errmsg="OK")



