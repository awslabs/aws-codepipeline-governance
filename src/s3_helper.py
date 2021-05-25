# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import time
import random
import zipfile
import logging
from client_session_helper import boto3_client, boto3_session

logging.basicConfig()
logger = logging.getLogger()
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.INFO)


def download_file_from_pipeline_s3(job_data, artifact, file_in_zip):
    """Pulls artifact credentials from job_data then downloads specific file from the artifact to /tmp

    Args:
        job_data (dict): Job_data section of pipeline event
        artifact (dict): Artifact object from pipeline to pull file from
        file_in_zip (str): File within the artifact dict to download

    Returns:
        str: Full path to the downloaded file
    """
    logger.debug(f'Getting file ({file_in_zip}) from S3...')

    credentials = {
        'AccessKeyId': job_data['artifactCredentials']['accessKeyId'],
        'SecretAccessKey': job_data['artifactCredentials']['secretAccessKey'],
        'SessionToken': job_data['artifactCredentials']['sessionToken']
    }
    session = boto3_session(credentials=credentials)

    bucket = artifact['location']['s3Location']['bucketName']
    artifact_path = artifact['location']['s3Location']['objectKey']
    zip_file = artifact_path.split('/')[2]
    temp_dir = '/tmp/' + str(random.randint(1, 9999)) + '/'

    try:
        logger.debug(f'Downloading {artifact_path} from S3 Bucket ({bucket})...')
        _response = s3_download_file(
            bucket_name=bucket,
            input_file_name=artifact_path,
            output_file_name=f"/tmp/{zip_file}",
            session=session
        )
        with zipfile.ZipFile('/tmp/' + zip_file, "r") as z:
            z.extract(file_in_zip, temp_dir)

        return str(temp_dir + file_in_zip)

    except (KeyError, AttributeError, OSError) as e:
        logger.error(f'Something went wrong trying to download file. {e}')
        raise Exception(str(e)) from e


def s3_download_file(bucket_name, input_file_name, output_file_name, session=None):
    """Download a file from S3 to disk

    Args:
        bucket_name (str): Name of the bucket
        input_file_name (str): Name of the file to download from S3 (including path if necessary)
        output_file_name (str): Path to where the file should be downloaded to including its name
        session (object, optional): boto3 session object

    Returns:
        dict: Standard AWS response dict
    """
    logger.debug(f"bucket_name:{bucket_name}")
    logger.debug(f"input_file_name:{input_file_name}")
    logger.debug(f"output_file_name:{output_file_name}")
    logger.debug(f"session:{session}")

    tries = 3
    count = 1
    client = boto3_client(service='s3', session=session)
    while True:
        try:
            logger.info(f"Attempt {count} of {tries} to download file {input_file_name} from {bucket_name}")
            response = client.download_file(bucket_name, input_file_name, output_file_name)
            return response

        except Exception as e:
            count += 1
            time.sleep(10)
            if count > tries:
                raise Exception(
                    f"Failed to download key {input_file_name} in bucket {bucket_name}: {str(e)}"
                ) from e
