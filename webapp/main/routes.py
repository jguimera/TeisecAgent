from flask import session, redirect, url_for, render_template, request
from . import main
from .. import teisecAgent

@main.route('/', methods=['GET'])
def index():
    return render_template('homepage.html')

@main.route('/session', methods=['GET'])
def display_session():
    session_data = teisecAgent.retrievedsession()
    models = {
        "4o-Mini": {
            "input_price_per_million": 0.14392,
            "output_price_per_million": 0.5757
        },
        "4o": {
            "input_price_per_million": 2.39866,
            "output_price_per_million": 9.5747
        }
    }
    total_input_tokens=0
    total_output_tokens=0
    for token in session_data["session_tokens"]:
        total_input_tokens += token["tokens"].prompt_tokens
        total_output_tokens += token["tokens"].completion_tokens
    total_tokens = total_input_tokens + total_output_tokens

    return render_template('session.html', session=session_data, models=models, total_tokens=total_tokens, total_input_tokens=total_input_tokens, total_output_tokens=total_output_tokens)

