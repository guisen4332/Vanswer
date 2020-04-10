# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import json
import os
import random

from faker import Faker
from datetime import timedelta
from flask import current_app
from flask_web3 import current_web3
from sqlalchemy.exc import IntegrityError

from vanswer.extensions import db, CustomIpfs
from vanswer.models import User, Notification, Survey, QuestionOption, SurveyQuestion

fake = Faker('zh_CN')


def fake_admin():
    admin = User(username='admin',
                 email='admin@vanswer.com',
                 confirmed=True,
                 Ethereum_account=current_web3.toChecksumAddress(current_app.config['ROOT_GETH_ACCOUNT']),
                 Ethereum_password=current_app.config['ROOT_GETH_PASSWORD'],
                 account_balance=current_web3.eth.getBalance(current_web3.toChecksumAddress(
                     current_app.config['ROOT_GETH_ACCOUNT'])))
    admin.set_password('12345678')
    notification = Notification(message='Hello, welcome to Vanswer.', receiver=admin)
    db.session.add(notification)
    db.session.add(admin)
    db.session.commit()


def fake_user(count=10):
    for i in range(count):
        account = current_web3.create_account(current_app.config['USER_GETH_PASSWORD'],
                                              current_web3.toWei(current_app.config['USER_GETH_BALANCE'], 'ether'))
        user = User(confirmed=True,
                    username=fake.user_name(),
                    member_since=fake.date_this_decade(),
                    email=fake.email(),
                    Ethereum_account=account,
                    Ethereum_password=current_app.config['USER_GETH_PASSWORD'],
                    account_balance=current_web3.eth.getBalance(account))
        user.set_password('123456')
        db.session.add(user)
        print('add user')
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def fake_follow(count=30):
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.follow(User.query.get(random.randint(1, User.query.count())))
    db.session.commit()


def fake_survey(survey_count=20):
    # survey
    question_count = 4 * survey_count
    rating_question_num = survey_count
    option_count = 15 * survey_count
    rating_option_num = 3 * survey_count
    for i in range(survey_count):
        start_timestamp = fake.date_time_this_month(before_now=True, after_now=False, tzinfo=None)
        end_timestamp = fake.date_time_this_year(before_now=False, after_now=True, tzinfo=None)
        survey = Survey(
            author=User.query.get(random.randint(1, User.query.count())),
            title=fake.sentence(),
            is_explore_public=True,
            reward=fake.random_digit(),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            timestamp=fake.date_time_between_dates(datetime_start=start_timestamp - timedelta(days=fake.random_digit(),
                                                                                              hours=fake.random_digit()),
                                                   datetime_end=start_timestamp,
                                                   tzinfo=None)
        )
        db.session.add(survey)
    db.session.commit()

    # question
    for i in range(question_count - rating_question_num):
        question = SurveyQuestion(
            name=fake.sentence(),
            type=fake.random_element(elements=('radiogroup', 'dropdown', 'checkbox')),
            survey=Survey.query.get(random.randint(1, Survey.query.count()))
        )
        db.session.add(question)
    for i in range(rating_question_num):
        question = SurveyQuestion(
            name=fake.sentence(),
            type='rating',
            survey=Survey.query.get(random.randint(1, Survey.query.count()))
        )
        db.session.add(question)
    db.session.commit()

    # option
    for i in range(option_count - rating_option_num):
        option = QuestionOption(choice_text=fake.sentence()
                                # question=SurveyQuestion.query.filter(SurveyQuestion.type != 'rating')
                                # .limit(1).offset(random.randint(0, option_count-rating_question_num-1)).first()
                                )
        db.session.add(option)
    # for i in range(rating_option_num):
    #     option = QuestionOption(choice_value=fake.random_digit(),
    #                             qustion=SurveyQuestion.query.filter(SurveyQuestion.type == 'rating')
    #                             .get(random.randint(1, rating_question_num))
    #                             )
    #     db.session.add(option)
    db.session.commit()

    questions = SurveyQuestion.query.filter(SurveyQuestion.type != 'rating').all()
    for question in questions:
        for i in range(random.randint(2, 5)):
            question.options.append(QuestionOption.query.filter(QuestionOption.question == None).first())
    db.session.commit()

    surveys = Survey.query.all()
    for survey in surveys:
        elements = list()
        questions = SurveyQuestion.query.with_parent(survey).all()
        for question in questions:
            element = {'type': question.type,
                       'name': question.name
                       }
            if question.type != 'rating':
                choices = QuestionOption.query.with_parent(question).all()
                element.update({'choices': list([choice.choice_text for choice in choices])})
            else:
                element.update({'rateMax': fake.random_digit()})
            elements.append(element)
        pages = {'name': 'page1', 'elements': elements}
        content = {'title': survey.title, 'pages': [pages]}
        survey.content = json.dumps(content)
        survey.survey_ipfs = CustomIpfs.save_survey(survey.id, {'data': json.dumps(content)})
        survey.geth_address, geth_abi = current_web3.publish_survey(
            survey.author.Ethereum_account,
            survey.author.Ethereum_password,
            id=str(survey.id), ipfs=survey.survey_ipfs,
            limit=5, reward=1)
        # geth_abi is a list
        survey.geth_abi = json.dumps(geth_abi)
        print('add survey')
    db.session.commit()


# def fake_question(question_count=80, rating_question_num=20):
#     for i in range(question_count-rating_question_num):
#         question = QuestionOption(
#             name=fake.sentence(),
#             type=fake.random_element(elements=('one choice', 'multiple choice')),
#             survey=Survey.query.get(random.randint(1, Survey.query.count()))
#         )
#         db.session.add(question)
#     for i in range(rating_question_num):
#         question = QuestionOption(
#             name=fake.sentence(),
#             type='rating'
#         )
#         db.session.add(question)
#     db.session.commit()


# def fake_option(option_count=120, rating_option_num=30):
#     for i in range(option_count-rating_option_num):
#         option = QuestionOption(choice_text=fake.sentence(),
#                                 qustion=SurveyQuestion.query.filter(SurveyQuestion.type != 'rating')
#                                 .get(random.randint(1, questino_count-rating_question_num))
#                                 )
#         db.session.add(option)
#     for i in range(rating_option_num):
#         option = QuestionOption(choice_value=fake.random_digit(),
#                                 qustion=SurveyQuestion.query.filter(SurveyQuestion.type == 'rating')
#                                 .get(random.randint(1, rating_question_num))
#                                 )
#         db.session.add(option)
#     db.session.commit()


# def fake_tag(count=20):
#     for i in range(count):
#         tag = Tag(name=fake.word())
#         db.session.add(tag)
#         try:
#             db.session.commit()
#         except IntegrityError:
#             db.session.rollback()


def fake_collect(count=50):
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.collect(Survey.query.get(random.randint(1, Survey.query.count())))
    db.session.commit()


# def fake_comment(count=100):
#     for i in range(count):
#         comment = Comment(
#             author=User.query.get(random.randint(1, User.query.count())),
#             body=fake.sentence(),
#             timestamp=fake.date_time_this_year(),
#             photo=Photo.query.get(random.randint(1, Photo.query.count()))
#         )
#         db.session.add(comment)
#     db.session.commit()
