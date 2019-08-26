# aws_create_wildcard_cert
serverless wildcard cert aws acm/certbot renewal code

This uses the serverless (https://serverless.com/) framework and dnssimple dns service (mods for other services are welcome).

To install, create ``config.yml`` using ``config.yml.example`` as a template.

The serverless component wakes up once a day and if it within the renewal graceperiod it renews the cert.  

