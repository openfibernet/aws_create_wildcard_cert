#!/usr/bin/env python
import logging
import certbot.main
import os
import sys
import boto3
from datetime import datetime, timezone
import random
import string
import re


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))



RENEWAL_GRACEPERIOD = os.environ.get('RENEWAL_GRACEPERIOD', 1)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

S3_URI = os.environ['S3_URI']
m = re.match('^([^/]*)/(.*)$', S3_URI)
if not m:
    logger.error('not a legal s3 uri %s' % S3_URI)
    sys.exit(-1)
else:
    s3_bucket = m.group(1)
    s3_prefix = m.group(2)
    s3_client = boto3.client('s3')


def run():
    dir_name = '/tmp/' + randomString(10)
    logger.info('writing credentials file')

    arn = os.environ['CERTIFICATE_ARN']
    region_name = arn.split(':')[3]
    client = boto3.client('acm', region_name=region_name)
    response = client.describe_certificate(CertificateArn=arn)
    wildcard_domain_name = response['Certificate']['DomainName']
    if not wildcard_domain_name.startswith('*.'):
        logger.error('%s is not a wildcard domain name, exiting')
        return
    domain_name = wildcard_domain_name[2:]
    delta_days = (response['Certificate']['NotAfter'] - datetime.now(timezone.utc)).days
    if delta_days < int(RENEWAL_GRACEPERIOD):
        os.system('mkdir ' + dir_name)
        logger.info('within grace period, renewing certificate, using directory %s' % dir_name)
        credential_file = dir_name + '/credentials'
        with open(credential_file, 'w') as file:
            file.write('dns_dnsimple_token = %s\n' % os.environ['CREDENTIAL'])
        os.chmod(credential_file, 0o600)
        args = ['certonly', '--agree-tos', '--email', os.environ['EMAIL_ADDRESS'], '--non-interactive', '--dns-dnsimple', '--dns-dnsimple-credentials', credential_file, '--dns-dnsimple-propagation-seconds', '60', '-d', '*.' + domain_name, '--config-dir', dir_name, '--work-dir', dir_name, '--logs-dir', dir_name]
        if os.environ.get('STAGING'):
            args.append('--staging')
        certbot.main.main(args)

        # certbot sets root logger level to DEBUG.... oy
        logging.getLogger().setLevel(logging.INFO)

        def readit(thing):
            return open('%s/live/%s/%s.pem' % (dir_name, domain_name, thing)).read()
        cert = readit('cert')
        chain = readit('chain')
        privkey = readit('privkey')
        fullchain = readit('fullchain')
        
        def upload_to_s3(thing):
            s3_client.upload_file('%s/live/%s/%s.pem' % (dir_name, domain_name, thing), s3_bucket, '%s/%s/%s.pem' % (s3_prefix, domain_name, thing))

        upload_to_s3('cert')
        upload_to_s3('chain')
        upload_to_s3('privkey')
        upload_to_s3('fullchain')
        if not os.environ.get('STAGING'):
            response = client.import_certificate(CertificateArn=arn, Certificate=cert, PrivateKey=privkey, CertificateChain=chain)
    else:
        logger.info('Not within grace period (%s day) of %s' % (RENEWAL_GRACEPERIOD, response['Certificate']['NotAfter']))
    return
    

def serverless_handler(event, context):
    logger.info('running importer')
    run()

if '__main__' == __name__:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    run()
    
