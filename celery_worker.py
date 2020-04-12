"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
import json
from celery import Celery
from flask import Flask, current_app
from flask_web3 import current_web3
from vanswer.extensions import db, CustomFlaskWeb3
from vanswer.models import Notification, Survey, User
from vanswer.settings import config

celery = Celery(
        __name__,
        backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )


def create_app(config_name):
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask(__name__)

    app.config.from_object(config[config_name])
    app.config.update({'ETHEREUM_PROVIDER': os.getenv('ETHEREUM_PROVIDER', 'http'),
                       'ETHEREUM_ENDPOINT_URI': os.getenv('ETHEREUM_ENDPOINT_URI', 'http://localhost:8545'),
                       'ETHEREUM_OPTS': {'timeout': 60},
                       'ETHEREUM_IPC_PATH': os.getenv('ETHEREUM_IPC_PATH', None),
                       'CELERY_BROKER_URL': os.getenv('CELERY_BROKER_URL'),
                       'CELERY_RESULT_BACKEND': os.getenv('CELERY_RESULT_BACKEND')})
    web3 = CustomFlaskWeb3(app=app)
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask


@celery.task
def save_result_web3(user_id, survey_id, survey_hash, answer_hash):
    user = User.query.get_or_404(user_id)
    survey = Survey.query.get_or_404(survey_id)
    try:
        current_web3.publish_answer(user.Ethereum_account, user.Ethereum_password,
                                    survey.geth_address, json.loads(survey.geth_abi),
                                    survey_hash, answer_hash)
        user.account_balance = current_web3.eth.getBalance(user.Ethereum_account) / 1000000000000000000
        notification = Notification(message='Succeed in saving answer to ethereum', receiver=user)
        db.session.add(notification)
    except Exception as e:
        current_app.logger.error(e)
        notification = Notification(message='Failed to save answer to ethereum', receiver=user)
        db.session.add(notification)
    db.session.commit()


@celery.task
def publish_survey_web3(user_id, survey_id):
    user = User.query.get_or_404(user_id)
    survey = Survey.query.get_or_404(survey_id)
    try:
        survey.geth_address, geth_abi = current_web3.publish_survey(user.Ethereum_account,
                                                                    user.Ethereum_password,
                                                                    survey.id, survey.survey_ipfs,
                                                                    survey.upper_limit_number, survey.reward)
        survey.geth_abi = json.dumps(geth_abi)
        user.account_balance = current_web3.eth.getBalance(user.Ethereum_account) / 1000000000000000000
        notification = Notification(message='Succeed in publishing survey to ethereum', receiver=user)
        db.session.add(notification)
    except Exception as e:
        current_app.logger.error(e)
        notification = Notification(message='Failed to publish survey to ethereum', receiver=user)
        db.session.add(notification)
    db.session.commit()


@celery.task
def end_survey_web3(user_id, survey_id):
    user = User.query.get_or_404(user_id)
    survey = Survey.query.get_or_404(survey_id)
    try:
        current_web3.end_survey(user.Ethereum_account, user.Ethereum_password,
                                survey.geth_address, json.loads(survey.geth_abi))
        user.account_balance = current_web3.eth.getBalance(user.Ethereum_account) / 1000000000000000000
        notification = Notification(message='Succeeding in ending survey in ethereum', receiver=user)
        db.session.add(notification)
    except Exception as e:
        current_app.logger.error(e)
        notification = Notification(message='Failed to end survey in ethereum', receiver=user)
        db.session.add(notification)
    db.session.commit()
