"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from flask import Flask, current_app
from vanswer.extensions import db, CustomFlaskWeb3, celery
from vanswer.settings import config


def create_app(config_name=None):

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
    return app


app = create_app()
