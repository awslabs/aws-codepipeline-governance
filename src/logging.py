# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os


class CustomLogger (object):
    """Sets up customer logger for all lambda functions

    Args:
        object (str): Lambda Event

    Returns:
        class:
    """
    def __init__(self, event=None):
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        self._logger = logging.getLogger()
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self._handler = self._logger.handlers[0]

        logging.getLogger("botocore").setLevel(logging.ERROR)

    @property
    def logger(self):
        return self._logger

