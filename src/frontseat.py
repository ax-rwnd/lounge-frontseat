#!/usr/bin/python
from flask import Flask, render_template
from flask_navigation import Navigation

app = Flask(__name__)
nav = Navigation(app) # setup flask navigation

nav.Bar('top', [
	nav.Item('Home', 'index'),
	nav.Item('About', 'about'),
	nav.Item('My Profile', 'profile'),
	nav.Item('Lounge', 'lounge')
])

@app.route('/')
def index ():
	return render_template('index.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/profile')
@app.route('/profile/<string:name>')
def profile(name=''):
	return render_template('profile.html', pname=name)

@app.route('/lounge')
@app.route('/lounge/<string:name>')
def lounge(name=''):
	return render_template('lounge.html', lname=name)

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8080, debug=True)
