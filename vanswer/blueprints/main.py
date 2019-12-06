# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
import json

from flask import render_template, flash, redirect, url_for, current_app, \
    send_from_directory, request, abort, Blueprint, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from collections import OrderedDict

from vanswer.decorators import confirm_required, permission_required
from vanswer.extensions import db
from vanswer.forms.main import SurveyForm
from vanswer.models import User, Survey, SurveyQuestion, QuestionOption, Collect, Notification, UserAnswer
from vanswer.notifications import push_collect_notification
from vanswer.utils import redirect_back, flash_errors, get_time_str, get_question_type, get_survey

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    survey_type = request.args.get('type', 'all')
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['VANSWER_SURVEY_PER_PAGE']

        pagination = get_survey[survey_type](Survey) \
            .filter(Survey.author_id == current_user.id) \
            .order_by(Survey.timestamp.desc()) \
            .paginate(page, per_page)

        surveys = pagination.items
    else:
        pagination = None
        surveys = None
    return render_template('main/index.html', pagination=pagination, surveys=surveys)


@main_bp.route('/explore')
def explore():
    survey_type = request.args.get('type')
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['VANSWER_SURVEY_PER_PAGE']
        a = Survey.query.all()
        try:
            pagination = Survey.query.filter(Survey.author_id != current_user.id,
                                             Survey.start_timestamp < datetime.utcnow(),
                                             Survey.end_timestamp > datetime.utcnow(),
                                             Survey.is_explore_public == True) \
                .order_by(Survey.timestamp.desc()) \
                .paginate(page, per_page)

            if survey_type == 'collected':
                user = User.query.get_or_404(current_user.id)
                pagination = Collect.query.with_parent(user).filter(current_user.id != Collect.collector_id) \
                    .order_by(Collect.timestamp.desc()).paginate(page, per_page)
            surveys = pagination.items
        except Exception as e:
            print(e)
            pagination = None
            surveys = None
    else:
        pagination = None
        surveys = None
    return render_template('main/explore.html', pagination=pagination, surveys=surveys)


@main_bp.route('/search/<string:search_type>')
@login_required
def search(search_type):
    q = request.args.get('q', '').strip()
    if q == '':
        flash('请输入调查相关信息，如标题关键字等.', 'warning')
        return redirect_back()

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['VANSWER_SEARCH_RESULT_PER_PAGE']

    if search_type == "index":
        pagination = Survey.query.filter(Survey.author_id == current_user.id).whooshee_search(q).paginate(page,
                                                                                                          per_page)
    else:
        pagination = Survey.query.filter(Survey.author_id != current_user.id,
                                         Survey.start_timestamp < datetime.utcnow(),
                                         Survey.end_timestamp > datetime.utcnow(),
                                         Survey.is_explore_public == True)\
            .whooshee_search(q).paginate(page, per_page)
    surveys = pagination.items
    return render_template('main/' + search_type + '.html', q=q, surveys=surveys, pagination=pagination)


@main_bp.route('/notifications')
@login_required
def show_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['VANSWER_NOTIFICATION_PER_PAGE']
    notifications = Notification.query.with_parent(current_user)
    filter_rule = request.args.get('filter')
    if filter_rule == 'unread':
        notifications = notifications.filter_by(is_read=False)

    pagination = notifications.order_by(Notification.timestamp.desc()).paginate(page, per_page)
    notifications = pagination.items
    return render_template('main/notifications.html', pagination=pagination, notifications=notifications)


@main_bp.route('/notification/read/<int:notification_id>', methods=['POST'])
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if current_user != notification.receiver:
        abort(403)

    notification.is_read = True
    db.session.commit()
    flash('通知已读！', 'success')
    return redirect(url_for('.show_notifications'))


@main_bp.route('/notifications/read/all', methods=['POST'])
@login_required
def read_all_notification():
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    flash('全部消息已读！', 'success')
    return redirect(url_for('.show_notifications'))


# @main_bp.route('/uploads/<path:filename>')
# def get_image(filename):
#     return send_from_directory(current_app.config['VANSWER_UPLOAD_PATH'], filename)


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


