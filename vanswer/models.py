# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
from datetime import datetime

from flask import current_app
from flask_avatars import Identicon
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from vanswer.extensions import db, whooshee

# relationship table
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
                             )


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    users = db.relationship('User', back_populates='role')
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')

    @staticmethod
    def init_role():
        roles_permissions_map = {
            'Locked': ['COLLECT'],
            'User': ['COLLECT', 'UPLOAD'],
            'Moderator': ['COLLECT', 'UPLOAD', 'MODERATE'],
            'Administrator': ['COLLECT', 'UPLOAD', 'MODERATE', 'ADMINISTER']
        }

        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


# relationship object
class Collect(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('survey.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    collector = db.relationship('User', back_populates='collections', lazy='joined')
    collected = db.relationship('Survey', back_populates='collectors', lazy='joined')


class UserAnswer(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), primary_key=True)
    answer_text = db.Column(db.Text)
    users = db.relationship('User', back_populates='surveys_participated', lazy='joined')
    surveys = db.relationship('Survey', back_populates='participants', lazy='joined')


@whooshee.register_model('username')
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, index=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    Ethereum_id = db.Column(db.Integer, index=True)
    Ethereum_password = db.Column(db.String(128))
    account_balance = db.Column(db.Float)
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64))

    confirmed = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    # public_collections = db.Column(db.Boolean, default=True)
    # receive_comment_notification = db.Column(db.Boolean, default=True)
    receive_collect_notification = db.Column(db.Boolean, default=True)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))

    role = db.relationship('Role', back_populates='users')
    surveys = db.relationship('Survey', back_populates='author', cascade='all')
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    surveys_participated = db.relationship('UserAnswer', back_populates='users', cascade='all')
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        # self.follow(self)  # follow self
        self.set_role()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_role(self):
        if self.role is None:
            if self.email == current_app.config['VANSWER_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    # def follow(self, user):
    #     if not self.is_following(user):
    #         follow = Follow(follower=self, followed=user)
    #         db.session.add(follow)
    #         db.session.commit()
    #
    # def unfollow(self, user):
    #     follow = self.following.filter_by(followed_id=user.id).first()
    #     if follow:
    #         db.session.delete(follow)
    #         db.session.commit()
    #
    # def is_following(self, user):
    #     if user.id is None:  # when follow self, user.id will be None
    #         return False
    #     return self.following.filter_by(followed_id=user.id).first() is not None
    #
    # def is_followed_by(self, user):
    #     return self.followers.filter_by(follower_id=user.id).first() is not None

    # @property
    # def followed_photos(self):
    #     return Photo.query.join(Follow, Follow.followed_id == Photo.author_id).filter(Follow.follower_id == self.id)

    def is_participant(self, survey):
        return UserAnswer.query.with_parent(self).filter_by(survey_id=survey.id).first() is not None

    def participate(self, survey):
        if not self.is_participant(survey):
            user_answer = UserAnswer(users=self, surveys=survey)
            db.session.add(user_answer)
            db.session.commit()

    def collect(self, photo):
        if not self.is_collecting(photo):
            collect = Collect(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()

    def uncollect(self, photo):
        collect = Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting(self, photo):
        return Collect.query.with_parent(self).filter_by(collected_id=photo.id).first() is not None

    def lock(self):
        self.locked = True
        self.role = Role.query.filter_by(name='Locked').first()
        db.session.commit()

    def unlock(self):
        self.locked = False
        self.role = Role.query.filter_by(name='User').first()
        db.session.commit()

    def block(self):
        self.active = False
        db.session.commit()

    def unblock(self):
        self.active = True
        db.session.commit()

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()

    @property
    def is_admin(self):
        return self.role.name == 'Administrator'

    @property
    def is_active(self):
        return self.active

    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and self.role is not None and permission in self.role.permissions


@whooshee.register_model('title', 'description')
class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(500))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True)
    is_explore_public = db.Column(db.Boolean, default=False)
    upper_limit_number = db.Column(db.Integer, default=999999999)
    reward = db.Column(db.Integer, default=0)
    start_timestamp = db.Column(db.DateTime, index=True, default=datetime(2099, 1, 1))
    end_timestamp = db.Column(db.DateTime, index=True, default=datetime(2099, 1, 1))
    flag = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    author = db.relationship('User', back_populates='surveys')
    questions = db.relationship('SurveyQuestion', back_populates='survey', cascade='all, delete-orphan')
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')
    participants = db.relationship('UserAnswer', back_populates='surveys', cascade='all')
    # tags = db.relationship('Tag', secondary=tagging, back_populates='photos')

    @property
    def is_published(self):
        if self.start_timestamp < datetime.utcnow() < self.end_timestamp:
            return True
        return False


class SurveyQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    # 单选：one choice；多选：multiple choice；级别：rating
    type = db.Column(db.String(10))
    # rate_max = db.Column(db.Integer)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'))

    survey = db.relationship('Survey', back_populates='questions')
    options = db.relationship('QuestionOption', back_populates='question', cascade='all')

    def rating_average(self):
        try:
            options = QuestionOption.query.with_parent(self).all()
            poll = sum([option.poll for option in options])
            average = sum([option.poll*option.choice_value for option in options])/poll
            return average
        except Exception as e:
            print(e)
            return None


class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('survey_question.id'))
    choice_text = db.Column(db.String(200))
    choice_value = db.Column(db.Integer)
    poll = db.Column(db.Integer, default=0)

    question = db.relationship('SurveyQuestion', back_populates='options')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    receiver = db.relationship('User', back_populates='notifications')


# @whooshee.register_model('name')
# class Tag(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(64), index=True, unique=True)
#
#     photos = db.relationship('Photo', secondary=tagging, back_populates='tags')
#
#
# class Comment(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     body = db.Column(db.Text)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
#     flag = db.Column(db.Integer, default=0)
#
#     replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
#     author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
#
#     photo = db.relationship('Photo', back_populates='comments')
#     author = db.relationship('User', back_populates='comments')
#     replies = db.relationship('Comment', back_populates='replied', cascade='all')
#     replied = db.relationship('Comment', back_populates='replies', remote_side=[id])


@db.event.listens_for(User, 'after_delete', named=True)
def delete_avatars(**kwargs):
    target = kwargs['target']
    for filename in [target.avatar_s, target.avatar_m, target.avatar_l, target.avatar_raw]:
        if filename is not None:  # avatar_raw may be None
            path = os.path.join(current_app.config['AVATARS_SAVE_PATH'], filename)
            if os.path.exists(path):  # not every filename map a unique file
                os.remove(path)


# @db.event.listens_for(Survey, 'after_delete', named=True)
# def delete_photos(**kwargs):
#     target = kwargs['target']
#     for filename in [target.filename, target.filename_s, target.filename_m]:
#         path = os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename)
#         if os.path.exists(path):  # not every filename map a unique file
#             os.remove(path)
