from flask import session, redirect, url_for, render_template, request
from . import main
from .. import teisecAgent


@main.route('/', methods=['GET'])
def index():
    return render_template('homepage.html')

@main.route('/session', methods=['GET'])
def display_session():
    session_data = teisecAgent.retrievedsession()
    return render_template('session.html', session=session_data)
