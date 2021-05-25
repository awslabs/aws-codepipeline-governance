# CodePipeline Governance
Ensure all AWS CodePipelines have mandatory actions being executed in the Orchestration Pipeline.

## Description
This solution will be initiated through a pipeline action and will parse through the CodePipeline CloudFormation template to ensure all governance rules are met before updating the CloudFormation Stack.  This 
allows the Security or Governance teams to mandate certain stages and/or actions to being executed in a particular order.  But more importantly, this will allow developers to update their own CI/CD Pipeline.  

### AWS Resource Diagram
![alt text](images/architecture-diagram.png) 

### Folder Structure
| Folder/File | Description |  
| :-------------------------| :-------------------------------------------------------------------------------------------------------------------|
| cloudformation/sam-bootstrap.yaml  | AWS Cloudformation template that will create the required AWS Resources for the solution to work properly. It will create an IAM Role, KMS Key/Alias and S3 Bucket. All of these AWS Resources are required for an AWS Serverless Application Model (SAM) deployment to successful.|
| cloudformation/function.yaml | SAM template that will deploy the AWS Lambda Function along with all dependant infrastructure. | 
| src     | Source code for AWS Lambda Functions. |
| test     | Test code for AWS Lambda Functions. |
| scripts   | Directory that has the scripts that will be executed from a CodeBuild BuildSpec file |
| scripts/main.sh | An orchestration script that will execute the all other linting/scanning scripts before building/deploying the SAM Function(s). | 
| scripts/pylint.sh   | Shell script that will execute the ```pylint``` command against all python files. |
| scripts/pyscan.sh   | Executes Bandit (python lib) against all python code within the repository to identify any security vulnerabilities. |
| scripts/sam.sh   | Executes a number of SAM commands to package / build / deploy the SAM Function to a specified account. | 
| scripts/test.sh   | Shell script that will execute the ```tox``` command to build a virtual environment and the ```pytest``` command to execute any unit tests found in the repository. |
| pytest.ini   | ini files are the configuration files of the tox project, and can also be used to hold pytest configuration if they have a [pytest] section. |
| test_requirements.txt   | Pip requirements file for test environment. |
| tox.ini | Configured file for Tox. Tox is a command-line driven automated testing tool for Python, based on the use of virtualenv. |

## Pre-requisite Steps:
- Install the Serverless Application Model CLI (SAM) [Link to AWS Doc](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
  - Since this solution builds the SAM function inside Lambda-like container, Docker must be installed and running on your workstation.

## How to deploy
### AWS Management or Shared Services Production Account
- Execute the cloudformation/sam-bootstrap.yaml into the AWS Account you chose.

  ```bash
  aws cloudformation create-stack --stack-name SAM-Bootstrap --template-body file://cloudformation/sam-bootstrap.yaml
  ```

- Deploy Serverless Application Model function.
  ```bash
  bash ./scripts/sam.sh
  ````
 
### AWS Deployment Account (account where CodePipeline will be deployed)
- IAM Role for function to assume and update CodePipeline after scanning it
  ```bash
  aws cloudformation create-stack --stack-name ScanCodePipelineAssumedRole --template-body file://cloudformation/assumed-iam-role.yaml --capabilities CAPABILITY_NAMED_IAM --parameters ParameterKey=pScanCodePipelineAccount,ParameterValue=xxxxxxxxxxx
  ````

## Deploy New / Update CodePipeline Governance Rules
- Create a yaml file with the CodePipeline Stage or Actions you wish to act as the Rule for the CodePipeline CloudFormation Template.
    - There is an example of a Rule located in *scripts/convert-2-dynamodb-item.yaml*. This example Rule ensures that the Scan Action doesn't get removed from the CodePipeline Template.
    ```yaml
    RuleNumber: "001"
    PatternType: "All"
    Contents:
      Stages:
        - Name: BuildAndPackage
          Actions:
            - Name: Scan-CodePipeline
              ActionTypeId:
                Category: Invoke
                Owner: AWS
                Provider: Lambda
                Version: "1"
              Configuration:
                FunctionName: ScanUpdateCodePipeline
                UserParameters: |
                  {
                    "cfn_template": "cloudformation/codepipeline-example.yaml"
                  }
              InputArtifacts:
                - Name: Source
              RunOrder: 1
            - Name: Update-CodePipeline
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Version: "1"
                Provider: CloudFormation
              InputArtifacts:
                - Name: Source
              Configuration:
                ActionMode: CREATE_UPDATE
                Capabilities: CAPABILITY_NAMED_IAM
                TemplatePath: Source::cloudformation/codepipeline-example.yaml
              RunOrder: 2
    ```
- Execute the convert-2-dynamodb-item script to build the Rule to fit the DynamoDB format 
  ```bash
  python scripts/convert-2-dynamodb-item.py > initial-dynamodb-item.json
  ```
  
- Deploy Initial DynamoDB Item into the Scan_CodePipeline_Rules Table
  ```bash
  aws dynamodb put-item --table-name Scan_CodePipeline_Rules --item file://initial-dynamodb-item.json
  ```

End Result - Rule Example (located in DynamoDB):

![alt text](images/rule-example-dynamodb.png) 

## Usage
Example code from CodePipeline.yaml:
```yaml
...
    - Name: BuildAndPackage
      Actions:
        - Name: Scan-CodePipeline
          ActionTypeId:
            Category: Invoke
            Owner: AWS
            Provider: Lambda
            Version: "1"
          Configuration:
            FunctionName: ScanCodePipeline
            UserParameters: !Sub |
              {
                "cfn_template": "iac/cloudformation/codepipeline.yaml"
              }
          InputArtifacts:
            - Name: Source
          OutputArtifacts: []
          RunOrder: 1
...
```

## Failure Definitions
CodePipeline action output of CloudFormation deployment failure

![alt text](images/failure.png) 

CodePipeline action output of CloudFormation deployment failure with output being over 500 characters

![alt text](images/failure-over_500_characters.png)

CodePipeline action output of CloudFormation validation failure 

![alt text](images/failure-cfn_validation_error.png) 

CodePipeline action output of CloudFormation Security Scan

![alt text](images/failure-scan.png) 

## Running CodePipeline Example
- Deploy CodePipeline (w/ dependencies) CloudFormation template
```bash
aws cloudformation create-stack --stack-name ScanCodePipelineExample --template-body file://cloudformation/codepipeline-example.yaml --capabilities CAPABILITY_NAMED_IAM 
```

- Zip up application directory
```bash
zip -r application.zip * -x "*.aws-sam*" -x "*.DS_Store*" 
```

- Update zip to S3 to initiate the pipeline
```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION=$(aws configure get region) || AWS_REGION='us-east-1'
aws s3 cp application.zip s3://orchestration-${AWS_ACCOUNT_ID}-${AWS_REGION}/application.zip 
```

### What the Pipeline should look like
![alt text](images/codepipeline-example.png) 

## License
This project is licensed under the Apache-2.0 License.
