# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
import json
import shutil
import yaml
from dynamodb_helper import scan_dynamodb

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)


def check_codepipeline_cfn_template(template):
    """Checks CodePipeline (CloudFormation Template) against DynamoDB Rules database
    to ensure security / governance policies

    Args:
        template (str): AWS CloudFormation template local location

    Returns:
        :obj: Returns list of results from security scan
    """
    cp_found = False
    scan_stages = None
    results = list()
    logger.info("Checking CodePipeline Template for Compliance")

    # Get Rules from DynamoDB Table
    scan_results = scan_dynamodb(table=os.environ['DYNAMODB_TABLE'])
    logger.info(f"Parsing through rules {scan_results}")

    if scan_results.get('Count', 0) < 0:
        logger.warning(f"No Items found in DynamoDBTable:{os.environ['DYNAMODB_TABLE']}")
        results.append("NoItemsFound")
        return results

    yaml.add_multi_constructor('!', lambda l, suffix, node: None)
    with open(template, 'r') as stream:
        _json = yaml.load(stream, Loader=yaml.Loader)
        # _json = yaml.safe_load(stream)   # <-- ISSUE: could not determine a constructor for the tag '!Sub'

    # Make sure current cfn file has CodePipeline in it
    for _key, _value in _json['Resources'].items():
        for __key, __value in _value.items():
            if __key == "Type" and __value == "AWS::CodePipeline::Pipeline":
                cp_found = True

            if cp_found and isinstance(__value, dict) and __key == 'Properties':
                scan_stages = __value

    # Scan each item in table
    if scan_stages:
        for x in scan_results['Items']:
            logger.info(f"Scanning Rule:{x['RuleNumber']}")
            if x['PatternType'] == 'All':
                results.append(compare_template_items(x, scan_stages))

    else:
        logger.warning("No CodePipeline Template found to Scan against.")
        results.append("NoPipelineStagesFound")

    logger.info(f"Scan Results:{results}")
    return results


def compare_template_items(dynamodb_item, cp_template):
    """Does the actual DynamoDB rule and CloudFormation Template compare

    Args:
        dynamodb_item (dict): Security / governance rule policy to scan against
        cp_template (dict): AWS CodePipeline CloudFormation Template

    Returns:
        :obj: Returns scan results
    """
    _result = ""
    _order_result = True

    logger.info(f"DynamoDB Item:{dynamodb_item}")
    logger.info("Determining whether DynamoDB Item is scanning for a Stage or an Action")

    dyn_scan_stages = dynamodb_item['Contents'].get('Stages')
    dyn_scan_actions = dynamodb_item['Contents'].get('Actions')

    if dyn_scan_stages:
        if len(dyn_scan_stages) > 1:
            _order_result = check_for_stage_order(dyn_scan_stages, cp_template['Stages'])

        for dyn_scan_stage in dyn_scan_stages:
            _result = scan_for_stage(dyn_scan_stage, cp_template['Stages'])

    elif dyn_scan_actions:
        for dyn_scan_action in dyn_scan_actions:
            _result = scan_for_action(dyn_scan_action, cp_template['Stages'])

    if _result and _order_result:
        return f"Passed:{dynamodb_item['RuleNumber']}"

    return f"Failed:{dynamodb_item}"


def scan_for_stage(dynamodb_item_stage, cp_stages):
    """This will compare the DynamoDB Stage Item against all CodePipeline Stages

    Args:
        dynamodb_item_stage (dict): Security / governance rule policy to scan against
        cp_stages (list): AWS CodePipeline Stages to be scanned

    Returns:
        :obj: Returns scan results
    """
    logger.info("Executing Stage Scan")
    dyn_item_actions = dynamodb_item_stage.get('Actions')
    dyn_item_actions_results = {}

    logger.debug(f"dynamodb_item_stage:{dynamodb_item_stage}")
    logger.debug(f"cp_stages:{cp_stages}")
    logger.debug(f"dyn_item_actions:{dyn_item_actions}")

    # Parse each stage in the CodePipeline Template
    for cp_stage in cp_stages:
        if cp_stage and (cp_stage["Name"] == dynamodb_item_stage.get("Name")):
            logger.info("Found Matching Stage Name, Checking Action Configuration")

            # Parse each action in the CodePipeline Template
            for cp_action in cp_stage['Actions']:

                # If DynamoDB doesn't have actions but Stage matched, PASS
                if not dyn_item_actions:
                    logger.info("DynamoDB Item has no actions")
                    return True

                else:
                    # Check each DynamoDB Action against the CodePipeline Actions, since we could have multiple actions
                    #  in the DynamoDB item we are setting the results of each action within a dictionary
                    #  (example {'Scan-CodePipeline': True, 'Update-CodePipeline': False}) if values are False, FAIL
                    for dyn_item_action in dyn_item_actions:
                        logger.info(f"dyn_item_action:{dyn_item_action}")
                        logger.info(f"cp_action:{cp_action}")

                        if dyn_item_action.get('Configuration', {}).items() <= cp_action['Configuration'].items() \
                                and dyn_item_action.get('ActionTypeId', {}).items() <= cp_action['ActionTypeId'].items() \
                                and dyn_item_action.get('Name', {}) == cp_action['Name']:
                            dyn_item_actions_results.update({dyn_item_action['Name']: True})

                        else:
                            if not dyn_item_actions_results.get(dyn_item_action['Name'], False):
                                dyn_item_actions_results.update({dyn_item_action['Name']: False})

            logger.debug(dyn_item_actions_results)

            if [_v for _k, _v in dyn_item_actions_results.items() if _v is False]:
                return False
            else:
                return True

    return False


