# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from client_session_helper import boto3_client

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)


def put_job_success(job_id, message, session=None):
    """Puts job success to a pipeline by job_id and logs message to cloudwatch

    Args:
        job_id (str): Job ID from the pipeline
        message (str): Message to log for the job success
        session (object, optional): boto3 session object

    Returns:
        None
    """
    logger.info('Putting job success...')
    logger.info(message)
    client = boto3_client(service='codepipeline', session=session)
    client.put_job_success_result(jobId=job_id)


def put_job_failure(job_id, message, session=None):
    """Puts job failure to a pipeline by job_id and with message

    Args:
        job_id (str): Job ID from the pipeline
        message (str): Message to log for the job failure
        session (object, optional): boto3 session object

    Returns:
        None
    """
    logger.info('Putting job failure...')
    logger.info(message)
    client = boto3_client(service='codepipeline', session=session)
    client.put_job_failure_result(
        jobId=job_id,
        failureDetails={'message': message, 'type': 'JobFailed'}
    )
