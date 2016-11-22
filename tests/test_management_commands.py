# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

from zengine.management_commands import ManagementCommands


def test_update_permissions():
    # TODO: Add cleanup for both Permission and User models
    # TODO: Add assertation
    ManagementCommands(args=['update_permissions'])


def test_load_load_diagrams():
    ManagementCommands(args=['load_diagrams'])
    # ManagementCommands(args=['load_diagrams', '--wf_path', './diagrams/multi_user2.bpmn'])


def test_check_list():
    ManagementCommands(args=['check_list'])
