# -*- coding: utf-8 -*-
"""
    :author: 杜桂森
    :url: https://github.com/guisen18
    :copyright: © 2019 guisen <duguisen@foxmail.com>
    :license: MIT, see LICENSE for more details.
"""
import json
import os
import requests
from celery import Celery
from flask import current_app
from flask_avatars import Avatars
from flask_bootstrap import Bootstrap
from flask_login import current_user, LoginManager, AnonymousUserMixin
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_web3 import current_web3, FlaskWeb3
from flask_whooshee import Whooshee
from flask_wtf import CSRFProtect
from web3 import Web3

bootstrap = Bootstrap()
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
moment = Moment()
whooshee = Whooshee()
avatars = Avatars()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    from vanswer.models import User
    user = User.query.get(int(user_id))
    return user


login_manager.login_view = 'auth.login'
# login_manager.login_message = 'Your custom message'
login_manager.login_message_category = 'warning'

login_manager.refresh_view = 'auth.re_authenticate'
# login_manager.needs_refresh_message = 'Your custom message'
login_manager.needs_refresh_message_category = 'warning'


class Guest(AnonymousUserMixin):

    def can(self, permission_name):
        return False

    @property
    def is_admin(self):
        return False


login_manager.anonymous_user = Guest


class CustomWeb3(Web3):
    def set_default_account(self, account: str, password: str):
        account = Web3.toChecksumAddress(account)
        self.eth.defaultAccount = account
        return self.geth.personal.unlockAccount(account, password)

    def transfer_transact_gas(self, account, gas: int):
        """
        to help the user who want to submit the transaction but don't have the enough gas it needs
        the root address will transfer the gas to address which the variate account stand for
        :param gas: suggest to use the estimateGas() function
        """
        if self.eth.getBalance(account) < gas:
            tx_hash = self.geth.personal.sendTransaction({'from': current_app.config['ROOT_GETH_ACCOUNT'],
                                                          'to': account, 'value': gas},
                                                         current_app.config['ROOT_GETH_PASSWORD'])
            return self.eth.waitForTransactionReceipt(tx_hash, timeout=current_app.config['RECEIPT_TIMEOUT'])

    def publish_survey(self, account: str, password: str, **kwargs):
        """
        input your ethereum account and passphrase
        input the args of the constructor function like:
            id='id', ipfs='ipfs', limit=1, reward=1
            the unit of reword is wei
        """
        value = kwargs['limit'] * kwargs['reward']
        self.set_default_account(account, password)
        with open(current_app.config['SURVEY_ABI'], 'r') as f_abi, \
                open(current_app.config['SURVEY_BIN'], 'r') as f_bytecode:
            abi = json.loads(f_abi.read())
            bytecode = f_bytecode.read()
            contact = self.eth.contract(abi=abi, bytecode=bytecode)

        tx_hash = contact.constructor(
            kwargs['id'], kwargs['ipfs'],
            kwargs['limit'], kwargs['reward']).transact(
            {'value': value, 'gas': current_app.config['TRANSACTION_GAS']})
        tx_receipt = self.eth.waitForTransactionReceipt(tx_hash, timeout=current_app.config['RECEIPT_TIMEOUT'])

        return tx_receipt.contractAddress, abi

    def publish_answer(self, account, password, address, abi: list, survey_hash: str, answer_hash: str):
        """
        To save the answer of the users.
        :param account: the account of user who want to save the answer
        :param survey_hash: the ipfs address of survey dir
        :param answer_hash: the ipfs address of answer file
        """
        self.set_default_account(account, password)

        contact_instance = self.eth.contract(address=address, abi=abi)
        tx_hash = contact_instance.functions.answer(survey_hash, answer_hash).transact()
        tx_receipt = self.eth.waitForTransactionReceipt(tx_hash, timeout=current_app.config['RECEIPT_TIMEOUT'])
        return tx_receipt

    def end_survey(self, account: str, password, address, abi: list):
        """
        the end the contract and get the balance back
        :param account: the account who deploy this contract
        """
        self.set_default_account(account, password)

        contact_instance = self.eth.contract(address=address, abi=abi)
        tx_hash = contact_instance.functions.surveyEnd().transact()
        tx_receipt = self.eth.waitForTransactionReceipt(tx_hash, timeout=current_app.config['RECEIPT_TIMEOUT'])
        return tx_receipt

    def transfer(self, from_account, password, to_account, value):
        self.set_default_account(from_account, password)
        tx_hash = self.eth.sendTransaction({'to': to_account, 'from': from_account, 'value': value})
        return self.eth.waitForTransactionReceipt(tx_hash, timeout=current_app.config['RECEIPT_TIMEOUT'])

    def create_account(self, password: str, balance: int):
        """
        :param password: the password of the new account
        :param balance:  the balance of the new account (transfer from the root)
        :return: the account's address
        """
        new_account = self.geth.personal.newAccount(password)
        self.transfer(current_app.config['ROOT_GETH_ACCOUNT'],
                      current_app.config['ROOT_GETH_PASSWORD'],
                      new_account,
                      balance)
        return new_account


class CustomFlaskWeb3(FlaskWeb3):
    web3_class = CustomWeb3


class CustomIpfs(object):
    @staticmethod
    def save_survey(survey_id, data=None):
        """
        :param survey_id: survey id
        :param data: survey data (format {'data': data})
        :return:
        """
        url = current_app.config['VHUB_HOST'] + '/api/survey/' + str(survey_id)
        if data is None:
            from vanswer.models import Survey
            data = {'data': Survey.query.filter_by(id=id).first().content}
        r = requests.post(url, data=data)
        return r.json()['survey_hash']

    @staticmethod
    def save_answer(user_id, data=None):
        """
        :param user_id: user_id of who answers the survey
        :param data: answer data (format {'survey_id': survey_id, 'data': data})
        :return:
        """
        url = current_app.config['VHUB_HOST'] + '/api/answer/' + str(user_id)
        if data is None:
            from vanswer.models import User
            from vanswer.models import UserAnswer
            user = User.query.filter_by(id=id).first()
            data = {'survey_id': None,
                    'data': UserAnswer.query.with_parent(user).first().answer_test}
        r = requests.post(url, data=data)
        survey_hash = r.json()['survey_hash']
        answer_hash = r.json()['answer_hash']
        return survey_hash, answer_hash
