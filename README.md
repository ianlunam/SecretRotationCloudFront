# SecretRotationCloudFront
Rotate AWS SecretsManager secret for CloudFront and WAF Custom Headers

Most SecretsManager auto-rotation examples are for databases. I needed to update a CloudFront Custom Header and the associated WAF String Rule, using a random generated string.


## To get started:
#### Create an S3 bucket
Create a bucket in S3 to store your code. This can be a completely private bucket created with the same account you will use for your profile in the build.sh. Use it's name in the parameters below.

#### Set the names of the bucket and lambda function
Update the BucketName and FunctionName parameters in the top of build.sh and cloudformation.json, making sure the BucketName and FunctionName match across files.
* FunctionName - this will be used as the name of the rotation Lambda
* BucketName - the name of the bucket we can store code in

#### Set your profile and region parameters
Update the Region and Profile parameters in the top of build.sh to match your region and the profile you have defined in ~/.aws/credentials.

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

Run `./build.sh create` to run the cloudformation and create the stack.

## Files:
* build.sh: Builds the zipfile for the lambda, uploads it to S3, updates the Lambda (or runs the cloudformation)
* cloudformation.json: Creates the SecretsManager secret and Lambda, with permissions for the Lambda to update the WAF, SecretsManager, Cloudfront, and log to cloudwatch.
* requirements.txt: Requirements file for pip, to install required modules
* setup.cfg: required by pip when the target is the current directory
* lambda_function.py: The python code that does all the work.

#### build.sh
This script is designed to update the lambda. The bucket used for storing code must exist before running this.

Make sure the region, profile, bucket name and lambda function name are what you want.

Can be run with different parameters:
* `./build create` - to create the stack
* `./build update` - to update the stack
* `./build upload` - to update the Lambda only
* `./build` - to update the Lambda only (same as with `upload`)

The script deletes anything old hanging around, installs the required modules from requirements.txt, zips it all up, uploads it to S3, and then, depending on the parameter passed, either creates or updates the cloudformation stack, or simply updates the Lambda, and finally deletes all the stuff the pip install did, leaving the zip file in place.

#### cloudformation.json
Cloudformation template in json format to setup the secret and lambda

#### requirements.txt
Standard format requirements file for pip.

#### setup.cfg
Required for pip if target is the current directory. If missing pip will throw the following error:

`distutils.errors.DistutilsOptionError: must supply either home or prefix/exec-prefix -- not both`


#### lambda_function.py
The code for rotating the secret and updating the CloudFront Distribution and WAF String Rule with the new secret.
