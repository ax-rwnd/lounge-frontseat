#!/usr/bin/python
import requests, json, os, re
import seated

from functools import wraps
from config import Config
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_navigation import Navigation
from flask_openid import OpenID
from urllib2 import urlopen
from urllib import urlencode
from wtforms import Form, BooleanField, StringField, PasswordField, IntegerField, validators

#load config
config = Config()

#setup flask
app = Flask(__name__)
app.secret_key = config.secret_key
oid = OpenID(app)

#setup flask navigation
nav = Navigation(app)  
nav.Bar('top', [
    nav.Item('Home', 'index'),
    nav.Item('Search', 'search'),
    nav.Item('Browse', 'browse'),
    nav.Item('Playlist', 'playlist'),
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
    """ Checks that the user is logged in before proceeding to the requested page. """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = {"username": session.get('user', ''), "session": session.get('session', '')}
        status = seated.send_post(config, "/api/auth", data)

        if status['status'] == "AUTH_OK":
            return f(*args, **kwargs)
	else:
            return redirect(url_for('login', next=request.url))

    return decorated_function

@app.before_request
def before_request():
    """ Populate global session variable. """
    g.session = None
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


@app.route('/')
@login_required
def index():
    """ Render home screen. """
    return render_template('index.html', title='Home')


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


class ProfileForm(Form):
    steamid = StringField('Steam ID')
    oldpassword = PasswordField('Old Password')
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    """ View and update profile data. """
    form = ProfileForm(request.form)
    if request.method == 'POST' and form.validate():
	    data = {'session':session.get('session', ''), 'username':session.get('user','')}

	    #update password
	    password = form.password.data
	    if len(form.password.data)>0:
		    data['newsecret'] = password
		    data['secret'] = form.oldpassword.data

            #update steanid
            steamid = form.steamid.data
            if len(steamid)>0:
		    data['steamid'] = steamid


            #make backseat update profile
            seated.send_post(config, '/api/profile/'+session['user'], data)
	    
            return redirect(url_for('profile'))

    return render_template('profile.html', form=form)

@app.route('/signout')
def signout():
    session.pop('session', None)
    flash("You have been logged out!")
    return redirect(url_for('login'))

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
        status = seated.send_post(config, "/api/register", data)
        if status.get('status','') != u"USER_CREATED":
		if status['status'] == u"USER_EXISTS":
		    flash("That username was already taken, pick another one.")
		elif status['status'] == u"USER_NAME_LENGTH":
		    flash("Your email seems to be invalid.")
		elif status['status'] == u"MISSING_PARAMS":
		    flash("There was an internal server error!")
		return redirect(url_for('register'))
	elif status['status'] == u"USER_CREATED":
	    flash('Thank you for registering')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


class LoginForm(Form):
    """ Defines the fields required to log in. """
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate():
        # clear current session and retrieve new token from server
        session.pop('session', None)
        data = {"username": form.username.data, "secret": form.password.data}
        hash = seated.send_post(config, "/api/login", data)

        if hash['status'] == 'LOGIN_OK':
            session['session'] = hash['session']
            session['user'] = hash['username']
            flash("You have been logged in!")
            return redirect(url_for('protected'))
        else:
            flash("Login failed.")
            return redirect(url_for('login'))
    else:
        return render_template('login.html', form=form)

# OpenID Part
_steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
def get_steam_userinfo(steam_id):
	options = {
		'key': config.openid_api_key,
		'steamids': steam_id
		}
	url = 'http://api.steampowered.com/ISteamUser/' \
	'GetPlayerSummaries/v0001/?%s' % urlencode(options)

	rv = json.load(urlopen(url))
	return rv['response']['players']['player'][0] or {}

@app.route('/steamlogin')
@oid.loginhandler
def steam_login():
    return oid.try_login('http://steamcommunity.com/openid')

@oid.after_login
def create_or_login(resp):
	match = _steam_id_re.search(resp.identity_url)
	data = {'steam_id':match.group(1)}

	status = seated.send_post(config, '/api/login', data)
	if status['status'] == u'MISSING_PARAMS':
		flash("There was an internal error!")
	elif status['status'] == u'LOGIN_FAILED':
		flash("Invalid login.")
	elif status['status'] == u'LOGIN_OK':
		session['user'] = status['username']
		session['session'] = status['session']
		flash("Welcome, "+session['user']+"!")
		return redirect(url_for('index'))
	return redirect(url_for('login'))

	#print "match",match
	#steamdata = get_steam_userinfo(match)
	#session['user_id'] = g.user.id
	#flash('You are logged in as %s' % g.user.nickname)

if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=True)
