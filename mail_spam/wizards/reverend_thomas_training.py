# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import os
import re
import requests
import subprocess
import tempfile

from contextlib import contextmanager
from xml.dom import minidom
from uuid import uuid4

from odoo import api, fields, models


class ReverendThomasTraining(models.Model):

    _name = 'reverend.thomas.training'
    _description = 'Train Bayesian Classifier'

    reverend_ids = fields.Many2many(
        string='Reverend',
        comodel_name='reverend.thomas',
        default='_default_reverend_ids',
    )
    ham_message_ids = fields.Many2many(
        string='Ham Messages',
        comodel_name='mail.message',
        default=lambda s: [(6, 0, s.env['mail.message'].search([]))],
    )
    spam_source_uri = fields.Char(
        default='http://untroubled.org/spam/',
    )
    spam_file_regex = fields.Char(
        default=r'.+\.7z$',
    )
    unarchive_command = fields.Char(
        default='7z e -o %(directory)s %(file_name)s',
    )

    @api.model
    def _default_reverend_ids(self):
        Model = self.env['reverend.thomas']
        if all((self.env.context.get('active_model') == Model._name,
                self.env.context.get('active_ids'))):
            return [(6, 0, self.env.context['active_ids'])]
        default = self.env.ref('mail_spam.reverend_thomas_default')
        return [(6, 0, default.ids)]

    @api.multi
    def train_all(self):
        self.train_hams()
        self.train_spams()
        return True

    @api.multi
    def train_hams(self):
        self.ensure_one()
        self.reverend_ids.train_ham(self.ham_message_ids)

    @api.multi
    def train_spams(self):
        self.ensure_one()
        index = requests.get(self.spam_source_uri)
        dom = minidom.parseString(index.text)
        for a in dom.getElementsByTagName('a'):

            href = a.getAttribute('href')
            if not re.search(self.spam_file_regex, href):
                continue

            directory = self.__download_archive(
                '%s/%s' % (self.spam_source_uri, href),
            )

            for root, sub_folders, files in os.walk(directory):
                for file_name in files:
                    with open(os.path.join(root, file_name)) as message_file:
                        message_vals = self.env['mail.thread'].message_parse(
                            message_file.read(),
                        )
                    self.reverend_ids.train_spam(
                        self.env['mail.message'].new(message_vals),
                    )

    @api.multi
    def __download_archive(self, uri):
        response = requests.get(uri)
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(response.text)
            with self._temp_dir() as temp_dir:
                command = self.unarchive_command % {
                    'directory': temp_dir,
                    'file_name': temp_file.name,
                }
                subprocess.check_call(command.split(' '))
                return temp_dir

    @classmethod
    @contextmanager
    def _temp_dir(cls):
        tempdir = tempfile.gettempdir()
        directory = os.path.join(tempdir, str(uuid4()))
        if os.path.isdir(directory):
            yield cls._temp_dir()
        os.mkdir(directory)
        try:
            yield directory
        finally:
            os.rmdir(directory)
