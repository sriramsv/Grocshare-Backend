#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Simple server to demonstrate token verification."""

__author__ = 'cartland@google.com (Chris Cartland)'

import json
import random
import string

from flask import Flask
from flask import make_response,Response
from flask import render_template
from flask import request

import httplib2
import oauth2client.client
from oauth2client.crypt import AppIdentityError
from oauth2client.client import verify_id_token


APPLICATION_NAME = 'Grocshare'
app = Flask(__name__)
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
                         for x in range(32))


# Update client_secrets.json with your Google API project information.
# Do not change this assignment.
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']  


@app.route('/', methods=['GET'])
def index():
  """Render index.html."""
  # Set the Client ID and Application Name in the HTML while serving it.
  response = make_response(
      render_template('index.html',
                      CLIENT_ID=CLIENT_ID,
                      APPLICATION_NAME=APPLICATION_NAME))
  response.headers['Content-Type'] = 'text/html'
  return response


@app.route('/auth',methods=['GET'])
def get():
  return 'auth page'

@app.route('/auth', methods=['POST'])
def verify():
  """Verify an ID Token or an Access Token."""
  id_token = request.form.get('id_token')
  access_token = request.form.get('access_token', None)
  token_status = {}
  id_status = {}
  valid=""
  if id_token is not None:
    # Check that the ID Token is valid.
    try:
      # Client library can verify the ID token.
      jwt = verify_id_token(id_token, CLIENT_ID)
      valid="True"
    except AppIdentityError:
      valid="False"
    token_status['id_token_status'] = id_status

  resp = Response(valid, status=200, mimetype='text/plain')
  return resp


if __name__ == '__main__':
  app.debug = True
  app.run(host='0.0.0.0', port=80)
