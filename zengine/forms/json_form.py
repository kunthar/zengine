# -*-  coding: utf-8 -*-
"""
This module contains JsonForm class which extends ModelForm to achieve
three main goals:

- Allow custom forms.
- Allow attaching of additional fields and buttons to existing Forms.
- Implement JSON serialization compatible with `Ulakbus-UI API`_.

.. _Ulakbus-UI API: http://www.ulakbus.org/wiki/ulakbus-api-ui-iliskisi.html

"""
# -
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
from uuid import uuid4

import six

from pyoko.fields import BaseField
from zengine.forms.fields import Button
from zengine.lib.cache import Cache
from zengine.lib.exceptions import FormValidationError
from .model_form import ModelForm

class FormCache(Cache):
    """
    Caches various properties of serialized form to validate incoming form data

    Args:
        form_id: Unique form id
    """
    PREFIX = 'FRMCACHE'
    SERIALIZE = True

    def __init__(self, form_id=None):
        if not form_id:
            form_id = uuid4().hex
        self.form_id = form_id
        super(FormCache, self).__init__(form_id)

class JsonForm(ModelForm):
    """
    A base class for building customizable forms with pyoko fields and models.
    Has some fake methods and attributes to simulate model API

    .. code-block:: python

        from zengine.forms import fields, JsonForm

        class TestForm(JsonForm):
            class Meta:
                title = 'Form Title'
                help_text = "Form help text"

            code = fields.String("Code Field")
            no = fields.Integer('Part No', required=False)
            save = fields.Button("Save", cmd="save_it", flow="goto_finish")

            class SomeFoos(ListNode):
                foo = fields.String('Foo Field')
                hid = fields.String(hidden=True)



    """

    # properties that will be directly transferred to serialized forms root
    META_TO_FORM_ROOT = ['inline_edit',]
    META_TO_FORM_META = ['translate_widget',
                         'allow_selection',
                         'allow_add_listnode',
                         'allow_actions']

    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('current')
        # Fake method to emulate pyoko model API.
        self._nodes = {}
        self._fields = {}
        self._field_values = {}
        self.key = None
        self._data = {}
        self.exist = False
        self._ordered_fields = []
        self.processed_nodes = []
        super(JsonForm, self).__init__(*args, **kwargs)
        self._prepare_nodes()
        self.process_form()

    def get_links(self, **kw):
        """ Fake method to emulate pyoko model API. """
        return []

    def _get_bucket_name(self):
        """ Fake method to emulate pyoko model API. """
        return ''

    def get_unpermitted_fields(self):
        """ Fake method to emulate pyoko model API. """
        return []

    def _set_get_choice_display_method(self, *args, **kwargs):
        """ Fake method to emulate pyoko model API. """
        pass

    def get_humane_value(self, name):
        """ Fake method to emulate pyoko model API. """
        return name

    def is_in_db(self):
        """ Fake method to emulate pyoko model API. """
        return False

    def process_form(self):
        # if self._ordered_fields:
        #     return
        self.non_data_fields = []
        self._ordered_fields = []
        _items = list(self.__class__.__dict__.items()) + list(self.__dict__.items())
        for key, val in _items:
            if isinstance(val, BaseField):
                val.name = key
                self._fields[key] = val
            if isinstance(val, (Button,)):
                self.non_data_fields.append(key)

        for v in sorted(self._fields.items(), key=lambda x: x[1]._order):
            self._ordered_fields.append((v[0], v[1]))

    def _prepare_nodes(self):
        _items = list(self.__class__.__dict__.items()) + list(self.__dict__.items())
        for key, val in _items:
            if getattr(val, '_TYPE', '') in ['Node', 'ListNode']:
                self._nodes[key] = val(_root_node=self)
                setattr(self, key, val(_root_node=self))

    def set_data(self, data):
        """
        Fills form with data

        Args:
            data (dict): Data to assign form fields.

        Returns:
            Self. Form object.

        """
        for name in self._fields:
            setattr(self, name, data.get(name))
        return self

    def serialize(self):
        """
        Converts the form/model into JSON ready dicts/lists compatible
        with `Ulakbus-UI API`_.

        Example:

            .. code-block:: json

                {
                  "forms": {
                    "constraints": {},
                    "model": {
                      "code": null,
                      "name": null,
                      "save_edit": null,
                    },
                    "grouping": {},
                    "form": [
                      {
                        "helpvalue": null,
                        "type": "help"
                      },
                      "name",
                      "code",
                      "save_edit"
                    ],
                    "schema": {
                      "required": [
                        "name",
                        "code",
                        "save_edit"
                      ],
                      "type": "object",
                      "properties": {
                        "code": {
                          "type": "string",
                          "title": "Code Name"
                        },
                        "name": {
                          "type": "string",
                          "title": "Name"
                        },
                        "save_edit": {
                          "cmd": "save::add_edit_form",
                          "type": "button",
                          "title": "Save"
                        }
                      },
                      "title": "Add Permission"
                    }
                  }
                }
        """
        result = {
            "schema": {
                "title": self.title,
                "type": "object",
                "properties": {},
                "required": []
            },
            "form": [
                {
                    "type": "help",
                    "helpvalue": self.help_text
                }
            ],
            "model": {}
        }
        for itm in self.META_TO_FORM_ROOT:
            if itm in self.Meta.__dict__:
                result[itm] = self.Meta.__dict__[itm]

        if self._model.is_in_db():
            result["model"]['object_key'] = self._model.key
            result["model"]['model_type'] = self._model.__class__.__name__
            result["model"]['unicode'] = six.text_type(self._model)

        for itm in self._serialize():
            item_props = {'type': itm['type'], 'title': itm['title']}

            if not itm.get('value') and 'kwargs' in itm and 'value' in itm['kwargs']:
                itm['value'] = itm['kwargs'].pop('value')

            if 'kwargs' in itm and 'widget' in itm['kwargs']:
                item_props['widget'] = itm['kwargs'].pop('widget')

            result["model"][itm['name']] = itm['value'] or itm['default']

            if itm['type'] == 'model':
                item_props['model_name'] = itm['model_name']

            if itm['type'] not in ['ListNode', 'model', 'Node']:
                if 'hidden' in itm['kwargs']:
                    # we're simulating HTML's hidden form fields
                    # by just setting it in "model" dict and bypassing other parts
                    continue
                else:
                    item_props.update(itm['kwargs'])
            if itm.get('choices'):
                self._handle_choices(itm, item_props, result)
            else:
                result["form"].append(itm['name'])

            if 'schema' in itm:
                item_props['schema'] = itm['schema']

            # this adds default directives for building
            # add and list views of linked models
            if item_props['type'] == 'model':
                item_props.update({
                    'add_cmd': 'add_edit_form',
                    'list_cmd': 'select_list',
                    'wf': 'crud',
                })
            result["schema"]["properties"][itm['name']] = item_props


            if itm['required']:
                result["schema"]["required"].append(itm['name'])
        self._cache_form_details(result)
        return result

    def deserialize(self, form_data, do_validation=True):
        if form_data and do_validation:
            form_id = form_data['form_key']
            form_details = FormCache(form_id).get()
            if form_data.keys() != form_details['model']:
                not_matching = filter(lambda x: x not in form_details['model'],
                               form_data.keys())
                if not_matching:
                    raise FormValidationError("Form keys not match: %s" % not_matching)
            self.non_data_fields = form_details['non_data_fields']
        return self._deserialize(form_data)

    def _cache_form_details(self, form):
        """
        Caches some form details to lates process and validate incoming (response) form data

        Args:
            form: form dict
        """
        cache = FormCache()
        form['model']['form_key'] = cache.form_id
        cache.set(
            {
                'model': form['model'].keys(),
                'non_data_fields': self.non_data_fields
            }
        )
        # updating form inplace


    def _handle_choices(self, itm, item_props, result):
        # ui expects a different format for select boxes
        choices_data = self.get_choices(itm.get('choices'))
        item_props['type'] = 'select'
        result["form"].append({'key': itm['name'],
                               'type': 'select',
                               'title': itm['title'],
                               'titleMap': choices_data})
