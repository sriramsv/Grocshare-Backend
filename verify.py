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
from flask import render_template,flash
from flask import request,session,g
import httplib2
import oauth2client.client
from oauth2client.crypt import AppIdentityError
from oauth2client.client import verify_id_token
import MySQLdb
from gcm import *
from orderclass import Order,OrderWrapper,jdefault,JsonLoad
from google.appengine.api import mail
import jinja2
import requests
APPLICATION_NAME = 'Grocshare'
app = Flask(__name__)
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
						 for x in range(32))


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Update client_secrets.json with your Google API project information.
# Do not change this assignment.
CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']
INSTANCE_NAME="grocshare-0408:grocshare-db"
API_KEY = json.loads(open('gcm_id.json', 'r').read())['api_key']

# Start the scheduler

send_data = signal('addorder')
check = signal('checkorder')

def sendmergedorder(mergelist=None,total=0):
    # send_email("vendor",mergelist)
    for items in mergelist:
        send_email("user",items)
        userid=items['userid']
        send_gcm(userid=userid,message="your order has been completed")

def send_email(whom,order):
    db=get_request_connection()
    cur=db.cursor()
    if whom=="user":
        print order
        userid=order['userid']
        # print order
        items=order['items']
        d1={"items":items}
        query="""select username,email from userlist where userid={};""".format(userid)
        cur.execute(query);
        d = cur.fetchone()
        username=d[0]
        email=d[1]
        d1['username']=username
        template = JINJA_ENVIRONMENT.get_template('userorder.html')
        subject="Grocshare Order Details"
        message = mail.EmailMessage(sender="Grocshare New Order Confirmation <sharegroc@gmail.com>",subject=subject)
        message.to = email
        message.html=template.render(d1)
        message.send()

    # elif whom=="vendor":
    #     email="sriramsv1991@gmail.com"
    #     subject="Grocshare Order Details"
    #     message = mail.EmailMessage(sender="Grocshare New Order Confirmation <sharegroc@gmail.com>",subject=subject)
    #     # template = JINJA_ENVIRONMENT.get_template('vendor.html')
    #     message.to = email
    #     a=OrderedDict()
    #     for o in order:
    #         d=OrderedDict()
    #         query="select username,email from userlist where userid={};".format(o['userid'])
    #         cur.execute(query)
    #         d['orders'].append(order['items'])
    #         l=cur.fetchone()
    #         d['username']=l[0]
    #         d['email']=l[1]
    #         d['items']=o['items']
    #         a['orders'].append(d)
    #     print a
    #     # html=template.render(a)
    #     # message.html = html
    #     message.send()

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
    userid=orderslist['userID']
    thisorder=OrderWrapper(userid)
    totalcost=orderslist['total']

    for o in orderslist['items']:
        orderitem=Order(o['item'],o['qty'],o['cost'])
        orderitemjson=json.dumps(orderitem,default=jdefault)
        thisorder.addorder(orderitem)

    db=get_request_connection()
    cursor=db.cursor()
    if totalcost>=25:
        cursor.execute("insert into orders(userid,status,orderObject,totalcost) values(%s,%s,%s,%s);",(userid,"completed",json.dumps(thisorder,default=jdefault),totalcost))
        send_email('user',thisorder.__dict__)
        send_gcm(userid=userid,message="your order has been completed")
    else:
        cursor.execute("insert into orders(userid,status,orderObject,totalcost) values(%s,%s,%s,%s);",(userid,"pending",json.dumps(thisorder,default=jdefault),totalcost))
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
        g["total"]=float(r[5])
        count+=1
    orderlist["orders"].append(g)
    orderlist["userid"]=userid
    return Response(json.dumps(orderlist,indent=4),status=200,mimetype='application/json')




@app.route('/checkemail',methods=['GET'])
def checkemail():
    return Response(status=200)

@app.route('/checkorder',methods=['GET'])
def checkorder():
    res=check.send('add',abc=123)
    return Response(json.dumps({"status":res[0][1]}),status=200)

@check.connect
@send_data.connect
def receive_data(sender, **kw):
    db=get_request_connection()
    cur=db.cursor()
    cur.execute("select orderid,userid,time,totalcost,orderObject from orders where status='pending';")
    l=cur.fetchall()
    print len(l)
    if len(l)<1:
        return "No pending orders"
    total=0
    k=[]
    orders=[]
    for i,r in enumerate(l):
        total=total+float(r[3])
        orders.append(int(r[0]))
        k.append(json.loads(r[4]))
        if total>=25:
            sendmergedorder(k,total)
            changestatus(orders)
            break



def changestatus(orders):
    for o in orders:
        db=get_request_connection()
        cur=db.cursor()
        query="""update orders set status='completed' where orderid={} and status='pending';""".format(o)
        cur.execute(query)
        db.commit()

@app.route('/gcmregister',methods=['POST'])
def gcmregister():
    data=json.loads(request.data)
    print data
    reg_id = data['regID']
    userid = data['userID']
    db=get_request_connection()
    cur=db.cursor()
    query="""update userlist set regID='{}' where userid={};""".format(reg_id,userid)
    cur.execute(query)
    db.commit()
    return "registration successful",200



def send_gcm(userid,message):
    gcm = GCM(API_KEY)
    db=get_request_connection()
    cursor=db.cursor()
    l=cursor.execute("""select regID from userlist where userid={};""".format(userid))
    reg_id=cursor.fetchone()
    data = {'message':message}
    gcm.plaintext_request(registration_id=reg_id, data=data)



if __name__ == '__main__':
  app.debug = True
  app.run(host='0.0.0.0', port=80)
