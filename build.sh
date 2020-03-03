FUNCTIONNAME="IanTestSecretRotation"
BUCKETNAME="digital-dev-lambda-code"
REGION="eu-west-1"
PROFILE="b4c-digital-dev"

STATE=${1:-upload}

# Get rid of any leftover crud
rm -rf reqbundle.zip bin* boto3* botocore* certifi* chardet* dateutil* dns* docutils* idna* jmespath* python_dateutil-2.8.1.dist-info requests* s3transfer* urllib3* six* __pycache__*

# Install required packages
pip3 install --target . -r requirements.txt

# Create zip file
zip -r9 reqbundle.zip .

# Upload
aws --region ${REGION} --profile ${PROFILE} s3 cp reqbundle.zip s3://${BUCKETNAME}/${FUNCTIONNAME}.zip

if [ "$STATE" == "upload" ]; then
    aws --region ${REGION} --profile ${PROFILE} lambda update-function-code --function-name ${FUNCTIONNAME} --zip-file fileb://reqbundle.zip
fi

if [ "$STATE" == "update" ]; then
    aws --region ${REGION} --profile ${PROFILE} cloudformation update-stack --stack-name ${FUNCTIONNAME} --template-body=file://cloudformation.json --capabilities CAPABILITY_IAM
fi

if [ "$STATE" == "create" ]; then
    aws --region ${REGION} --profile ${PROFILE} cloudformation create-stack --stack-name ${FUNCTIONNAME} --template-body=file://cloudformation.json --capabilities CAPABILITY_IAM
fi

# Remove packages and zip file
rm -rf bin* boto3* botocore* certifi* chardet* dateutil* dns* docutils* idna* jmespath* python_dateutil-2.8.1.dist-info requests* s3transfer* urllib3* six* __pycache__*