# @main_bp.route('/upload', methods=['GET', 'POST'])
# @login_required
# @confirm_required
# @permission_required('UPLOAD')
# def upload():
#     if request.method == 'POST' and 'file' in request.files:
#         f = request.files.get('file')
#         filename = rename_image(f.filename)
#         f.save(os.path.join(current_app.config['VANSWER_UPLOAD_PATH'], filename))
#         filename_s = resize_image(f, filename, current_app.config['VANSWER_PHOTO_SIZE']['small'])
#         filename_m = resize_image(f, filename, current_app.config['VANSWER_PHOTO_SIZE']['medium'])
#         photo = Photo(
#             filename=filename,
#             filename_s=filename_s,
#             filename_m=filename_m,
#             author=current_user._get_current_object()
#         )
#         db.session.add(photo)
#         db.session.commit()
#     return render_template('main/upload.html')


@main_bp.route('/survey')
@login_required
@confirm_required
def fill_in_survey():
    survey_id = request.args.get('survey_id')
    survey = Survey.query.get_or_404(survey_id)
    if not survey.is_published:
        flash('问卷未发布或已截止', 'warning')
        return redirect(url_for('.index'))
    return render_template('main/fillinsurvey.html', survey=survey)


@main_bp.route('/display_survey/<int:survey_id>')
def display(survey_id):
    # survey_id = request.args.get('id')
    survey = Survey.query.get_or_404(survey_id)
    return render_template('main/displaysurvey.html', survey=survey)


@main_bp.route('/change_survey_status/<int:survey_id>')
@login_required
@confirm_required
def change_survey_status(survey_id):
    action = request.args.get('action')
    survey = Survey.query.get_or_404(survey_id)
    if action == 'publish':
        survey.start_timestamp = datetime.utcnow()
        flash('问卷已发布', 'info')
    else:
        survey.start_timestamp = datetime(2099, 1, 1)
        flash('问卷已停止', 'info')
    survey.end_timestamp = datetime(2099, 1, 1)
    db.session.commit()
    return redirect(url_for('.index'))


@main_bp.route('/new_survey')
@login_required
@confirm_required
@permission_required('UPLOAD')
def new_survey():
    time = datetime.utcnow()
    title = '问卷' + str(current_user.id) + get_time_str(time)
    # user = User.query.get_or_404(current_user.id)
    survey = Survey(
        timestamp=time,
        title=title,
        author=current_user._get_current_object()
    )
    db.session.add(survey)
    # current_user.surveys.append(survey)
    db.session.commit()
    return render_template('main/editsurvey.html', survey=survey)


@main_bp.route('/save_survey', methods=['POST'])
@login_required
@confirm_required
def save_survey():
    json_data = json.loads(request.get_data().decode("utf-8"))
    survey_id = json_data['surveyId']
    survey_text = json_data["surveyText"]

    survey = Survey.query.get_or_404(survey_id)
    if survey.is_published:
        flash('问卷发布中，不能修改', 'warning')
        return redirect(url_for('.index'))
    survey.content = survey_text
    survey.timestamp = datetime.utcnow()
    survey.questions.clear()
    db.session.commit()

    order = json.loads(survey_text, object_pairs_hook=OrderedDict)
    survey.title = order['title']

    for item in order['pages']:
        for element in item['elements']:
            name = element['name']
            question_type = get_question_type(element['type'])
            # rate_max = element['rateMax']
            question = SurveyQuestion(
                name=name,
                type=question_type
            )
            # db.session.add(question)
            survey.questions.append(question)

            if question_type != 'rating':
                choices = element['choices']
                for choice in choices:
                    option = QuestionOption(choice_text=choice)
                    # db.session.add(option)
                    question.options.append(option)
            # else:
            #     for i in range(rate_max)

    db.session.commit()
    return 'success'


@main_bp.route('/send_survey/<int:survey_id>')
@login_required
@confirm_required
def send_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if not survey.is_published:
        flash('问卷未发布或已截止', 'warning')
        return redirect(url_for('.index'))
    return render_template('main/sendsurvey.html', survey_id=survey_id)


