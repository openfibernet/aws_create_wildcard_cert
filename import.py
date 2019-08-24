#!/usr/bin/env python
import logging
import certbot.main
import os
import boto3
from datetime import datetime, timezone
import random
import string
def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


dir_name = '/tmp/' + randomString(10)

RENEWAL_GRACEPERIOD = os.environ.get('RENEWAL_GRACEPERIOD', 1)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

def run():
    logger.info('writing credentials file')
    arn = os.environ['CERTIFICATE_ARN']
    region_name = arn.split(':')[3]
    client = boto3.client('acm', region_name=region_name)
    response = client.describe_certificate(CertificateArn=arn)
    domain_name = os.environ['DOMAIN_NAME']
    #pdb.set_trace()
    delta_days = (response['Certificate']['NotAfter'] - datetime.now(timezone.utc)).days
    if delta_days < int(RENEWAL_GRACEPERIOD):
        os.system('mkdir ' + dir_name)
        logger.info('within grace period, renewing certificate, using directory %s' % dir_name)
        credential_file = dir_name + '/credentials'
        with open(credential_file, 'w') as file:
            file.write('dns_dnsimple_token = %s\n' % os.environ['CREDENTIAL'])
        os.chmod(credential_file, 0o600)
        certbot.main.main(['certonly', '--staging', '--agree-tos', '--email', os.environ['EMAIL_ADDRESS'], '--non-interactive', '--dns-dnsimple', '--dns-dnsimple-credentials', credential_file, '--dns-dnsimple-propagation-seconds', '60', '-d', '*.' + domain_name, '--config-dir', dir_name, '--work-dir', dir_name, '--logs-dir', dir_name])        
        def readit(thing):
            return open('%s/live/%s/%s.pem' % (dir_name, domain_name, thing)).read()
        cert = readit('cert')
        chain = readit('chain')
        privkey = readit('privkey')

        #response = client.import_certificate(CertificateArn=arn, Certificate=cert, PrivateKey=privkey, CertificateChain=chain)
    else:
        logger.info('Not within grace period (%s day) of %s' % (RENEWAL_GRACEPERIOD, response['Certificate']['NotAfter']))
    return
    

def serverless_handler(event, context):
    logger.info('running warmer')
    run()

if '__main__' == __name__:
    run()
    
