#!/usr/bin/env bash

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

set -e

while getopts o:r: flag; do
  case "${flag}" in
    o) ORG_ID=${OPTARG};;
    r) CP_ROLE=${OPTARG};;
    *)
  esac
done

if [[ "${ORG_ID}" == "" ]] || [[ "${CP_ROLE}" == "" ]]; then
  echo "**** Warn: OrganizationId or CodePipeline Role not found ****"
  FUNCTION_CFN="cloudformation/function.yaml"
  PARAM_OVERRIDE=""
else
  FUNCTION_CFN="cloudformation/function-sep-acc.yaml"
  PARAM_OVERRIDE="--parameter-overrides pPrincipalOrgID=${ORG_ID} pCodePipelineServiceRole=${CP_ROLE}"
fi


BASE=$(basename $PWD)
echo "#-------------------------------------------------------------#"
echo "#     Building SAM Packages for ${BASE}                        "
echo "#-------------------------------------------------------------#"

echo "Setting variables for AWS Region ang SAM S3 Bucket"
REGION=$(aws configure get region) || REGION="us-east-1"
BUCKET=$(aws s3 ls |awk '{print $3}' |grep -E "^sam-[0-9]{12}-${REGION}" )

echo "Getting KMS Key ID for SAM S3 Bucket"
KMS=$(aws s3api get-bucket-encryption \
  --bucket "${BUCKET}" \
  --region "${REGION}" \
  --query 'ServerSideEncryptionConfiguration.Rules[*].ApplyServerSideEncryptionByDefault.KMSMasterKeyID' \
  --output text
  )

echo "Building SAM Function"
sam build -t "${FUNCTION_CFN}" --use-container --region "${REGION}"

echo "Packaging SAM Function"
sam package \
  --template-file .aws-sam/build/template.yaml \
  --s3-bucket "${BUCKET}" \
  --s3-prefix "SAM" \
  --kms-key-id "${KMS}" \
  --region "${REGION}" \
  --output-template-file cloudformation/generated-sam-template.yaml

echo "Deploying SAM Function"
if [[ "${PARAM_OVERRIDE}" == "" ]]; then
  sam deploy \
    --stack-name ScanCodePipeline \
    --template-file cloudformation/generated-sam-template.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset
else
  sam deploy \
    --stack-name ScanCodePipeline \
    --template-file cloudformation/generated-sam-template.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    ${PARAM_OVERRIDE} \
    --no-fail-on-empty-changeset
fi