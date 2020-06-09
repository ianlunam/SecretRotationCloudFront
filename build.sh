#!/bin/bash

VARFILE=../../vars.env
source ${VARFILE}

S3Key=${S3Key:-package.zip}
S3Bucket=${S3Bucket:-my-lambda-code}
LambdaKey=RotationLambda

cd "$(dirname "$0")"

rm -rf build ${S3Key}

mkdir build
cd build
cp ../setup.cfg .
cp ../lambda_function.py .

if [[ $(uname -s) == 'Darwin' ]]; then
    pip3 install -r ../requirements.txt --target .
else
    pip3 install -r ../requirements.txt --system --target .
fi
zip -r9q ../${S3Key} *
cd ..
rm -rf build

if [[ ! -z "${S3Bucket}" ]]; then
    aws s3 mb s3://${S3Bucket} --region eu-west-1 || true
    aws s3 cp ${S3Key} s3://${S3Bucket}/
fi

if [[ ! -z "${STACK_NAME}" && ! -z "${LambdaKey}" ]]; then
    FunctionName=$(aws cloudformation describe-stack-resource --stack-name ${STACK_NAME} --logical-resource-id ${LambdaKey} --query 'StackResourceDetail.PhysicalResourceId' --output text 2>/dev/null || true)
fi
if [[ ! -z "${FunctionName}" ]]; then
    aws lambda update-function-code --function-name ${FunctionName} --zip-file fileb://${S3Key}
    rm -f ${S3Key}
fi

