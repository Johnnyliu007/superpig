from flask import current_app, jsonify
from flask import g
from flask import render_template
from flask import request
from flask import session

from info import constants
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import blue_index


@blue_index.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("news/favicon.ico")


@blue_index.route("/")
@user_login_data
def index():

    # 点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_new_list = []
    for news in news_list if news_list else []:
        every_news = news.to_basic_dict()
        click_new_list.append(every_news)

    # 分类
    category_list = []
    categories = Category.query.all()
    for category in categories:
        category_list.append(category.to_dict())

    data = {
        "user_info" : g.user.to_dict() if g.user else None,
        "click_new_list": click_new_list,
        "category_list": category_list
    }

    return render_template("news/index.html", data = data)

# 获取新闻内容
@blue_index.route("/news_list")
def news_body():
    cid = request.args.get("cid", 1)
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        cid = 1
        page = 1
        per_page = 10
        current_app.logger.error(e)

    filters =[News.status == 0]
    if cid != 1:
        filters.append(News.category_id == cid)

    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    items = paginate.items
    total_page = paginate.pages
    current_page = paginate.page

    new_list = []

    for news in items:
        new_list.append(news.to_dict())

    data = {
        "total_page" : total_page,
        "current_page" : current_page,
        "news_dict": new_list
    }

    return jsonify(errno=RET.OK, errmsg="OK", data =data)