@main_bp.route('/save_result', methods=['POST'])
@login_required
@confirm_required
def save_result():
    survey_id = request.args.get('id')
    order = json.loads(request.get_data().decode("utf-8"), object_pairs_hook=OrderedDict)
    survey = Survey.query.get_or_404(survey_id)
    if not survey.is_published:
        flash('问卷未发布或已截止', 'warning')
        return redirect(url_for('.index'))
    current_user.participate(survey)
    for k, v in order.items():
        question = SurveyQuestion.query.with_parent(survey).filter(SurveyQuestion.name == k).first()
        if isinstance(v, str):
            v = v.split(' ')
        try:
            for choice in v:
                option = QuestionOption.query.with_parent(question).filter(QuestionOption.choice_text == choice).first()
                option.poll += 1
        except Exception as e:
            print(e)
            option = QuestionOption.query.with_parent(question).filter(QuestionOption.choice_value == v).first()
            if option is None:
                option = QuestionOption(choice_value=v)
                question.options.append(option)
                db.session.commit()
            option.poll += 1
    db.session.commit()
    # option = QuestionOption.query.all()
    return 'success'


@main_bp.route('/edit_survey/<int:survey_id>')
@login_required
@confirm_required
def edit_survey(survey_id):
    # id = request.args.get('id')
    survey = Survey.query.get_or_404(survey_id)
    if survey.is_published:
        flash('问卷发布中, 不能修改 ', 'warning')
        return redirect(url_for('.index'))
    return render_template('main/editsurvey.html', survey=survey)


@main_bp.route('/survey_content')
def survey_content():
    survey_id = request.args.get('id')
    survey = Survey.query.get_or_404(survey_id)
    return jsonify(survey.content)


@main_bp.route('/set_survey/<int:survey_id>', methods=['GET', 'POST'])
@login_required
@confirm_required
def set_survey(survey_id):
    form = SurveyForm()
    survey = Survey.query.get_or_404(survey_id)
    if survey.is_published:
        flash('问卷发布中, 不能更改设置 ', 'warning')
        return redirect(url_for('.index'))
    if form.validate_on_submit():
        survey.reward = form.reward.data
        if survey.reward != 0 and (current_user.Ethereum_id is None or current_user.Ethereum_password is None):
            flash('以太账户设置错误', 'warning')
            return redirect(url_for('user.user.change_ethereum'))
        survey.title = form.surveytitle.data

        order = json.loads(survey.content, object_pairs_hook=OrderedDict)
        order['title'] = survey.title
        survey.content = json.dumps(order)

        survey.upper_limit_number = form.surveynumber.data
        survey.is_explore_public = form.ispublic.data
        try:
            survey.start_timestamp = datetime.strptime(form.starttime.data, "%Y-%m-%d %H:%M")
        except Exception as e:
            print(e)
        try:
            survey.end_timestamp = datetime.strptime(form.endtime.data, "%Y-%m-%d %H:%M")
        except Exception as e:
            print(e)
        db.session.commit()
        flash("修改成功！")

    form.ispublic.data = survey.is_explore_public
    form.reward.data = survey.reward
    form.surveytitle.data = survey.title
    form.surveynumber.data = survey.upper_limit_number
    form.starttime.data = survey.start_timestamp.strftime("%Y-%m-%d %H:%M")
    form.endtime.data = survey.end_timestamp.strftime("%Y-%m-%d %H:%M")

    return render_template('main/setsurvey.html', form=form)


@main_bp.route('/analyse_survey/<int:survey_id>')
@login_required
@confirm_required
def analyse_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.is_published:
        flash('问卷发布中, 不能分析 ', 'warning')
        return redirect(url_for('.index'))
    return render_template('main/analysesurvey.html', survey=survey)


@main_bp.route('/question_result/<int:question_id>')
@login_required
@confirm_required
def question_result(question_id):
    question = SurveyQuestion.query.get_or_404(question_id)
    # a = question.survey.participants
    participants = len(question.survey.participants)
    ans = list()
    for option in question.options:
        option_name = option.choice_text
        if option_name is None:
            option_name = option.choice_value
        poll = option.poll
        percentage = str(100 * poll / participants) + '%'
        ans.append({'option_name': option_name, 'poll': poll, 'percentage': percentage})
    return jsonify(ans)


@main_bp.route('/delete/survey/<int:survey_id>', methods=['GET', 'POST'])
@login_required
def delete_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if current_user != survey.author and not current_user.can('MODERATE'):
        abort(403)

    db.session.delete(survey)
    db.session.commit()
    flash('问卷已删除', 'info')

    return redirect(url_for('.index'))


