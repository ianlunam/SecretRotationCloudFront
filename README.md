# SecretRotationCloudFront
Rotate AWS SecretsManager secret for CloudFront and WAF Custom Headers

Most SecretsManager auto-rotation examples are for databases. I needed to update a CloudFront Custom Header and the associated WAF String Rule, using a random generated string.

## To get started:
#### Set the names of the bucket and lambda function
Update the BucketName and FunctionName parameters in the top of build.sh and cloudformation.json, making sure the BucketName and FunctionName match across files.
* FunctionName - this will be used as the name of the rotation Lambda
* S3Bucket - the name of the bucket we can store code in

#### Set your profile and region parameters
Update your environment Region and Profile parameters as required, to match your region and the profile you have defined in ~/.aws/credentials.
```
export AWS_DEFAULT_REGION=us-west-1
export AWS_PROFILE=my-profile
```

#### Set the CloudFront parameters and secret name
Update the rest of the parameters in the top of cloudformation.json:
* SecretName - the name of the secret we will create in SecretsManager
* RotationDays - the frequency at which to rotate the secret, in days
* CNAME - the CNAME you use in your CloudFront Distribution
* HEADERNAME - the name of the custom header defined in your CloudFront Distribution
* WACLNAME - the name of your WAF ACL (assumes it is a Regional WAF)

#### Create the CloudFormation Stack
This step will create:
* SecretsManager secret
* Secret rotation schedule
* Lambda Function
* Lambda permissions to run and access CloudFront, SecretsManager, WAF and CloudWatch logs
* Permissions for the Secret to run the Lambda

Run `./build.sh` to build the lambda and upload it to your S3 bucket. Will also update the function if STACK_NAME is set.

## Files:
* build.sh: Builds the zipfile for the lambda, uploads it to S3, updates the Lambda (or runs the cloudformation)
* cloudformation.json: Creates the SecretsManager secret and Lambda, with permissions for the Lambda to update the WAF, SecretsManager, Cloudfront, and log to cloudwatch.
* requirements.txt: Requirements file for pip, to install required modules
* setup.cfg: required by pip when the target is the current directory
* lambda_function.py: The python code that does all the work.

#### build.sh
This script is designed to update the lambda.

Make sure you have set AWS_DEFAULT_REGION and AWS_PROFILE as required for your config.
Make sure the bucket name and lambda function name are what you want.

The script builds the zip file, creates the S3 bucket (if it doesn't exist) and uploads the zip to the bucket.

If the environment variable STACK_NAME is set it will attempt to extract the name of the lambda function from the stack and update the code.

To create the stack:
*    aws cloudformation create-stack --stack-name ${STACK_NAME} --template-body=file://cloudformation.json --capabilities CAPABILITY_IAM
To update the stack:
*    aws cloudformation update-stack --stack-name ${STACK_NAME} --template-body=file://cloudformation.json --capabilities CAPABILITY_IAM

#### cloudformation.json
Cloudformation template in json format to setup the secret and lambda

#### requirements.txt
Standard format requirements file for pip.

#### setup.cfg
Required for pip if target is the current directory. If missing pip will throw the following error:

`distutils.errors.DistutilsOptionError: must supply either home or prefix/exec-prefix -- not both`


#### lambda_function.py
The code for rotating the secret and updating the CloudFront Distribution and WAF String Rule with the new secret.
