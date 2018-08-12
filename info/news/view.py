from flask import abort, jsonify
from flask import current_app
from flask import g
from flask import render_template
from flask import request

from info import constants, db
from info.models import User, News, Comment, CommentLike
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import blue_news


# 关注与取消关注
@blue_news.route("/followed_user", methods=["GET", "POST"])
@user_login_data
def followed_user():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    author_id = request.json.get("user_id")
    action = request.json.get("action")

    if not all([author_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")

    if not author:
        return jsonify(errno=RET.NODATA, errmsg="未找到该作者")

    if action == "follow":
        if author not in user.followed:
            user.followed.append(author)
        else:
            return jsonify(errno = RET.NODATA,errmsg = "已经关注")
    else:
        if author in user.followed:
            user.followed.remove(author)
        else:
            return jsonify(errno = RET.NODATA,errmsg = "还没有关注")

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    return jsonify(errno=RET.OK, errmsg="OK")


# 点赞
@blue_news.route('/comment_like', methods=["GET" ,"POST"])
@user_login_data
def set_comment_like():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    comment_id = request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="未知操作")

    # 查询评论是否存在
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.looger.error(e)
        return jsonify(errno = RET.DBERR, errmsg = "数据获取失败")

    if not comment:
        return jsonify(errno=RET.DBERR, errmsg="评论不存在")
    # 点赞
    if action == "add":
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id).order_by(CommentLike.comment_id.desc()).first()
        # 判断是否点赞， 如果已点赞，怎不能在点赞， 否则可以点赞
        if not comment_like:  # comment_like 结果为空则说明为点赞
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            db.session.commit()
            # 点赞数加１
            comment.like_count += 1
    else:
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id).order_by(CommentLike.comment_id.desc()).first()
        # 如果 已点赞， 则可以取消点赞
        if comment_like:
            db.session.delete(comment_like)  # 直接删除整条数据
            # 点赞数减１
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


# 新闻评论
@blue_news.route("/news_comment", methods=["GET", "POST"])
@user_login_data
def news_comment():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    news_id = request.json.get("news_id")
    comment_str = request.json.get("comment")
    parent_id = request.json.get("parent_id")

    # 只有是回复是才有父评论
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻已经不存在")

    comment = Comment()
    comment.news_id = news_id
    comment.user_id = user.id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存评论数据失败")
    return jsonify(errno=RET.OK, errmsg="评论成功", data=comment.to_dict())


# 新闻收藏
@blue_news.route("/news_collect", methods=["GET", "POST"])
@user_login_data
def news_collect():
    user = g.user
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not user:
        return jsonify(errno = RET.PARAMERR, errmsg = "请先登陆")

    if not news_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ("collect", "cancel_collect"):
        return jsonify(errno=RET.PARAMERR, errmsg="未知操作")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻数据不存在")

    if action == "collect":
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存失败")

    return jsonify(errno=RET.OK, errmsg="操作成功")


# 新闻详情页面
@blue_news.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    user = g.user
    # 点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_new_list = []
    for news in news_list if news_list else []:
        every_news = news.to_basic_dict()
        click_new_list.append(every_news)

    # 每次进入，代表该新闻点击量加1
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    if not news:
        abort(404)

    news.clicks += 1

    # 展示评论
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据获取失败")

    # 判断用户是否已对该新闻点赞
    comments_like_ids = []
    if user:
        comments_likes = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        comments_like_ids = [comment_like.comment_id for comment_like in comments_likes]

    comments_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        if comment.id in comments_like_ids:
            comment_dict["is_like"] = True
        comments_list.append(comment_dict)

    # 判断用户是否收藏该新闻
    is_collected = False
    is_focus = False

    if user:
        if news in user.collection_news:
            is_collected = True
        if news.user in user.followed:
            is_focus = True

    data = {"user_info": g.user.to_dict() if g.user else None,
            "news": news.to_dict(),
            "click_new_list": click_new_list,
            "is_collected": is_collected,
            "is_followed": is_focus,
            "comments": comments_list
            }
    return render_template("news/detail.html", data=data)
