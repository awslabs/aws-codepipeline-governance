# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import logging
from helper import check_codepipeline_cfn_template, get_user_params, cleanup_temp
from cp_helper import put_job_success, put_job_failure
from s3_helper import download_file_from_pipeline_s3
from sts_helper import assume_role
from client_session_helper import boto3_session

log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def lambda_handler(event, context):
    print(json.dumps(event))
    required_param_list = ['cfn_template']

    job_id = event['CodePipeline.job']['id']
    job_data = event['CodePipeline.job']['data']
    artifacts = job_data['inputArtifacts']
    dest_account = event['CodePipeline.job']['accountId']

    try:
        # Set assumed role
        if dest_account != os.environ['CURRENT_ACCOUNT']:
            credentials = assume_role(account_number=dest_account, role_name=os.environ['ROLE'])
            session = boto3_session(credentials=credentials)
        else:
            session = boto3_session()

    except Exception as e:
        logger.error(f"Unable to assume role {os.environ['ROLE']}")
        session = boto3_session(credentials=job_data['artifactCredentials'])
        put_job_failure(job_id=job_id, message=str(e), session=session)

    try:
        # Extract the params
        params = get_user_params(
            job_data=job_data,
            required_param_list=required_param_list
        )

        # Get CloudFormation files from s3
        logger.info("Get CloudFormation Template file from CodePipeline - S3")
        template_location = download_file_from_pipeline_s3(
            job_data=job_data,
            artifact=artifacts[0],
            file_in_zip=params['cfn_template']
        )

        if template_location:
            scan_results = check_codepipeline_cfn_template(template=template_location)

            if "Failed:" in ",".join(scan_results):
                raise Exception(f"Pipeline Scan {scan_results}")
        else:
            logger.warning('No CloudFormation Template or Parameter file found.')

        put_job_success(job_id=job_id, message='Deployment was successful', session=session)

    except Exception as e:
        logger.info(e)
        put_job_failure(job_id=job_id, message=f"{str(e)}", session=session)

    finally:
        # Clean up the /tmp folder to avoid overlap on subsequent runs
        cleanup_temp()
