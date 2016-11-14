#!/usr/bin/env python2.7

"""
Columbia W4111 Project 1
Alimentos - Restaurant Ratings App

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# Creates database engine and connects to URI
DATABASEURI = "postgresql://na2603:xs3d4@104.196.175.120/postgres"
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None


@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """
  logged_in = False
  if 'username' in session:
      logged_in = True

  # DEBUG: this is debugging code to see what request looks like
  # print request.args

  context = dict(data = logged_in)
  return render_template("index.html", **context)


@app.route('/restaurants/')
def restaurants():
   cursor = g.conn.execute("SELECT avg(stars),Restaurants.rid,name,city,state,address,postalCode from Ratings RIGHT OUTER JOIN Restaurants ON Ratings.rid=Restaurants.rid GROUP BY Restaurants.rid")
   restaurants = {}
   for result in cursor:
     if result['avg'] != None:
         avg= ("%.2f" % round(result['avg'],2))
     else:
         avg='None'
     location = result['address'] + ', ' + result['city'] + ', ' + result['state'] + ' ' + str(result['postalcode'])
     key = '/restaurants/' + str(result['rid'])
     restaurants[key]=[result['name'], location, avg]
   cursor.close()
   context = dict(data = restaurants)
   return render_template("restaurants.html", **context)


@app.route('/restaurants/<rid>/')
def restaurantInfo(rid):
    cmd = "SELECT Restaurants.rid, name, address, city, state, postalCode, category,avg(stars) from Ratings RIGHT OUTER JOIN Restaurants ON Ratings.rid=Restaurants.rid WHERE Restaurants.rid=:rid GROUP BY Restaurants.rid"
    cursor=g.conn.execute(text(cmd), rid=rid);
    for result in cursor:
        if result['avg'] != None:
            avg= ("%.2f" % round(result['avg'],2))
        else:
            avg='None'
        location = result['address'] + ', ' + result['city'] + ', ' + result['state'] + ' ' + str(result['postalcode'])
        restaurantInfo = [result['name'],location,result['category'],avg]
    cursor.close()

    cmd= "SELECT name,count(username) FROM favDishes WHERE rid=:rid GROUP BY name"
    cursor=g.conn.execute(text(cmd), rid=rid);
    favDishes={}
    for result in cursor:
        favDishes[result['name']]=result['count']
    cursor.close()

    cmd= "SELECT * from ratingPhotos RIGHT OUTER JOIN Ratings ON Ratings.raid=ratingPhotos.raid where rid=:rid"
    cursor=g.conn.execute(text(cmd), rid=rid);
    ratings=[]
    for result in cursor:
        ratings.append(result)
    cursor.close()

    context = dict(data = [restaurantInfo,favDishes,ratings])
    return render_template("restaurantInfo.html", **context)


@app.route('/users/')
def users():
    if 'username' in session:
        cursor = g.conn.execute("SELECT firstName,lastName,username FROM Users")
        users = {}
        for result in cursor:
          if (result["username"]!=session['username']):
              users[result["username"]]=(result[0] + ' ' + result[1])
        cursor.close()

        cmd = "SELECT destination FROM Follows WHERE Follows.source=:username"
        cursor = g.conn.execute(text(cmd), username=session['username'])
        following = []
        for result in cursor:
            following.append(result['destination'])
        cursor.close()

        context = dict(data = [users, following])
        return render_template("users.html", **context)
    else:
        return redirect('/login')


@app.route('/follow/', methods=['POST'])
def follow():
    destination=request.form['destination']
    cmd= "INSERT INTO Follows(source,destination) VALUES(:username, :destination)"
    g.conn.execute(text(cmd), username=session['username'], destination=destination)
    return redirect('/users')


@app.route('/mydetails/')
def mydetails():
  if 'username' in session:
      username = session['username']
      cmd = "SELECT firstName,lastName from Users WHERE Users.username=:username"
      cursor = g.conn.execute(text(cmd), username=username)
      result = cursor.fetchone()
      name = result[0] + " " + result[1]
      cursor.close()

      cmd = "SELECT source FROM Follows WHERE destination=:username"
      cursor = g.conn.execute(text(cmd), username=username);
      followers=[]
      for result in cursor:
          followers.append(result["source"])
      cursor.close()

      cmd = "SELECT destination FROM Follows WHERE source=:username"
      cursor = g.conn.execute(text(cmd), username=username);
      following=[]
      for result in cursor:
          following.append(result["destination"])
      cursor.close()

      cmd = "SELECT Ratings.raid, name, address, city, state, postalCode,stars,comment,caption,photoUrl from Ratings JOIN Restaurants ON Ratings.rid=Restaurants.rid LEFT OUTER JOIN ratingPhotos ON Ratings.raid=ratingPhotos.raid WHERE Ratings.username=:username"
      cursor=g.conn.execute(text(cmd), username=session['username']);
      ratings={}
      for result in cursor:
          location = result['address'] + ', ' + result['city'] + ', ' + result['state'] + ' ' + str(result['postalcode'])
          ratings[result['raid']] = [result['name'],location,result['stars'],result['comment'],result['caption'],result['photourl']]
      cursor.close()

      cmd= "SELECT favDishes.name AS fname,Restaurants.name AS rname FROM favDishes,Restaurants WHERE favDishes.rid=Restaurants.rid AND username=:username"
      cursor=g.conn.execute(text(cmd), username=session['username']);
      favDishes=[]
      for result in cursor:
          favDishes.append([result['rname'],result['fname']])
      cursor.close()

      context = dict(data = [name,followers,following, len(followers), len(following), favDishes,ratings])
      return render_template("mydetails.html", **context)
  else:
      return redirect('/login')

# Example of inserting into database that needs to be fixed
@app.route('/add/', methods=['POST'])
def add():
  restaurantCount = restaurantCount + 1
  name = request.form['name']
  lat = request.form['latitude']
  lon = request.form['longitude']
  cmd = 'INSERT INTO Restaurants(rid, name, rlocation) VALUES (:rid, :name, point(:lat,:lon))';
  g.conn.execute(text(cmd),rid = restaurantCount, name = name, lat = latitude, lon = longitude);
  return redirect('/')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    else:
        username= request.form['username']
        password= request.form['password']

        cmd= "SELECT username,password FROM Users WHERE username=:username AND password=md5(:password)"
        cursor=g.conn.execute(text(cmd), username=username, password=password);
        if(cursor.fetchone()):
            session['username'] = username
            return redirect('/')
        else:
            return redirect('/login')


@app.route('/logout/')
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/newuser/', methods=['GET', 'POST'])
def newuser():
    if request.method == 'GET':
        return render_template("newuser.html")
    else:
        newusername = request.form['username']
        password = request.form['password']
        firstName = request.form['firstname']
        lastName = request.form['lastname']

        cmd = "SELECT username FROM Users WHERE username=:newusername"
        cursor = g.conn.execute(text(cmd), newusername=newusername)
        matches = []
        for result in cursor:
            matches.append(result['username'])
        cursor.close()
        if len(matches)>0:
            return redirect('/newuser')
        else:
            cmd= "INSERT INTO Users(username, password, firstname, lastname) VALUES(:username, md5(:password), :firstName, :lastName)"
            cursor=g.conn.execute(text(cmd), username=username, password=password, firstName=firstName, lastName=lastName);
            return redirect('/')


if __name__ == "__main__":
  import click
  app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
