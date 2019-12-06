# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp

from vanswer.models import User


# class EditProfileForm(FlaskForm):
#     name = StringField('Name', validators=[DataRequired(), Length(1, 30)])
#     username = StringField('Username', validators=[DataRequired(), Length(1, 20),
#                                                    Regexp('^[a-zA-Z0-9]*$',
#                                                           message='The username should contain only a-z, A-Z and 0-9.')])
#     submit = SubmitField()
#
#     def validate_username(self, field):
#         if field.data != current_user.username and User.query.filter_by(username=field.data).first():
#             raise ValidationError('The username is already in use.')


class ChangeEthereumForm(FlaskForm):
    Ethereum_id = StringField('以太账户', validators=[DataRequired(), Length(1, 100)])
    Ethereum_password = PasswordField('新密码', validators=[
        DataRequired(), Length(8, 128), EqualTo('Ethereum_password2')])
    Ethereum_password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField()


class UploadAvatarForm(FlaskForm):
    image = FileField('上传', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'The file format should be .jpg or .png.')
    ])
    submit = SubmitField()


class CropAvatarForm(FlaskForm):
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField('截取并更新')


class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField()

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('邮箱已存在.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('旧密码', validators=[DataRequired()])
    password = PasswordField('新密码', validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField()


class NotificationSettingForm(FlaskForm):
    # receive_comment_notification = BooleanField('New comment')
    # receive_follow_notification = BooleanField('New follower')
    receive_collect_notification = BooleanField('新收藏')
    submit = SubmitField()


# class PrivacySettingForm(FlaskForm):
#     public_collections = BooleanField('Public my collection')
#     submit = SubmitField()


class DeleteAccountForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    submit = SubmitField()

    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError('错误的用户名.')
