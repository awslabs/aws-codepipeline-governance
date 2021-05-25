# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
import json
from src.helper import compare_template_items

# --------------
# STAGE RULES
# --------------
# Matching stage/action in dynamodb item
dynamodb_item_1 = {'RuleNumber': '001', 'Contents': {'Stages': [{'Actions': [{'ActionTypeId': {'Owner': 'AWS', 'Category': 'Invoke', 'Version': '1', 'Provider': 'Lambda'}, 'Configuration': {'FunctionName': 'ScanCodePipeline', 'UserParameters': '{\n  "cfn_template": "cloudformation/codepipeline-example.yaml"\n}\n'}, 'InputArtifacts': [{'Name': 'Source'}], 'RunOrder': '1', 'Name': 'Scan-CodePipeline'}, {'ActionTypeId': {'Owner': 'AWS', 'Category': 'Deploy', 'Version': '1', 'Provider': 'CloudFormation'}, 'Configuration': {'ActionMode': 'CREATE_UPDATE', 'Capabilities': 'CAPABILITY_NAMED_IAM', 'TemplatePath': 'Source::cloudformation/codepipeline-example.yaml'}, 'InputArtifacts': [{'Name': 'Source'}], 'RunOrder': '2', 'Name': 'Update-CodePipeline'}], 'Name': 'BuildAndPackage'}]}, 'PatternType': 'All'}
# Matching action order
dynamodb_item_2 = {'RuleNumber': '002', 'Contents': {'Stages': [{'Name': 'Test'}, {'Name': 'Prod'}]}, 'PatternType': 'All'}
# Matching stage name
dynamodb_item_3 = {'RuleNumber': '003', 'Contents': {'Stages': [{'Name': 'Test'}]}, 'PatternType': 'All'}

# ---------------
# ACTION RULES
# ---------------
dynamodb_item_4 = {'RuleNumber': '001', 'PatternType': 'All', 'Contents': {'Actions': [{'Name': 'Scan-CodePipeline', 'ActionTypeId': {'Category': 'Invoke', 'Owner': 'AWS', 'Provider': 'Lambda', 'Version': '1'}, 'Configuration': {'FunctionName': 'ScanCodePipeline', 'UserParameters': '{\n  "cfn_template": "cloudformation/codepipeline-example.yaml"\n}\n'}, 'InputArtifacts': [{'Name': 'Source'}], 'RunOrder': 1}]}}

# -------------------
# PASSING TEMPLATE
# -------------------
f = open("test/pass_1_cp_template.json", "r")
pass_cp_template = json.loads(f.read())

# -------------------
# FAILING TEMPLATES
# -------------------
# No Scan-CodePipeline in stage
f = open("test/fail_1_cp_template_missing_action.json", "r")
fail_1_cp_template = json.loads(f.read())

# Not matching action order
f = open("test/fail_2_cp_template_stage_order.json", "r")
fail_2_cp_template = json.loads(f.read())

f.close()


class TestStringMethods(unittest.TestCase):

    # Pass
    def test_matching_stage_name(self):
        self.assertTrue(compare_template_items(dynamodb_item=dynamodb_item_1, cp_template=pass_cp_template))

    def test_matching_action_in_stage(self):
        self.assertTrue(compare_template_items(dynamodb_item=dynamodb_item_2, cp_template=pass_cp_template))

    def test_matching_stage_order(self):
        self.assertTrue(compare_template_items(dynamodb_item=dynamodb_item_3, cp_template=pass_cp_template))

    def test_matching_action(self):
        self.assertTrue(compare_template_items(dynamodb_item=dynamodb_item_4, cp_template=pass_cp_template))

    # Fail
    def test_missing_action_in_stage(self):
        self.assertIn(
            "Failed:",
            compare_template_items(dynamodb_item=dynamodb_item_1, cp_template=fail_1_cp_template)
        )

    def test_stage_misordered(self):
        self.assertIn(
            "Failed:",
            compare_template_items(
                dynamodb_item=dynamodb_item_2,
                cp_template=fail_2_cp_template
            )
        )

    def test_missing_action(self):
        self.assertIn(
            "Failed:",
            compare_template_items(dynamodb_item=dynamodb_item_4, cp_template=fail_1_cp_template)
        )


if __name__ == '__main__':
    unittest.main()
