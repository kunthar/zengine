# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
import pika

from pyoko import Model, field, ListNode
from pyoko.conf import settings
from pyoko.lib.utils import get_object_from_path
from zengine.client_queue import BLOCKING_MQ_PARAMS

UserModel = get_object_from_path(settings.USER_MODEL)

MSG_TYPES = (
    (1, "Info"),
    (11, "Error"),
    (111, "Success"),
    (2, "Direct Message"),
    (3, "Broadcast Message")
    (4, "Channel Message")
)

CHANNEL_TYPES = (
    (10, "System Broadcast"),
    (10, "User Broadcast"),
    (15, "Direct"),
    (20, "Chat"),
)


MESSAGE_STATUS = (
    (1, "Created"),
    (11, "Transmitted"),
    (22, "Seen"),
    (33, "Read"),
    (44, "Archived"),

)
ATTACHMENT_TYPES = (
    (1, "Document"),
    (11, "Spreadsheet"),
    (22, "Image"),
    (33, "PDF"),

)


def get_mq_connection():
    connection = pika.BlockingConnection(BLOCKING_MQ_PARAMS)
    channel = connection.channel()
    return connection, channel

class  Channel(Model):
    name = field.String("Name")
    code_name = field.String("Internal name")
    description = field.String("Description")
    owner = UserModel(reverse_name='created_channels')
    typ = field.Integer("Type", choices=CHANNEL_TYPES)

    class Managers(ListNode):
        user = UserModel(reverse_name='managed_channels')


    def _connect_mq(self):
        self.connection, self.channel = get_mq_connection()
        return self.channel

    def create_exchange(self):
        """
        This method creates MQ exch
        which actually needed to be defined only once.
        """
        channel = self._connect_mq()
        channel.exchange_declare(exchange=self.code_name)

class Subscription(Model):
    """
    Permission model
    """

    channel = Channel()
    user = UserModel(reverse_name='channels')
    is_muted = field.Boolean("Mute the channel")
    inform_me = field.Boolean("Inform when I'm mentioned")
    can_leave = field.Boolean("Membership is not obligatory", default=True)
    # status = field.Integer("Status", choices=SUBSCRIPTION_STATUS)

    def _connect_mq(self):
        self.connection, self.channel = get_mq_connection()
        return self.channel

    def create_exchange(self):
        """
        This method creates user's private exchange
        which actually needed to be defined only once.
        """
        channel = self._connect_mq()
        channel.exchange_declare(exchange=self.user.key)




    def __unicode__(self):
        return "%s in %s" % (self.user, self.channel.name)

class Message(Model):
    """
    Permission model
    """

    typ = field.Integer("Type", choices=MSG_TYPES)
    status = field.Integer("Status", choices=MESSAGE_STATUS)
    msg_title = field.String("Title")
    body = field.String("Body")
    url = field.String("URL")
    channel = Channel()
    sender = UserModel(reverse_name='sent_messages')
    receiver = UserModel(reverse_name='received_messages')

    def __unicode__(self):
        content = self.msg_title or self.body
        return "%s%s" % (content[:30], '...' if len(content) > 30 else '')


class Attachment(Model):
    """
    A model to store message attachments
    """
    file = field.File("File", random_name=True, required=False)
    typ = field.Integer("Type", choices=ATTACHMENT_TYPES)
    name = field.String("Name")
    description = field.String("Description")
    channel = Channel()
    message = Message()

    def __unicode__(self):
        return self.name


class Favorite(Model):
    """
    A model to store users favorited messages
    """
    channel = Channel()
    user = UserModel()
    message = Message()