def scan_for_action(dynamodb_item_action, cp_stages):
    """This will compare the DynamoDB Action Item against all CodePipeline Stages

    Args:
        dynamodb_item_action (dict): Security / governance rule policy to scan against
        cp_stages (list): AWS CodePipeline Stages to be scanned

    Returns:
        :obj: Returns scan results
    """
    logger.info("Executing Action Scan")
    logger.debug(f"dynamodb_item_action:{dynamodb_item_action}")
    # Parse each stage in the CodePipeline Template
    for cp_stage in cp_stages:
        logger.debug(f"cp_stage:{cp_stage}")
        logger.info(f"Scanning CodePipeline Stage:{cp_stage['Name']}")
        for cp_action in cp_stage['Actions']:
            logger.debug(f"cp_action:{cp_action}")
            if cp_action.get('Configuration') and \
                    dynamodb_item_action['Configuration'].items() <= cp_action['Configuration'].items() and \
                    dynamodb_item_action['ActionTypeId'].items() <= cp_action['ActionTypeId'].items() and \
                    dynamodb_item_action.get('Name') == cp_action.get('Name'):
                return True

    return False


def check_for_stage_order(dyn_scan_stages, cp_stages):
    """This will compare the DynamoDB Stage order against all CodePipeline Stages

    Args:
        dyn_scan_stages (dict): Dictionary of CodePipeline Stages in a governed order
        cp_stages (list): AWS CodePipeline Stages to be scanned

    Returns:
        :boolean: If stage order matches
    """
    logger.debug(f"dyn_scan_stages:{dyn_scan_stages}")
    logger.debug(f"cp_stages:{cp_stages}")

    # Get just Stage Names from DynamoDB Item and CodePipeline
    _dyn_scan_stages = list(map(lambda x: x['Name'], dyn_scan_stages))
    _cp_stages = list(map(lambda x: x['Name'], cp_stages))

    # Removing Stages that are not mentioned in the dyn_scan_stages
    _stages_to_remove = [x for x in _cp_stages if x not in _dyn_scan_stages]
    for _stage_to_remove in _stages_to_remove:
        _cp_stages.remove(_stage_to_remove)

    logger.debug(f"_dyn_scan_stages:{_dyn_scan_stages}")
    logger.debug(f"_cp_stages:{_cp_stages}")

    return _dyn_scan_stages == _cp_stages


def get_user_params(job_data, required_param_list):
    """Pulls and validates required user parameters from job_data, returns json object with parameters

    Args:
        job_data (dict): Job data from event
        required_param_list (list): List of parameters required to be pulled

    Returns:
        :obj:`json`: Returns json object (dict) of the user parameters
    """

    logger.debug(f'Getting User Parameters ({", ".join(required_param_list)})')
    try:
        # Get the user parameters which contain the stack, artifact and file settings
        user_parameters = job_data['actionConfiguration']['configuration']['UserParameters']
        decoded_parameters = json.loads(user_parameters)
        logger.info(f"decoded_parameters:{decoded_parameters}")

    except TypeError as e:
        # We're expecting the user parameters to be encoded as JSON so we can pass multiple values.
        # If the JSON can't be decoded then fail the job with a helpful message.
        raise Exception('UserParameters could not be decoded as JSON') from e

    for param in required_param_list:
        if param not in decoded_parameters:
            # Validate that the stack is provided, otherwise fail the job with a helpful message.
            raise Exception(f'Error: Parameter ({param}) not found in Function Invoke.')

    return decoded_parameters


def cleanup_temp():
    temp_dir = '/tmp'
    for f in os.listdir(temp_dir):
        logger.info('Removing {} from {}'.format(f, temp_dir))
        if os.path.isdir(f"{temp_dir}/{f}"):
            shutil.rmtree(f"{temp_dir}/{f}")

        else:
            os.remove(os.path.join(temp_dir, f))
