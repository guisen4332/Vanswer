# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
import sys

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'


class Operations:
    CONFIRM = 'confirm'
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'


class BaseConfig:
    VANSWER_ADMIN_EMAIL = os.getenv('VANSWER_ADMIN', 'admin@helloflask.com')
    VANSWER_SURVEY_PER_PAGE = 12
    VANSWER_NOTIFICATION_PER_PAGE = 20
    VANSWER_USER_PER_PAGE = 20
    VANSWER_MANAGE_SURVEY_PER_PAGE = 20
    VANSWER_MANAGE_USER_PER_PAGE = 30
    VANSWER_SEARCH_RESULT_PER_PAGE = 20
    VANSWER_MAIL_SUBJECT_PREFIX = '[Vanswer]'
    VANSWER_PHOTO_SIZE = {'small': 400,
                         'medium': 800}
    VANSWER_PHOTO_SUFFIX = {
        VANSWER_PHOTO_SIZE['small']: '_s',  # thumbnail
        VANSWER_PHOTO_SIZE['medium']: '_m',  # display
    }

    ROOT_GETH_ACCOUNT = os.getenv('ROOT_GETH_ACCOUNT')
    ROOT_GETH_PASSWORD = os.getenv('ROOT_GETH_PASSWORD')
    USER_GETH_PASSWORD = os.getenv('USER_GETH_PASSWORD')

    VHUB_HOST = os.getenv('VHUB_HOST')

    SECRET_KEY = os.getenv('SECRET_KEY', 'secret string')
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # file size exceed to 3 Mb will return a 413 error response.

    BOOTSTRAP_SERVE_LOCAL = True

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AVATARS_SAVE_PATH = os.path.join(basedir, 'avatars')
    AVATARS_SIZE_TUPLE = (30, 100, 200)

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    # MAIL_PORT = os.getenv('MAIL_PORT', 465)
    # MAIL_USE_SSL = True
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'robot@vanswer.com'


    DROPZONE_ALLOWED_FILE_TYPE = 'image'
    DROPZONE_MAX_FILE_SIZE = 3
    DROPZONE_MAX_FILES = 30
    DROPZONE_ENABLE_CSRF = True

    WHOOSHEE_MIN_STRING_LEN = 1


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = \
        prefix + os.path.join(basedir, 'data-dev.db')
    REDIS_URL = "redis://localhost"


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'  # in-memory database


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL',
                                        prefix + os.path.join(basedir, 'data.db'))


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
