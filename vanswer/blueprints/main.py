# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import json
import importlib
from collections import OrderedDict
from datetime import datetime
from flask import render_template, flash, redirect, url_for, current_app, \
    send_from_directory, request, abort, Blueprint, jsonify
from flask_login import login_required, current_user
from flask_web3 import current_web3

from vanswer.decorators import confirm_required, permission_required
from vanswer.extensions import db, CustomIpfs, publish_survey_web3, end_survey_web3, save_result_web3
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
                                         Survey.is_explore_public is True) \
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


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


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
        task = publish_survey_web3.delay(survey_id)
        current_app.logger.info('publish survey ' + str(survey.id) + ' ' 
                                'task.id: ' + str(task.id))
        # survey.geth_address, geth_abi = current_web3.publish_survey(current_user.Ethereum_account,
        #                                                             current_user.Ethereum_password,
        #                                                             survey.id, survey.survey_ipfs,
        #                                                             survey.upper_limit_number, survey.reward)
        # survey.geth_abi = str(geth_abi)
        flash('问卷已发布', 'info')
    else:
        survey.start_timestamp = datetime(2099, 1, 1)
        task = end_survey_web3.delay(survey_id)
        current_app.logger.info('end survey ' + str(survey.id) + ' ' 
                                'task.id: ' + str(task.id))

        # current_web3.end_survey(current_user.Ethereum_account, current_user.Ethereum_password,
        #                         survey.geth_address, json.loads(survey.geth_abi))
        flash('问卷已停止，重新发布会清除原有数据', 'info')
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
    survey.survey_ipfs = CustomIpfs.save_survey(survey_id, data={'data': survey_text})
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
    answer = request.get_data().decode("utf-8")
    order = json.loads(answer, object_pairs_hook=OrderedDict)

    survey_hash, answer_hash = CustomIpfs.save_answer(current_user.id, {'survey_id': survey_id, 'data': answer})
    survey = Survey.query.get_or_404(survey_id)

    if not survey.is_published:
        flash('问卷未发布或已截止', 'warning')
        return redirect(url_for('.index'))

    # user_answer = UserAnswer(users=current_user, surveys=survey, answer_ipfs=answer_hash, answer_text=answer)
    # db.session.add(user_answer)

    if not current_user.participate(survey, answer_hash, answer):
        flash('已参加过该调查', 'warning')
        return redirect(url_for('.index'))

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

    task = save_result_web3.delay(survey_id, survey_hash, answer_hash)
    current_app.logger.info('publish answer' +
                            'survey_id: ' + str(survey.id) + ' ' +
                            'user_id: ' + str(current_user.id) + ' ' +
                            'task.id: ' + str(task.id))
    # current_web3.publish_answer(current_user.Ethereum_account, current_user.Ethereum_password,
    #                             survey.geth_address, json.loads(survey.geth_abi),
    #                             survey_hash, answer_hash)
    # user = User.query.get_or_404(current_user.id)
    # user.account_balance = current_web3.eth.getBalance(user.Ethereum_account) / 1000000000000000000
    # db.session.commmit()

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
        survey.reward = form.reward.data * 1000000000000000000
        survey.upper_limit_number = form.surveynumber.data
        if survey.reward != 0 and (current_user.Ethereum_account is None or current_user.Ethereum_password is None):
            flash('以太账户设置错误', 'warning')
            return redirect(url_for('user.change_ethereum'))
        if survey.reward * survey.upper_limit_number > survey.account_balance:
            flash('账户余额不足', 'warning')
            return redirect(url_for('.index'))
        survey.title = form.surveytitle.data

        order = json.loads(survey.content, object_pairs_hook=OrderedDict)
        order['title'] = survey.title
        survey.content = json.dumps(order)

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
    form.reward.data = survey.reward / 1000000000000000000
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


@main_bp.route('/task_status/', )
def task_status():
    task_name = request.args.get('name')
    task_id = request.args.get('id')

    imp_module = importlib.import_module(__name__)
    task = getattr(imp_module, task_name).AsyncResult(task_id)

    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)
