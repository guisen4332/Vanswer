# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email
from flask_wtf import FlaskForm
from vanswer.models import User, Role
from wtforms.validators import Regexp


class EditProfileAdminForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 254), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20),
                                                   Regexp('^[a-zA-Z0-9]*$',
                                                          message='用户名需仅有 a-z, A-Z 或 0-9.')])
    Ethereum_account = StringField('以太账号', validators=[Length(0, 20), Regexp('^[a-zA-Z0-9]*$',
                                                                        message='用户名需仅有 a-z, A-Z 或 0-9.')])
    # Ethereum_account = StringField('以太账号', validators=[DataRequired(), Length(1, 20),
    #                                                Regexp('^[a-zA-Z0-9]*$',
    #                                                       message='用户名需仅有 a-z, A-Z 或 0-9.')])

    role = SelectField('Role', coerce=int)
    active = BooleanField('Active')
    confirmed = BooleanField('Confirmed')
    submit = SubmitField()

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已被使用.')

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('邮箱已被使用.')
