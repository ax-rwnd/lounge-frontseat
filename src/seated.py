import requests
import json
from flask import url_for

debug_ca_path = '/etc/letsencrypt/live/fiskpinnar.campus.ltu.se/'

def send_post(config, endpoint, data):
    '''sends a request to rest api
    configuration contain api url
    endpoint describes a resource'''
    url = config.api_url + endpoint
    headers = {'Content-Type': 'application/json'}
    data['api_key'] = config.api_key
    print "data:",data
    r = requests.post(url, data=json.dumps(data), headers=headers, verify=False)

    return r.json()


def send_get(config, endpoint):
    '''send a request to rest api
    configuration contain api url
    endpoint describes a resource'''
    url = config.api_url + endpoint
    r = requests.get(url,verify=False)
    return r.json()


def send_file(config, endpoint, data):
    fp = requests.files["name_of_file"]
    url = create_upload_url(url_for('handle_upload_response'))
    response = requests.post(url, {'file':
                                       (fp.filename, fp.stream,
                                        fp.content_type, fp.headers)})
    if response == "Success":
        return "File uploaded successfully"
    else:
        return "Something didn't work out"
