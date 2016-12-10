#!/usr/bin/python
from flask_openid import OpenID
from flask import Flask
app = Flask(__name__)
oid = OpenID(app, safe_roots=[])


if __name__ == "__main__":
    app.run(debug=True)
