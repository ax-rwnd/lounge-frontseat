import requests
import json
from flask import Flask, render_template,request

app = Flask(__name__)

@app.route('/run_post')
def run_post():
	username="asd"
	url = 'http://127.0.0.1:5000/api/register/'+username
	data = {'username':username,'email':'test@test.com','secret':'somesecrethash'}
	headers = {'Content-Type': 'application/json'}

	r = requests.post(url, data=json.dumps(data), headers=headers)

	return json.dumps(r.json(), indent=4)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
