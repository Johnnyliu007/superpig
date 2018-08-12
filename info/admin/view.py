import time
from datetime import datetime, timedelta

from flask import current_app, jsonify
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import constants, db
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import blue_admin


# 添加分类
@blue_admin.route("/add_category", methods=["GET", "POST"])
def add_category():
    category_id = request.json.get("id")
    category_name = request.json.get("name")

    # 根据有没有id　判断是新增分类还是修改分类，　数据库category_id　是自增长，　不需要前端传
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno = RET.DBERR, errmsg="数据查询失败")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="未查询到分类信息")

        category.name = category_name
    else:
        category = Category()
        category.name = category_name

    try:
        db.session.add(category)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    return jsonify(errno=RET.OK, errmsg="OK")


# 分类管理
@blue_admin.route("/news_type")
def news_type():
    categories = Category.query.all()
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())
    category_list.pop(0)

    data = {
        "categories": categories
    }
    return render_template("admin/news_type.html", data=data)


# 已发布新闻编辑详情页
@blue_admin.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")

        if not news_id:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger(e)

        if not news:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        # 查询所有分类，　并检查当前新闻是哪个分类
        categories = Category.query.all()
        category_dict_list = []
        for category in categories:
            category_dict = category.to_dict()
            category_dict["is_selected"] = False
            if category.id == news.category_id:
                category_dict["is_selected"] = True
            category_dict_list.append(category_dict)

        category_dict_list.pop(0)

        data = {
            "news": news.to_dict(),
            "categories": category_dict_list
        }

        return render_template("admin/news_edit_detail.html", data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")

    if not all([news_id, title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")
    #　读取图片
    try:
        image_source = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片读取错误")

    #　上传图片
    try:
        key = storage(image_source)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="第三方错误")

    news.title = title
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="OK")


# 已发布新闻编辑列表
@blue_admin.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    current_page = 1
    total_page = 1
    items = []
    filters = []
    try:
        if keywords:
            filters = [News.title.contains(keywords)]
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    news_dict_list = []
    for item in items:
        news_dict_list.append(item.to_basic_dict())

    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_edit.html", data=data)


# 新闻审核详情
@blue_admin.route("/news_review_detail", methods=["GET", "POST"])
def news_review_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template("admin/news_review_detail.html",data={"errmsg": "参数错误"})

        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template("admin/news_review_detail.html", data={"errmsg": "未查询到此新闻"})

        data = {
            "news": news.to_dict()
        }
        return render_template("admin/news_review_detail.html", data=data)

    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not all([news_id, action]):
        return jsonify(errno = RET.PARAMERR, errmsg = "参数错误" )
    if action not in("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.PARAMERR, errmsg="未找到该新闻")

    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="新指出拒绝原因")
        news.status = -1
        news.reason = reason
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="数据保存失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


# 新闻审核
@blue_admin.route("/news_review")
def new_review():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    current_page = 1
    total_page = 1
    news_list = []
    filters = [News.status != 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for item in items:
        news_dict_list.append(item.to_review_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_dict_list
    }
    return render_template("admin/news_review.html", data=data)


# 用户列表
@blue_admin.route("/user_list")
def user_list():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
        current_page = 1
        total_page = 1
        items = []
    try:
        paginate = User.query.filter(User.is_admin != 1).order_by(User.last_login.desc()).paginate(page, 10, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    users_list = []
    for item in items:
        users_list.append(item.to_admin_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "users": users_list
    }

    return render_template("admin/user_list.html", data=data)


# 用户统计
@blue_admin.route("/user_count")
def user_count():
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    mon_count = 0
    try:
        now = time.localtime()
        mon_begin_day = "%d-%02d-01" % (now.tm_year, now.tm_mon)
        mon_begin_time = datetime.strptime(mon_begin_day, '%Y-%m-%d')
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_time).count()
    except Exception as e:
        current_app.logger.error(e)

    daily_count = 0
    try:
        day_begin = "%d-%02d-%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_time = datetime.strptime(day_begin, "%Y-%m-%d")
        daily_count = User.query.filter(User.is_admin == False, User.create_time >= day_begin_time).count()
    except Exception as e:
        current_app.logger.error(e)

    # 统计一个月的的每一天活跃用户量
    today_begin_time = datetime.strptime(day_begin, "%Y-%m-%d")
    # today_begin_time = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    active_date = []
    active_count = []
    for i in range(0, 30):
        begin_time =today_begin_time - timedelta(days=i)
        end_time = today_begin_time - timedelta(days=(i-1))
        active_date.append(begin_time.strftime('%Y-%m-%d'))
        count = 0
        try:
            count = User.query.filter(User.is_admin != 1, User.create_time>=begin_time, User.create_time<end_time).count()
        except Exception as e:
            current_app.logger.error(e)
        active_count.append(count)

    active_date.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": daily_count,
        "active_count": active_count,
        "active_date": active_date
    }

    return render_template("admin/user_count.html", data=data)


# 后台主页
@blue_admin.route("/index")
@user_login_data
def admin_index():
    user = g.user
    if user:
        user = user.to_dict()
    return render_template('admin/index.html', user=user)


# 后台登陆
@blue_admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # 去 session 中取指定的值
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        # 如果用户id存在，并且是管理员，那么直接跳转管理后台主页
        if user_id and is_admin:
            return redirect(url_for('admin.admin_index'))
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username, password]):
        return render_template('admin/login.html', errmsg="参数不足")
    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not user:
        return render_template('admin/login.html', errmsg="用户不存在")

    if not user.check_password(password):
        return render_template('admin/login.html', errmsg="密码错误")

    if not user.is_admin:
        return render_template('admin/login.html', errmsg="用户权限错误")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = True

    return redirect(url_for('admin.admin_index'))

# 登出
@blue_admin.route("/logout", methods=["GET","POST"])
def logout():
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    session.pop('is_admin', None)
    return redirect("/admin/login")

