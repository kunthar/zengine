# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
import pytest
from pyoko.conf import settings
from pyoko.db.adapter.db_riak import BlockSave
from zengine.lib.exceptions import HTTPError
from zengine.lib.test_utils import BaseTestCase
from zengine.models import User
from zengine.messaging.model import Message
from zengine.signals import lane_user_change


class TestCase(BaseTestCase):
    def test_multi_user_mono(self):
        test_user = User.objects.get(username='test_user')
        self.prepare_client('/multi_user2/', user=test_user)
        with BlockSave(Message):
            resp = self.client.post()
        assert resp.json['msgbox']['title'] == settings.MESSAGES['lane_change_message_title']
        token, user = self.get_user_token('test_user2')
        self.prepare_client('/multi_user2/', user=user, token=token)
        resp = self.client.post()
        resp.raw()
        resp = self.client.post()
        resp.raw()
        assert resp.json['msgbox']['title'] == settings.MESSAGES['lane_change_message_title']

    def test_multi_user_with_fail(self):
        def mock(sender, *args, **kwargs):
            self.current = kwargs['current']
            self.old_lane = kwargs['old_lane']
            self.owner = list(kwargs['possible_owners'])[0]

        Message.objects.delete()

        lane_user_change.connect(mock)
        wf_name = '/multi_user/'
        self.prepare_client(wf_name, username='test_user')
        with BlockSave(Message):
            self.client.post()
        token, user = self.get_user_token('test_user')
        assert self.owner.username == 'test_user'
        self.prepare_client(wf_name, username='test_user2', token=token)
        with pytest.raises(HTTPError) as exc_info:
            self.client.post()
        assert  exc_info.value[0] == 403
        assert 'You don\'t have required permission' in exc_info.value[1]


