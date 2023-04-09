import os
# os.system("for /f %i in ('python -m certifi') do set SSL_CERT_FILE=%i")
os.environ["SSL_CERT_FILE"]="C:/Python39/lib/site-packages/certifi/cacert.pem"
