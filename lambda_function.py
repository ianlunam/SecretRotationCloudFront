#!/usr/bin/env python

import boto3
import dns.resolver
import logging
import json
import os
import re
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("Starting")

session = boto3.session.Session()
cft_client = session.client('cloudfront', region_name='eu-west-1')
sm_client = session.client('secretsmanager', region_name='eu-west-1')
waf_client = session.client('waf-regional', region_name='eu-west-1')

def getDistro(CName):
    distros = cft_client.list_distributions()
    while True:
        for distro in distros['DistributionList']['Items']:
            for alias in distro['Aliases']['Items']:
                if alias == CName:
                    distro = cft_client.get_distribution(Id = distro['Id'])
                    return distro['Distribution'], distro['ETag']
        if 'IsTruncated' in distros and distros['IsTruncated']:
            distros = cft_client.list_distributions(Marker = distros['NextMarker'])
    return false

def getWafId(WaclName):
    acls = waf_client.list_web_acls()
    while True:
        for acl in acls['WebACLs']:
            if acl['Name'] == WaclName:
                return acl['WebACLId']
        if 'NextMarker' in acl:
            acls = waf_client.list_web_acls(NextMarker = acl['NextMarker'])
        else:
            break
    return False

def getByteMatchSet(WaclName, HeaderName):
    waf = waf_client.get_web_acl(WebACLId = getWafId(WaclName))
    for ruleItem in waf['WebACL']['Rules']:
        rule = waf_client.get_rule(RuleId = ruleItem['RuleId'])
        if rule['Rule']['Name'] == 'StringRule':
            for predicate in rule['Rule']['Predicates']:
                if predicate['Type'] == 'ByteMatch':
                    bms = waf_client.get_byte_match_set(ByteMatchSetId = predicate['DataId'])
                    for bmt in bms['ByteMatchSet']['ByteMatchTuples']:
                        if bmt['FieldToMatch']['Type'] == 'HEADER':
                            if bmt['FieldToMatch']['Data'] == HeaderName:
                                return bms['ByteMatchSet']['ByteMatchSetId'], bmt
    return False

def replaceHeaderValue(distro, headerName, passwd):
    i = 0
    while i < len(distro['Origins']['Items']):
        h = 0
        while h < len(distro['Origins']['Items'][i]['CustomHeaders']['Items']):
            if distro['Origins']['Items'][i]['CustomHeaders']['Items'][h]['HeaderName'] == headerName:
                distro['Origins']['Items'][i]['CustomHeaders']['Items'][h]['HeaderValue'] = passwd
                return distro
            h += 1
        i += 1
    return distro

def updateHeader(distro, etag, headerName, passwd):
    distroId = distro['Id']
    distro = distro['DistributionConfig']
    distro = replaceHeaderValue(distro, headerName, passwd)
    response = cft_client.update_distribution(DistributionConfig=distro, Id=distroId, IfMatch=etag)

def updateByteMatchField(byteMatchSetId, tuple, passwd):
    # Delete existing tuple
    updates = [{
        'Action': 'DELETE',
        'ByteMatchTuple': tuple
    }]
    changeToken = waf_client.get_change_token()
    changeToken = changeToken['ChangeToken']
    response = waf_client.update_byte_match_set(ByteMatchSetId=byteMatchSetId, Updates=updates, ChangeToken=changeToken)

    # Add new tuple
    tuple['TargetString'] = passwd.encode('utf-8')
    updates = [{
        'Action': 'INSERT',
        'ByteMatchTuple': tuple
    }]
    changeToken = waf_client.get_change_token()
    changeToken = changeToken['ChangeToken']
    response = waf_client.update_byte_match_set(ByteMatchSetId=byteMatchSetId, Updates=updates, ChangeToken=changeToken)

def create_secret(SecretId, token):
    # Generate a random password
    passwd = sm_client.get_random_password(PasswordLength=30, ExcludePunctuation=True)
    passwd = passwd['RandomPassword']

    # Now try to get the secret version, if that fails, put a new secret
    try:
        sm_client.update_secret(SecretId=SecretId, ClientRequestToken=token, SecretString=passwd)
        logger.info("createSecret: Successfully reset passwd for existing secret for %s." % SecretId)
    except sm_client.exceptions.ResourceNotFoundException:
        # Put the secret
        sm_client.put_secret_value(SecretId=SecretId, ClientRequestToken=token, SecretString=passwd, VersionStages=['AWSPENDING'])
        logger.info("createSecret: Successfully put secret for SecretId %s and version %s." % (SecretId, token))


def set_secret(SecretId, token):
    metadata = sm_client.describe_secret(SecretId=SecretId)
    current_version = None
    for version in metadata["VersionIdsToStages"]:
        if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
            if version == token:
                current_version = token
                break
            current_version = version
            break

    if current_version != token:
        # Finalize by staging the secret version current
        sm_client.update_secret_version_stage(SecretId=SecretId, VersionStage="AWSCURRENT", MoveToVersionId=token, RemoveFromVersionId=current_version)
        logger.info("setSecret: Successfully set AWSCURRENT stage to version %s for secret %s." % (token, SecretId))

    # Make sure the current secret exists
    passwd = sm_client.get_secret_value(SecretId=SecretId, VersionId=token, VersionStage="AWSCURRENT")
    passwd = passwd['SecretString']
    logger.info("createSecret: Successfully retrieved secret for %s." % SecretId)

    CName = os.environ['CNAME']
    WaclName = os.environ['WACLNAME']
    HeaderName = os.environ['HEADERNAME']

    distro, etag = getDistro(CName)
    byteMatchSet, tuple = getByteMatchSet(WaclName, HeaderName)

    if not distro or not byteMatchSet:
        return

    logger.info("Setting new value in applications: {}".format(passwd))
    logger.info(distro)
    logger.info(byteMatchSet)
    logger.info(tuple)

    updateHeader(distro, etag, HeaderName, passwd)
    updateByteMatchField(byteMatchSet, tuple, passwd)

def test_secret(SecretId, token):
    pass

def finish_secret(SecretId, token):
    pass

def lambda_handler(event, context):
    logger.info("Called")
    logger.info(event)
    SecretId = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    metadata = sm_client.describe_secret(SecretId=SecretId)
    logger.info(metadata)
    if not metadata['RotationEnabled']:
        logger.error("Secret %s is not enabled for rotation" % SecretId)
        raise ValueError("Secret %s is not enabled for rotation" % SecretId)
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        logger.error("Secret version %s has no stage for rotation of secret %s." % (token, SecretId))
        raise ValueError("Secret version %s has no stage for rotation of secret %s." % (token, SecretId))
    # if "AWSCURRENT" in versions[token]:
    #     logger.info("Secret version %s already set as AWSCURRENT for secret %s." % (token, SecretId))
    #     return
    # elif "AWSPENDING" not in versions[token]:
    #     logger.error("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, SecretId))
    #     raise ValueError("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, SecretId))

    if step == "createSecret":
        create_secret(SecretId, token)

    elif step == "setSecret":
        set_secret(SecretId, token)

    elif step == "testSecret":
        test_secret(SecretId, token)

    elif step == "finishSecret":
        finish_secret(SecretId, token)

    else:
        raise ValueError("Invalid step parameter")
