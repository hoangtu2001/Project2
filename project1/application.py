import os

from flask import Flask, session, request, render_template, redirect, url_for, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import psycopg2
import requests
import json
from flask import jsonify
from datetime import timedelta

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#login 
@app.route('/')
def login():
    if 'name' in session:
        flash('Already Signed in')
        return redirect(url_for('admin'))
    else:
        return render_template('signin.html')

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == 'POST':
        # get user info from input
        email = request.form['email']
        password = request.form['password']

        # check if password match with database
        check_user = db.execute("select * from public.users where email = :email", {'email' : email}).fetchone()

        if check_user: 
            list = []
            for i in check_user:
               list.append(i)

            check_name = list[0]
            check_email = list[1]
            check_pass = list[2]
            check_date = list[3]
            if check_email == email and check_pass == password:
                session.permanent = True
                session['name'] = check_name
                session['password'] = check_pass
                session['email'] = check_email
                session['date'] = check_date
                flash('Signed successfully')
                return redirect(url_for('admin'))
            else:
                flash('User name or password is incorrect')
                return redirect(url_for('login'))
        else:
            flash('You are not registed in this website. Please register first.')
            return redirect(url_for('register'))
    else:
        flash('Sign In First')
        return redirect(url_for('login'))
    


@app.route('/register' , methods = ['POST','GET'])
def register():
   if request.method == 'POST':
      # get info from user input
      name = request.form['signupName']
      email = request.form['signupEmail']
      password = request.form['signupPassword']

      #check if the email is already in the table 
      check_user = db.execute("select * from public.users where email = :email", {'email' : email}).fetchall()
      
      if check_user:
         flash('You are already registed.')
         return redirect(url_for('login'))
      else :
         # add a new user in database
         db.execute("INSERT INTO public.users (name, email, password) VALUES (:name, :email , :password)", {
            "name":name, "email":email, "password":password})
         db.commit()

         #save the data in session
         session['name'] = name
         session['email'] = email
         session['password'] = password

         flash('Registraion successful')
         return redirect(url_for('admin'))
   else:
      if 'name' in session:
         flash('You are Already registered ')
         return redirect(url_for('admin'))
      else:
         return render_template('register.html')


@app.route('/book', methods=['GET', 'POST'])
def search():
    if request.method == "POST":
        title = request.form['byTitle']
        title = title.title()
        author = request.form['byAuthor']
        author = author.capitalize()
        year = request.form['byYear']
        isbn = request.form['byIsbn']

        list = []
        text = None
        baseUrl = request.base_url
        if title:
            result = db.execute(" SELECT * FROM books WHERE title LIKE '%"+title+"%' ;").fetchall()
            text = title
        elif author:
            result = db.execute(" SELECT * FROM books WHERE author LIKE '%"+author+"%' ;").fetchall()
            text = author
        elif year:
            result = db.execute(" SELECT * FROM books WHERE year = :year", {'year':year}).fetchall()
            text = year
        else:
            result = db.execute(" SELECT * FROM books WHERE isbn LIKE '%"+isbn+"%' ;").fetchall()
            text = isbn

        #if found then save it in list 
        if result: 
            for i in result : 
                list.append(i)
            itemsCount = len(list)
            return render_template('search.html', baseUrl = baseUrl,  items = list, msg = "Yei ! Search result found", text = text , itemsCount = itemsCount)
            
        #if not found show a not found message
        else:
            return render_template('search.html', msgNo = "Sorry! No books found" , text = text)


   
    return render_template ('search.html')



@app.route("/signout")
def signout():
    if 'name' in session:
        session.pop('name', None)
        session.pop('email', None)
        session.pop('password', None)

        flash('Signed out successfully', 'info')
        return redirect(url_for('login'))
    else:
        flash('Already Singed out')
        return  redirect(url_for('login'))


@app.route('/admin')
def admin():
    if 'email' in session:    
        email = session['email']   
        db_user_query = db.execute("select * from public.users where email = :email", {'email': email}).fetchall()
        db_review_query = db.execute(" select * from public.reviews where email = :email", {'email' : email}).fetchall()
        # root = request.url_root()
        userInfo = {
            'name': db_user_query[0][0], 
            'email': session['email'],
            'password': db_user_query[0][2],
            'date': db_user_query[0][3]
        }
        reviewCount = len(db_review_query)


        return render_template('admin.html', userInfo = userInfo, reviewedbooks = db_review_query , reviewCount= reviewCount )

    else: 
        flash('Sign first')
        return redirect(url_for('login'))





@app.route('/book/<string:isbn>', methods = ['GET', 'POST'])
def singleBook(isbn):

    isbn = isbn
    email = session['email']
    


    apiCall = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Um008J1spJX9PAksIxqjmg", "isbns": isbn })
    apidata = apiCall.json()
    dbdata = db.execute(" SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    dbreviews = db.execute('SELECT * FROM reviews WHERE isbn = :isbn', {'isbn': isbn}).fetchall()

    alreadyHasReview = db.execute('SELECT * FROM public.reviews WHERE isbn = :isbn and email = :email ', {'isbn': isbn, 'email': email}).fetchall()
    if request.method == 'POST':
        if alreadyHasReview: 
            flash('You alreaddy submitted a review on this book')
        else : 
            rating = int(request.form['rating'])
            comment = request.form['comment']
            email = session['email']
            fisbn = request.form['isbn']
            db.execute("INSERT into public.reviews (email, rating, comment, isbn) Values (:email, :rating, :comment, :isbn)", {'email': email, 'rating': rating, 'comment': comment, 'isbn': fisbn})
            db.commit()
            flash('Awesome, Your review added successfully ')
    
    if apiCall:
        return render_template('singlebook.html', apidata = apidata, dbdata = dbdata, dbreviews = dbreviews, isbn = isbn )
    else:
        flash('Data fetch failed')
        return render_template('singlebook.html')

    
       
@app.route("/book/api/<string:isbn>")
def api(isbn):
    if 'email' in session: 
        data=db.execute("SELECT * FROM public.books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
        if data==None:
            return render_template('404.html')
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Um008J1spJX9PAksIxqjmg", "isbns": isbn})
        average_rating=res.json()['books'][0]['average_rating']
        work_ratings_count=res.json()['books'][0]['work_ratings_count']
        x = {
        "title": data.title,
        "author": data.author,
        "year": data.year,
        "isbn": isbn,
        "review_count": work_ratings_count,
        "average_rating": average_rating
        }
        # api=json.dumps(x)
        # return render_template("api.json",api=api)
        return  jsonify(x)


@app.errorhandler(404)
def page_not_found():
    return render_template("404.html"), 404





if __name__ == '__main__':
    app.run(debug =True)