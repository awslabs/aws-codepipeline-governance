# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from boto3.dynamodb.types import TypeSerializer
import yaml

f = open("scripts/convert-2-dynamodb-item.yaml", "r")
document = f.read()
db_entry = yaml.safe_load(document)
# print(db_entry)  # <-- use for creating new test cases

serializer = TypeSerializer()
deserialized_db_entry = {k: serializer.serialize(v) for k, v in db_entry.items()}
# print(json.dumps(deserialized_db_entry))
print(json.dumps(deserialized_db_entry, indent=2))  # <-- use for loaded item into AWS DynamoDB
