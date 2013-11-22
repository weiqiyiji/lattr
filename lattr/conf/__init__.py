#!/usr/bin/env python
# coding=utf-8

import os
import importlib

from lattr.conf import default_settings

ENVIRONMENT_VARIABLE = 'LATTR_SETTINGS'


class Settings(object):
    def configure(self):
        # Load settings from defaults
        self._from_object(default_settings)

        # Load settings from module defined in env
        self._from_envvar(ENVIRONMENT_VARIABLE, True)

    def _from_object(self, obj):
        for k in filter(lambda x: x.isupper(), dir(obj)):
            setattr(self, k, getattr(obj, k))

    def _from_envvar(self, variable_name, silent=False):
        module_name = os.environ.get(variable_name)
        if not module_name:
            if silent:
                return False
            raise RuntimeError('The environment variable %r is not set. '
                               'Set this variable and make it '
                               'point to a configuration file' %
                               variable_name)
        module = importlib.import_module(module_name)
        if not module:
            raise ImportError('Unknown settings module' + module_name)
        self._from_object(module)
        return True

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dir(self))


settings = Settings()
