#!/usr/bin/env python
# coding=utf-8

import logging.config


def configure(config_file):
    logging.config.fileConfig(config_file)
