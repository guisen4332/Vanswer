# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, FloatField, IntegerField
from wtforms.validators import DataRequired, Optional, Length


# class DescriptionForm(FlaskForm):
#     description = TextAreaField('Description', validators=[Optional(), Length(0, 500)])
#     submit = SubmitField()


# class TagForm(FlaskForm):
#     tag = StringField('Add Tag (use space to separate)', validators=[Optional(), Length(0, 64)])
#     submit = SubmitField()


# class CommentForm(FlaskForm):
#     body = TextAreaField('', validators=[DataRequired()])
#     submit = SubmitField()


class SurveyForm(FlaskForm):
    ispublic = BooleanField('是否使用探索公开', validators=[DataRequired()])
    reward = FloatField('单份答卷回答奖励', default=0, render_kw={'placeholder': '0'})
    surveynumber = IntegerField('回收答卷上限份数', default=9999, render_kw={'placeholder': '9999'})
    starttime = StringField('starttime',render_kw={'placeholder': '无'})
    endtime = StringField('endtime', render_kw={'placeholder': '无'})
    submit = SubmitField('确定')
