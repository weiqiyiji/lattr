#!/usr/bin/env python
# coding=utf-8

import os
import logging
import unittest

from lattr.conf import Settings, default_settings, ENVIRONMENT_VARIABLE

# Test settings
DB_BACKEND = 'test_backend'
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'lattr': {
            'handlers': ['fake']
        }
    },
    'handlers': {
        'fake': {
            'class': 'lattr.conf_test.FakeHandler',
            'level': 'INFO'
        }
    }
}


class FakeHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.record = None

    def emit(self, record):
        self.record = record


class SettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.settings = Settings()

    def tearDown(self):
        if ENVIRONMENT_VARIABLE in os.environ:
            del os.environ[ENVIRONMENT_VARIABLE]

    def test_configure(self):
        self.settings.configure()
        self.assertEqual(default_settings.DB_BACKEND,
                         self.settings.DB_BACKEND)

    def test_configure_with_env(self):
        os.environ[ENVIRONMENT_VARIABLE] = __name__
        self.settings.configure()
        self.assertEqual(DB_BACKEND, self.settings.DB_BACKEND)

    def test_configure_with_unknown_settings_module(self):
        os.environ[ENVIRONMENT_VARIABLE] = 'unknown.module'
        with self.assertRaises(ImportError):
            self.settings.configure()
