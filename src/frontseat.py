#!/usr/bin/python
import requests
import json

from config import Config
from seated import post_request

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_navigation import Navigation
from wtforms import Form, BooleanField, StringField, PasswordField, validators

config = Config()
app = Flask(__name__)
nav = Navigation(app)  # setup flask navigation
app.secret_key = config.secret

nav.Bar('top', [
    nav.Item('Home', 'index'),
    nav.Item('Search', 'search'),
    nav.Item('Browse', 'browse'),
    nav.Item('Playlist', 'playlist'),
    nav.Item('Radio', 'radio'),
    nav.Item('Info', 'info', items=[
        nav.Item('About', 'about'),
        nav.Item('Contact', 'contact'),
    ]),
    nav.Item('Profile', 'profile', items=[
        nav.Item('Settings', 'settings'),
        nav.Item('Signout', 'signout'),
    ]),
])


@app.route('/')
def index():
    return render_template('index.html', title='Home', icon='home')


@app.route('/search')
def search():
    return render_template('search.html', title='Search')


@app.route('/browse')
@app.route('/browse/<string:name>')
def browse(name=''):
    return render_template('browse.html', title='Browse', lname=name)


@app.route('/playlist')
def playlist():
    return render_template('playlist.html', title='Playlist')


@app.route('/radio')
def radio():
    return render_template('radio.html', title='Radio')


@app.route('/info')
def info():
    return render_template('info.html', title='info')


@app.route('/about')
def about():
    return render_template('about.html', title='About us')


@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact us')


@app.route('/profile')
@app.route('/profile/<string:name>')
def profile(name=''):
    return render_template('profile.html', pname=name)


@app.route('/settings')
def settings():
    return render_template('settings.html', title='Settings')


@app.route('/signout')
def signout():
    return render_template('signout.html', title='Sign out')


class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)

    if request.method == 'POST' and form.validate():
	endpoint = '/api/register'
        data = {"username": form.username.data, "email": form.email.data, "secret": form.password.data}

	response = post_request(config, endpoint, data)
	status = response.get('status', None)
	assert(status != 'MISSING_PARAMS') #missing parameters

	if status == 'USER_CREATED':
		return redirect(url_for('profile'))
	elif status == 'USER_EXISTS':
		return "User already exists!"

    return render_template('register.html', form=form)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