@main_bp.route('/report/survey/<int:survey_id>', methods=['POST'])
@login_required
@confirm_required
def report_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    survey.flag += 1
    db.session.commit()
    flash('问卷已举报.', 'success')
    return redirect_back()


# @main_bp.route('/photo/<int:photo_id>')
# def show_photo(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     page = request.args.get('page', 1, type=int)
#     per_page = current_app.config['VANSWER_COMMENT_PER_PAGE']
#     pagination = Comment.query.with_parent(photo).order_by(Comment.timestamp.asc()).paginate(page, per_page)
#     comments = pagination.items
#
#     comment_form = CommentForm()
#     description_form = DescriptionForm()
#     tag_form = TagForm()
#
#     description_form.description.data = photo.description
#     return render_template('main/photo.html', photo=photo, comment_form=comment_form,
#                            description_form=description_form, tag_form=tag_form,
#                            pagination=pagination, comments=comments)


# @main_bp.route('/photo/n/<int:photo_id>')
# def photo_next(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     photo_n = Photo.query.with_parent(photo.author).filter(Photo.id < photo_id).order_by(Photo.id.desc()).first()
#
#     if photo_n is None:
#         flash('This is already the last one.', 'info')
#         return redirect(url_for('.show_photo', photo_id=photo_id))
#     return redirect(url_for('.show_photo', photo_id=photo_n.id))
#
#
# @main_bp.route('/photo/p/<int:photo_id>')
# def photo_previous(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     photo_p = Photo.query.with_parent(photo.author).filter(Photo.id > photo_id).order_by(Photo.id.asc()).first()
#
#     if photo_p is None:
#         flash('This is already the first one.', 'info')
#         return redirect(url_for('.show_photo', photo_id=photo_id))
#     return redirect(url_for('.show_photo', photo_id=photo_p.id))


