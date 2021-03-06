#!/usr/bin/python
import requests, json, os, re
import seated

from functools import wraps
from config import Config
from flask import Flask, Request, render_template, request, redirect, url_for, flash, session, g
from flask_navigation import Navigation
from flask_openid import OpenID
from werkzeug import secure_filename
from urllib2 import urlopen
from urllib import urlencode
from wtforms import Form, BooleanField, StringField, PasswordField, IntegerField, validators

# load config
config = Config()

# setup flask
app = Flask(__name__)
app.secret_key = config.secret_key
oid = OpenID(app)

# setup flask navigation
nav = Navigation(app)
nav.Bar('top', [
    nav.Item('Home', 'index'),
    nav.Item('Search', 'search'),
    nav.Item('Browse', 'browse'),
    nav.Item('Playlists', 'playlist'),
    nav.Item('Info', 'info', items=[
        nav.Item('About', 'about'),
        nav.Item('Contact', 'contact'),
    ]),
    nav.Item('Profile', 'profile', items=[
        nav.Item('Settings', 'settings'),
	nav.Item('Friends', 'users'),
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
	elif status['status'] == 'CONNECTION_FAILED':
	    flash("The service is currently unavailable, please try again later.", 'warning')
        return redirect(url_for('login'))

    return decorated_function


@app.before_request
def before_request():
    """ Populate global session variable. """
    g.session = None
    if 'session' in session:
        g.session = session['session']


@app.route('/')
@login_required
def index():
    """ Render home screen. """
    data = {'username':session['user'], 'session':session['session'], 'action':'GET'}
    response = seated.send_post(config, '/api/friends', data)
    friends = []
    pending  = []

    if response['status'] == 'QUERY_OK':
	    friends = response['friends']
	    pending = response['pending']

    return render_template('home.html', title='Home', friends=friends, unconfirmed=pending)


@app.route('/lounge')
@app.route('/lounge/<string:username>')
def lounge (username=''):
    if username == '':
        username = session['user']

    return render_template('lounge.html', config=config, session=session, username=username)

@app.route('/search')
@login_required
def search():
    return render_template('search.html', title='Search')


@app.route('/browse')
@app.route('/browse/<string:username>')
@login_required
def browse(username=''):
    if username == '':
        username = session['user']
    data = {'username':username, 'session':session['session'], 'action':'GET', 'playlist_id':'*'}
    status = seated.send_post(config, '/api/music/0', data)
    if status['status'] == u'MUSIC_LIST':
	    items = status['tracks']
	    mitems = []
	    for item in items:
		    mitems += [MusicItem(item[2],item[1],item[0])]
            return render_template('browse.html', title='Browse', config=config, items=mitems)
    else:
        flash("Something went wrong!", 'danger')
    return render_template('browse.html', title='Browse', items=None)


class PlaylistItem:
    name = None
    id = None

    def __init__(self, name, id):
        self.name = name
        self.id = id

@app.route('/playlist')
@login_required
def playlist():
    data = {'username':session['user'], 'session':session['session'], 'title':'N/A', 'action':'GET'}
    items = seated.send_post(config, '/api/playlist', data)

    if items['status'] == u'QUERY_OK':
        pitems = []
        for item in items['ids']:
            pitems += [PlaylistItem(item[1], item[0])]
    elif items['status'] == u'NO_PLAYLISTS':
        pitems = None
    return render_template('playlists.html', title='Playlist',api_url=config.api_url, items=pitems, session=session)

class MusicItem:
    path = None
    name = None
    id = None

    def __init__(self, path, name, id):
    	self.path = path
        self.name = name
        self.id = id

@app.route('/sendfile/<int:playlist_id>', methods=['POST'])
@login_required
def upload(playlist_id):

	if not os.path.isdir(config.tmp_folder):
		os.makedirs(config.tmp_folder)

	if len(request.files.getlist("file")) == 1 and len(request.files.getlist("file")[0].filename)<=0:
		flash("Please select a file before uploading.", 'danger')
		return redirect(url_for('music', playlist_id=playlist_id))

	for f in request.files.getlist("file"):
		path = os.path.join(config.tmp_folder,secure_filename(f.filename))
		f.save(path)
		files = {'username':session['user'], 'session':session['session'], 'playlist_id':str(playlist_id), f.filename:open(path,"rb")}
		url = os.path.join(config.showtime_url,"upload")
		r = requests.post(url, files=files, verify=False)
		if (r.text == 'UPLOAD_OK'):
			flash("Your file was uploaded!", 'success')
		else:
			flash ("Upload failed, the file may have been of a non-ogg format.", 'danger')
	return redirect(url_for('music', playlist_id=playlist_id))

@app.route('/music/<int:playlist_id>')
@login_required
def music(playlist_id=None):
    if playlist_id == None:
        return redirect(url_for('playlist'))
    
    data = {'username':session['user'], 'session':session['session'], 'action':'GET', 'targetlist':playlist_id, 'playlist_id':str(playlist_id)}
    status = seated.send_post(config, '/api/music/0', data)
    if status['status'] == u'MUSIC_LIST':
        items = status['tracks']
	mitems = []
        for item in items:
            mitems += [MusicItem(item[2], item[1], item[0])]
        return render_template('music.html', title='Playlist', config=config, playlist=playlist_id,  items=mitems,api_url=config.api_url)
    elif status['status'] == u'AUTH_FAIL':
        flash("Your session is invalid, please login.", 'warning')
	return redirect(url_for('login'))
    else:
        flash("Something went wrong!", 'danger')
        return redirect(url_for('playlist'))

    #items = seated.send_get(config, '/api/music/' + str(user_id))
    #if items['status'] == u'TRACK_FOUND':
    #    pitems = []
    #    for item in items['ids']:
    #        pitems += [PlaylistItem(item[0], item[1])]
    #elif items['status'] == u'TRACK_UNKNOWN':
    #    pitems = None

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


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """ View and update profile data. """
    form = ProfileForm(request.form)
    if request.method == 'POST' and form.validate():
        data = {'session': session.get('session', ''), 'username': session.get('user', '')}

        # update password
        password = form.password.data
        if len(form.password.data) > 0:
            data['newsecret'] = password
            data['secret'] = form.oldpassword.data

        # update steamid
        steamid = form.steamid.data
        if len(steamid) > 0:
            data['steamid'] = steamid

            # make backseat update profile
        seated.send_post(config, '/api/profile/' + session['user'], data)

        return redirect(url_for('profile'))

    return render_template('profile.html', form=form)


@app.route('/signout')
def signout():
    session.pop('session', None)
    flash("You have been logged out!",'info')
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
        if status.get('status', '') != u"USER_CREATED":
            if status['status'] == u"USER_EXISTS":
                flash("That username was already taken, pick another one.",'warning' )
            elif status['status'] == u"USER_NAME_LENGTH":
                flash("Your name is too long.",'warning')
            elif status['status'] == u"MISSING_PARAMS":
                flash("There was an internal server error!", 'warning')
            elif status['status'] == u"INVALID_NAME":
                flash("Your name contained some illegal characters.",'warning')
            return redirect(url_for('register'))
        elif status['status'] == u"USER_CREATED":
            flash('Thank you for registering','success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


class LoginForm(Form):
    """ Defines the fields required to log in. """
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])


@app.route('/friends', methods=['GET'])
@login_required
def friends ():
	data = {'username':session['user'], 'session':session['session'], 'action':'GET'}
	response = seated.send_post(config, '/api/friends', data)

	if response['status'] == 'QUERY_OK':
	    confirmed = response['friends']
	    pending = response['pending']
	    return render_template('friends.html', friends=confirmed, pending=pending)

	elif response['status'] == 'NO_FRIENDS':
		flash('You have no friends yet, add some below!', 'info')
		return render_template('friends.html', friends=[])
	else:
		flash('Something went wrong!', 'warning')
		return url_for('index')

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
            session['uid'] = hash['uid']
            flash("Welcome, " + session['user'] + "!",'success')
            return redirect(url_for('index'))
	elif hash['status'] == 'CONNECTION_FAILED':
	    flash("The service is unavailable, please try again later.", "warning")
        else:
            flash("Login failed.",'danger')
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
    data = {'steam_id': match.group(1)}

    status = seated.send_post(config, '/api/login', data)
    if status['status'] == u'MISSING_PARAMS':
        flash("There was an internal error!", 'danger')
    elif status['status'] == u'LOGIN_FAILED':
        flash("Invalid login.", 'danger')
    elif status['status'] == u'INVALID_API_KEY':
        flash("The service has not configured its backend API key correctly, please contact an administrator!", danger)
    elif status['status'] == u'LOGIN_OK':
        session['user'] = status['username']
        session['uid'] = status['uid']
        session['session'] = status['session']
        flash("Welcome, " + session['user'] + "!",'success')
        return redirect(url_for('index'))
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=True)
