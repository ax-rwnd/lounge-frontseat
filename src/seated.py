import requests, json
from config import Config

def post_request (config, url, data):
	""" Sends a post/rest request and returns the JSON dictionary.
	config - the config to use
	url - the api endpoint address
	data - the JSON dictionary to send """
	assert(isinstance(config, Config))
	assert(isinstance(url, str))

        headers = {'Content-Type': 'application/json'}

        r = requests.post(config.api_url+url, data = json.dumps(data), headers = headers)
	print "JSON:",r.json()
	return r.json()
