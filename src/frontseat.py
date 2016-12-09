#!/usr/bin/python
import requests
import json
import os
import seated
from functools import wraps
from config import Config
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_navigation import Navigation
from wtforms import Form, BooleanField, StringField, PasswordField, validators

config = Config()
app = Flask(__name__)
nav = Navigation(app)  # setup flask navigation
app.secret_key = 'supersecret'
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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = {"username": session.get('user', ''), "session": session.get('session', '')}
        status = seated.send_post(config, "/api/auth", data)

        if status['status'] == "AUTH_OK":
            return f(*args, **kwargs)
        return redirect(url_for('login', next=request.url))

    return decorated_function


@app.route('/')
@login_required
def index():
    return render_template('index.html', title='Home', icon='home')


@app.route('/search')
@login_required
def search():
    return render_template('search.html', title='Search')


@app.route('/browse')
@app.route('/browse/<string:name>')
@login_required
def browse(name=''):
    return render_template('browse.html', title='Browse', lname=name)


class PlaylistItem:
    name = None
    id = None

    def __init__(self, name, id):
        self.name = name
        self.id = id


@app.route('/playlist/<int:user_id>')
@login_required
def playlist(user_id=''):
    ## Or, more likely, load items from your database with something like
    # items = ItemModel.query.all()

    items = seated.send_get(config, '/api/playlist/' + str(user_id))

    if items['status'] == u'QUERY_OK':
        pitems = []
        for item in items['ids']:
            pitems += [PlaylistItem(item[0], item[1])]
    elif items['status'] == u'NO_PLAYLISTS':
        pitems = None

    return render_template('playlist.html', title='Playlist', items=pitems)


@app.route('/radio')
@login_required
def radio():
    return render_template('radio.html', title='Radio')


@app.route('/info')
@login_required
def info():
    return render_template('info.html', title='info')


@app.route('/about')
@login_required
def about():
    return render_template('about.html', title='About us')


@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html', title='Contact us')


@app.route('/profile')
@app.route('/profile/<string:name>')
@login_required
def profile(name=''):
    return render_template('profile.html', pname=name)


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')

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
        data = {"username": form.username.data, "email": form.email.data, "secret": form.password.data}
        print seated.send_post(config, "/api/register", data)

        flash('Thanks for registering')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        session.pop('session', None)
        data = {"username": form.username.data, "secret": form.password.data}
        hash = seated.send_post(config, "/api/login", data)

        if hash['status'] == 'LOGIN_OK':
            session['session'] = hash['session']
            session['user'] = request.form['username']
            return redirect(url_for('protected'))
        # if data is valid, redirect to index.
        flash('Thanks for signing in')
        return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.before_request
def before_request():
    g.session = None
    print session
    if 'session' in session:
        g.session = session['session']


@app.route('/protected')
def protected():
    if g.session:
        return redirect(url_for('index'))


@app.route('/getsession')
def getsession():
    if 'session' in session:
        return session['session']
    return 'Not logged in!'


@app.route('/dropsession')
def dropsession():
    session.pop('session', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
    # app.run(host=config.host, port=config.port, debug=True)
