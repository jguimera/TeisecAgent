#!/bin/env python
import os  
import argparse  
from colorama import Fore  
from dotenv import load_dotenv  
from webapp import create_app, socketio,auth_app
load_dotenv()
# Parse Arguments and decide which Authentication to use 
parser = argparse.ArgumentParser(description="AI Assistant argument parser")  
parser.add_argument("auth", choices=["interactive", "client_secret", "default"], help="Authentication method to use.")  
args = parser.parse_args()  
auth_type = args.auth  
app = create_app(debug=False)
auth_app(auth_type)
if __name__ == '__main__':
    socketio.run(app,ssl_context='adhoc',host='localhost', port=5000)


