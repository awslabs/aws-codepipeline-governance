# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
from client_session_helper import boto3_client

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)

function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']


def assume_role(account_number, role_name, role_session_name=function_name):
    """Assumes the provided role name in the provided account number

    Args:
        account_number (str): Account number where the role to assume resides
        role_name (str): Name of the role to assume
        role_session_name (str, optional): The name you'd like to use for the session
            (suggested to use the lambda function name)

    Returns:
        dict: Returns standard AWS dictionary with credential details
    """
    logger.info(f"Assuming Role:{role_name} in Account:{account_number}")
    sts_client = boto3_client(service='sts')

    assumed_role_object = sts_client.assume_role(
        RoleArn=f'arn:aws:iam::{account_number}:role/{role_name}',
        RoleSessionName=role_session_name
    )

    assumed_credentials = assumed_role_object['Credentials']
    return assumed_credentials
