# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os

import click
import logging
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from logging.handlers import RotatingFileHandler

from vanswer.blueprints.admin import admin_bp
from vanswer.blueprints.ajax import ajax_bp
from vanswer.blueprints.auth import auth_bp
from vanswer.blueprints.main import main_bp
from vanswer.blueprints.user import user_bp
from vanswer.extensions import bootstrap, db, login_manager, mail,\
    moment, whooshee, avatars, csrf, CustomFlaskWeb3, celery
from vanswer.models import Role, User, Notification, Collect,\
    Permission, Survey, SurveyQuestion, QuestionOption, UserAnswer
from vanswer.settings import config


def create_app(config_name=None):
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

    register_extensions(app)
    register_logger(app)
    register_blueprints(app)
    register_commands(app)
    register_errorhandlers(app)
    register_shell_context(app)
    register_template_context(app)
    return app


def register_extensions(app):
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    # dropzone.init_app(app)
    moment.init_app(app)
    whooshee.init_app(app)
    avatars.init_app(app)
    csrf.init_app(app)


def register_logger(app):
    p, f = os.path.split(os.getenv('LOG_PATH'))
    if not os.path.isdir(p):  # 无文件夹时创建
        os.makedirs(p)
    if not os.path.isfile(f):  # 无文件时创建
        fd = open(f, mode="w", encoding="utf-8")
        fd.close()
    app.logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler(os.getenv('LOG_PATH'), maxBytes=10 * 1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    if not app.debug:
        app.logger.addHandler(file_handler)


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(ajax_bp, url_prefix='/ajax')


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, User=User, Survey=Survey, SurveyQuestion=SurveyQuestion,
                    UserAnswer=UserAnswer, QuestionOption=QuestionOption, Collect=Collect,
                    Notification=Notification)


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        if current_user.is_authenticated:
            notification_count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
        else:
            notification_count = None
        return dict(notification_count=notification_count)


def register_errorhandlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 500


def register_commands(app):
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """Initialize the database."""
        if drop:
            click.confirm('This operation will delete the database, do you want to continue?', abort=True)
            db.drop_all()
            click.echo('Drop tables.')
        db.create_all()
        click.echo('Initialized database.')

    @app.cli.command()
    def init():
        """Initialize Vanswer."""
        click.echo('Initializing the database...')
        db.create_all()

        click.echo('Initializing the roles and permissions...')
        Role.init_role()

        click.echo('Done.')

    @app.cli.command()
    @click.option('--user', default=10, help='Quantity of users, default is 10.')
    @click.option('--survey_count', default=30, help='Quantity of photos, default is 30.')
    @click.option('--collect', default=50, help='Quantity of collects, default is 50.')
    def forge(user, survey_count, collect):
        """Generate fake data."""

        from vanswer.fakes import fake_admin, fake_follow, fake_user, fake_collect, fake_survey

        db.drop_all()
        db.create_all()

        click.echo('Initializing the roles and permissions...')
        Role.init_role()
        click.echo('Generating the administrator...')
        fake_admin()
        click.echo('Generating %d users...' % user)
        fake_user(user)
        # click.echo('Generating %d follows...' % follow)
        # fake_follow(follow)
        # click.echo('Generating %d tags...' % tag)
        # fake_tag(tag)
        click.echo('Generating %d surveys...' % survey_count)
        fake_survey(survey_count)
        click.echo('Generating %d collects...' % survey_count)
        fake_collect(collect)
        # click.echo('Generating %d comments...' % comment)
        # fake_comment(comment)
        # click.echo('Done.')
