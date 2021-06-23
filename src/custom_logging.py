# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os


class CustomLogger:
    """Sets up custom logger for lambda functions

    Returns:
        class:
    """
    def __init__(self):
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        self._logger = logging.getLogger()
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self._handler = self._logger.handlers

        logging.getLogger("botocore").setLevel(logging.ERROR)

    @property
    def logger(self):
        return self._logger
