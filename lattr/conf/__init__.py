#!/usr/bin/env python
# coding=utf-8

import os
import importlib
import logging.config

from lattr.conf import default_settings


ENVIRONMENT_VARIABLE = 'LATTR_SETTINGS'


class Settings(object):

    def configure(self, defaults=default_settings, module_env=ENVIRONMENT_VARIABLE):
        # Load settings from defaults
        self._from_object(defaults)

        # Load settings from module defined in env
        if module_env:
            self._from_envvar(module_env, True)

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
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            raise ImportError('Unknown settings module ' + module_name)
        self._from_object(module)
        return True

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dir(self))


settings = Settings()
