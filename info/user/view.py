from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session

from info import constants
from info import db
from info.models import Category, News, User
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import blue_user


# 其他用户新闻列表
@blue_user.route("/other_news_list")
@user_login_data
def other_news_list():
    user = g.user

    user_id = request.args.get("user_id")
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    if not all([page, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not other_user:
        return jsonify(errno=RET.DBERR, errmsg="该用户不存在")

    items = []
    current_page = 1
    total_page = 1

    try:
        paginate = News.query.filter(News.user_id == other_user.id).paginate(page, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    other_news_list = []
    for item in items:
        other_news_list.append(item.to_dict())

    data = {
        "news_list": other_news_list,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


# 其他，点击详情页的作者名跳转到作者的详情页面
@blue_user.route("/other_info")
@user_login_data
def other_info():
    user = g.user

    user_id = request.args.get("id")

    if not user_id:
        return abort(404)

    try:
        author = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    if not author:
        abort(404)

    is_followed = False
    if user:
        if author in user.followed:
            is_followed = True

    data = {
        "user_info": user.to_dict() if user else None,
        "other_info": author.to_dict(),
        "is_followed": is_followed
    }

    return render_template("news/other.html", data=data)


# 关注列表
@blue_user.route("/user_follow",methods=["GET", "POST"])
@user_login_data
def user_follow():
    user = g.user

    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    items = []
    current_page = 1
    total_page = 1

    try:
        paginate = user.followed.paginate(page, constants.USER_FOLLOWED_MAX_COUNT, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_list = []

    for item in items:
        user_dict_list.append(item.to_dict())

    data = {
        "users": user_dict_list,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("news/user_follow.html", data=data)


#　个人新闻列表
@blue_user.route("/news_list")
@user_login_data
def news_list():
    user = g.user
    p = request.args.get("q", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    paginate = News.query.filter(News.user_id == user.id).paginate(p, 5, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    all_news_list = []
    for item in items:
        all_news_list.append(item.to_review_dict())

    data = {
        "news_list": all_news_list,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template('news/user_news_list.html', data=data)


# 发布新闻
@blue_user.route("/news_release", methods = ["GET", "POST"])
@user_login_data
def news_release():
    user = g.user
    if not user:
        redirect("/")

    if request.method == "GET":
        categories_list = []
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="获取数据失败")

        for category in categories:
            categories_list.append(category.to_dict())

        categories_list.pop(0)

        return render_template("news/user_news_release.html", data={"categories":categories_list})

    # POST 提交过来的新闻数据
    title = request.form.get("title")
    source = "个人发布"
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    content = request.form.get("content")

    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    avatar = index_image.read()

    key = storage(avatar)

    news = News()
    news.title = title
    news.source = source
    news.category_id = category_id
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.user_id = user.id
    news.status = 1
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="发布成功，等待审核")


# 个人新闻收藏
@blue_user.route("/collection")
@user_login_data
def collection():
    user = g.user
    if not user:
        return redirect("/")

    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    paginate = user.collection_news.paginate(p, 5, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    collections_list = []
    for item in items:
        collections_list.append(item.to_basic_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "collections": collections_list
    }
    return render_template("news/user_collection.html", data=data)


# 修改密码
@blue_user.route("/pass_info", methods= ["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user
    if not user:
        redirect("/")
    if request.method == "GET":
        return render_template("news/user_pass_info.html")

    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="请求参数错误")
    # 一定要先检验旧密码，　就密码不对，　不让修改
    if not user.check_password(old_password):
        return jsonify(errno=RET.DATAERR, errmsg="原密码错误")

    # 更新密码
    user.password = new_password
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="OK")


#　修改头像
@blue_user.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    user = g.user
    if request.method == "GET":
        if not user:
            redirect("/")
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/user_pic_info.html", data=data)
    # 接收上传的头像
    avatar = request.files.get("avatar").read()
    key = storage(avatar)

    user.avatar_url = key

    db.session.commit()

    data = {
        "avatar_url":constants.QINIU_DOMIN_PREFIX + key
    }

    return jsonify(errno=RET.OK, errmsg="OK", data=data)


# 基本资料
@blue_user.route("/base_info", methods=["GET", "POST"])
@user_login_data
def user_login():
    user = g.user
    if request.method == "GET":

        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/user_base_info.html", data=data)
    # POST 提交来的新数据
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if gender not in ("MAN", "WOMAN"):
        return jsonify(errno=RET.PARAMERR, errmsg="心别参数所悟")

    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    #　更新完毕，　要让昵称显示更新
    session["nick_name"] = nick_name

    return jsonify(errno=RET.OK, errmsg="资料更新成功")




#　个人中心页面
@blue_user.route("/info", methods = ["GET", "POST"])
@user_login_data
def get_user_center():
    user = g.user
    if not user:
        redirect("/")

    data={
        "user_info":user.to_dict() if user else None
    }
    return render_template("news/user.html", data=data)