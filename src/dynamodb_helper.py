# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from custom_logging import CustomLogger
from boto3.dynamodb.types import TypeDeserializer
import boto3

logger = CustomLogger().logger


def scan_dynamodb(table: str, filter_express=None, exp_att_value=None, exp_att_name=None):
    """Perform a scan of dynamoDB with optional filters

    https://boto3.readthedocs.io/en/latest/reference/services/dynamodb.html#DynamoDB.Client.scan

    Args:
        table (str): Name of the table to scan
        filter_express (str, opt): String expression for the filter
        exp_att_value (dict, opt): Values of the named expression items
        exp_att_name (dict, opt): Names of expression attributes

    Example With Filter:
        filter_express = "#env = :ENVIRONMENT"
        exp_att_value = {":ENVIRONMENT": {"S": "Dev"}}
        exp_att_name = {"#env": "envName"}
        result = scan_dynamodb('Environments', filter_express, exp_att_value, exp_att_name)
        ## This will return the row of the Environments table (dict) where envName is 'Dev'

    Returns:
        list of dict: List of all items returns, contents are dict with column as key or None if no match
    """
    db_result_items = list()
    param = dict()
    count = 0

    deserializer = TypeDeserializer()

    param['TableName'] = table

    if filter_express:
        param['FilterExpression'] = filter_express
    if exp_att_value:
        param['ExpressionAttributeValues'] = exp_att_value
    if exp_att_name:
        param['ExpressionAttributeNames'] = exp_att_name

    client = boto3.client('dynamodb')
    paginator = client.get_paginator("scan")
    for page in paginator.paginate(**param):
        count = count + page['Count']
        for db_item in page['Items']:
            logger.debug(f"Adding {db_item} to items list")
            # Update DynamoDB Item from Mapping to Dictionary
            db_result_items.append({k: deserializer.deserialize(v) for k, v in db_item.items()})

    result = {'Items': db_result_items, 'Count': count}
    return result
