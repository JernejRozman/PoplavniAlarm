from flask import Flask
from markupsafe import escape

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/<name>')
def hello_name(name):
    # Escape the name to prevent XSS attacks
    return f'Hello, {escape(name)}!'