@main_bp.route('/collect/<int:survey_id>', methods=['POST'])
@login_required
@confirm_required
@permission_required('COLLECT')
def collect(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if current_user.is_collecting(survey):
        flash('Already collected.', 'info')
        return redirect_back()

    current_user.collect(survey)
    flash('问卷已收藏.', 'success')
    # if current_user != survey.author and survey.author.receive_collect_notification:
    #     push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
    # return redirect(url_for('.show_survey', survey_id=survey_id))


@main_bp.route('/uncollect/<int:survey_id>', methods=['POST'])
@login_required
def uncollect(survey_id):
    photo = Survey.query.get_or_404(survey_id)
    if not current_user.is_collecting(photo):
        flash('Not collect yet.', 'info')
        return redirect_back()

    current_user.uncollect(photo)
    flash('取消收藏.', 'info')
    return redirect_back()

# @main_bp.route('/report/comment/<int:comment_id>', methods=['POST'])
# @login_required
# @confirm_required
# def report_comment(comment_id):
#     comment = Comment.query.get_or_404(comment_id)
#     comment.flag += 1
#     db.session.commit()
#     flash('Comment reported.', 'success')
#     return redirect(url_for('.show_photo', photo_id=comment.photo_id))


# @main_bp.route('/photo/<int:photo_id>/collectors')
# def show_collectors(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     page = request.args.get('page', 1, type=int)
#     per_page = current_app.config['VANSWER_USER_PER_PAGE']
#     pagination = Collect.query.with_parent(photo).order_by(Collect.timestamp.asc()).paginate(page, per_page)
#     collects = pagination.items
#     return render_template('main/collectors.html', collects=collects, photo=photo, pagination=pagination)


# @main_bp.route('/photo/<int:photo_id>/description', methods=['POST'])
# @login_required
# def edit_description(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     if current_user != photo.author and not current_user.can('MODERATE'):
#         abort(403)
#
#     form = DescriptionForm()
#     if form.validate_on_submit():
#         photo.description = form.description.data
#         db.session.commit()
#         flash('Description updated.', 'success')
#
#     flash_errors(form)
#     return redirect(url_for('.show_photo', photo_id=photo_id))


# @main_bp.route('/photo/<int:photo_id>/comment/new', methods=['POST'])
# @login_required
# @permission_required('COMMENT')
# def new_comment(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     page = request.args.get('page', 1, type=int)
#     form = CommentForm()
#     if form.validate_on_submit():
#         body = form.body.data
#         author = current_user._get_current_object()
#         comment = Comment(body=body, author=author, photo=photo)
#
#         replied_id = request.args.get('reply')
#         if replied_id:
#             comment.replied = Comment.query.get_or_404(replied_id)
#             if comment.replied.author.receive_comment_notification:
#                 push_comment_notification(photo_id=photo.id, receiver=comment.replied.author)
#         db.session.add(comment)
#         db.session.commit()
#         flash('Comment published.', 'success')
#
#         if current_user != photo.author and photo.author.receive_comment_notification:
#             push_comment_notification(photo_id, receiver=photo.author, page=page)
#
#     flash_errors(form)
#     return redirect(url_for('.show_photo', photo_id=photo_id, page=page))


# @main_bp.route('/photo/<int:photo_id>/tag/new', methods=['POST'])
# @login_required
# def new_tag(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     if current_user != photo.author and not current_user.can('MODERATE'):
#         abort(403)
#
#     form = TagForm()
#     if form.validate_on_submit():
#         for name in form.tag.data.split():
#             tag = Tag.query.filter_by(name=name).first()
#             if tag is None:
#                 tag = Tag(name=name)
#                 db.session.add(tag)
#                 db.session.commit()
#             if tag not in photo.tags:
#                 photo.tags.append(tag)
#                 db.session.commit()
#         flash('Tag added.', 'success')
#
#     flash_errors(form)
#     return redirect(url_for('.show_photo', photo_id=photo_id))


# @main_bp.route('/set-comment/<int:photo_id>', methods=['POST'])
# @login_required
# def set_comment(photo_id):
#     photo = Photo.query.get_or_404(photo_id)
#     if current_user != photo.author:
#         abort(403)
#
#     if photo.can_comment:
#         photo.can_comment = False
#         flash('Comment disabled', 'info')
#     else:
#         photo.can_comment = True
#         flash('Comment enabled.', 'info')
#     db.session.commit()
#     return redirect(url_for('.show_photo', photo_id=photo_id))


# @main_bp.route('/reply/comment/<int:comment_id>')
# @login_required
# @permission_required('COMMENT')
# def reply_comment(comment_id):
#     comment = Comment.query.get_or_404(comment_id)
#     return redirect(
#         url_for('.show_photo', photo_id=comment.photo_id, reply=comment_id,
#                 author=comment.author.name) + '#comment-form')


# @main_bp.route('/delete/comment/<int:comment_id>', methods=['POST'])
# @login_required
# def delete_comment(comment_id):
#     comment = Comment.query.get_or_404(comment_id)
#     if current_user != comment.author and current_user != comment.photo.author \
#             and not current_user.can('MODERATE'):
#         abort(403)
#     db.session.delete(comment)
#     db.session.commit()
#     flash('Comment deleted.', 'info')
#     return redirect(url_for('.show_photo', photo_id=comment.photo_id))


# @main_bp.route('/tag/<int:tag_id>', defaults={'order': 'by_time'})
# @main_bp.route('/tag/<int:tag_id>/<order>')
# def show_tag(tag_id, order):
#     tag = Tag.query.get_or_404(tag_id)
#     page = request.args.get('page', 1, type=int)
#     per_page = current_app.config['VANSWER_PHOTO_PER_PAGE']
#     order_rule = 'time'
#     pagination = Photo.query.with_parent(tag).order_by(Photo.timestamp.desc()).paginate(page, per_page)
#     photos = pagination.items
#
#     if order == 'by_collects':
#         photos.sort(key=lambda x: len(x.collectors), reverse=True)
#         order_rule = 'collects'
#     return render_template('main/tag.html', tag=tag, pagination=pagination, photos=photos, order_rule=order_rule)


# @main_bp.route('/delete/tag/<int:photo_id>/<int:tag_id>', methods=['POST'])
# @login_required
# def delete_tag(photo_id, tag_id):
#     tag = Tag.query.get_or_404(tag_id)
#     photo = Photo.query.get_or_404(photo_id)
#     if current_user != photo.author and not current_user.can('MODERATE'):
#         abort(403)
#     photo.tags.remove(tag)
#     db.session.commit()
#
#     if not tag.photos:
#         db.session.delete(tag)
#         db.session.commit()
#
#     flash('Tag deleted.', 'info')
#     return redirect(url_for('.show_photo', photo_id=photo_id))
