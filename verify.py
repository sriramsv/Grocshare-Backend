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

from collections import OrderedDict
try:
    import cPickle as pickle
except:
    import pickle
import json,os
import random
import string
from collections import defaultdict
from blinker import signal
from flask import Flask
from flask import make_response,Response
from flask import render_template
from flask import request,session,g
import httplib2
import oauth2client.client
from oauth2client.crypt import AppIdentityError
from oauth2client.client import verify_id_token
import MySQLdb
from orderclass import Order,OrderWrapper,jdefault,JsonLoad
import mail

APPLICATION_NAME = 'Grocshare'
app = Flask(__name__)
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
						 for x in range(32))


# Update client_secrets.json with your Google API project information.
# Do not change this assignment.
CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']
INSTANCE_NAME="grocshare-0408:grocshare-db"


# Start the scheduler

send_data = signal('addorder')
check = signal('checkorder')


def request_has_connection():
	return hasattr(g, 'db')

def get_request_connection():
	if not request_has_connection():
	  if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
			g.db = MySQLdb.connect(unix_socket='/cloudsql/' + INSTANCE_NAME, db='orderlist', user='root', charset='utf8',passwd='root')
	  else:
			g.db = MySQLdb.connect(host='127.0.0.1', port=3306, db='orderlist', user='root',charset='utf8',passwd='toor')
	return g.db

@app.teardown_request
def close_db_connection(ex):
	if request_has_connection():
		conn = get_request_connection()
		conn.close()

def index():
  """Render index.html."""
  response=Response("grocshare application",status=200)
  return response


@app.route('/auth',methods=['GET'])
def get():
  if 'valid' in session.keys():
	valid=session['valid']
	resp=Response(str(valid),status=200,mimetype='text/plain')
  else:
	resp=Response(status=404)
  return resp

@app.route('/auth', methods=['POST'])
def verify():
  """Verify an ID Token or an Access Token."""
  id_token = request.form.get('id_token')
  access_token = request.form.get('access_token', None)
  token_status = {}
  id_status = {}
  valid=""
  v={}
  print id_token
  if id_token is not None:
	# Check that the ID Token is valid.
	try:
	  # Client library can verify the ID token.
	  jwt = verify_id_token(id_token, CLIENT_ID)
	  valid=True
	  db=get_request_connection()
	  cursor=db.cursor()
	  name=jwt['given_name']
	  email=jwt['email']
	  userid=jwt['sub']
	  try:
		cursor.execute("insert into userlist(username,userid,email) values(%s,%s,%s);",(name,userid,email))
	  except:
		Response("Could not save data",status=200)
	  db.commit()
	  # db.close()
	except AppIdentityError:
	  valid=False
	token_status['id_token_status'] = id_status
	session['valid']=valid

	v['valid']=valid
	resp = Response(json.dumps(v), status=200, mimetype='application/json')
  else:
	resp=Response("Empty token",status=200)
  return resp


@app.route('/addorder',methods=['POST'])
def addorder():
    orderslist=json.loads(request.data)
    userid=orderslist['userid']
    thisorder=OrderWrapper(userid)
    totalcost=orderslist['total']
    for o in orderslist['items']:
        orderitem=Order(o['item'],o['qty'],o['cost'])
        orderitemjson=json.dumps(orderitem,default=jdefault)
        thisorder.addorder(orderitem)

    db=get_request_connection()
    cursor=db.cursor()
    cursor.execute("insert into orders(userid,status,orderObject,totalcost) values(%s,%s,%s,%s);",(userid,1,json.dumps(thisorder,default=jdefault),totalcost))
    db.commit()
    result = send_data.send('add',abc=123)
    return Response(status=200)

@app.route('/history/<userid>',methods=['GET'])
def history(userid):
	db=get_request_connection()
	cursor=db.cursor()
	status=""
	query='select * from orders where userid={}'.format(userid)
	cursor.execute(query)
	count=1
	orderlist=defaultdict(list)
	rows=cursor.fetchall()
	if len(rows)<1:
		return Response(json.dumps({"status":"invalid user id"}),status=200)
	for r in rows:
		g=OrderedDict()
		g["orderid"]=count
		g["items"]=eval(r[4])['items']
		g["status"]=r[3]
		count+=1
		orderlist["orders"].append(g)
	orderlist["userid"]=userid
	return Response(json.dumps(orderlist,indent=4),status=200,mimetype='application/json')



@app.route('/checkorder',methods=['GET'])
def checkorder():
    check.send('add',abc=123)
    return Response(status=200)

@check.connect
@send_data.connect
def receive_data(sender, **kw):
    db=get_request_connection()
    cur=db.cursor()
    cur.execute("select orderid,userid,time,totalcost,orderObject from orders where status=1;")
    l=cur.fetchall()
    k=[]
    if l<0:
        return "No pending orders"
    total=0
    k=OrderedDict()
    for i,r in enumerate(l):
        total+=int(r[3])
        g=OrderedDict()
        g['orderid']=int(r[0])
        g['items'].append(eval(r[4]))
        if total>=25:
            break
        print json.dumps(g)    
    print total

if __name__ == '__main__':
  app.debug = True
  app.run(host='0.0.0.0', port=80)
