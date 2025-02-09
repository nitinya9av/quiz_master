from flask import render_template, request, flash, redirect, url_for, session
from app import app
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps


def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to continue')
            return redirect(url_for('login'))
    return wrapper    


@app.route('/')
@auth_required
def index():
    user = User.query.get(session['user_id'])
    if user.is_admin:
        return redirect(url_for('admin'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Please fill required fields')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.passhash, password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        flash('Logged in successfully')
        return redirect(url_for('index'))


@app.route('/register' , methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        dob = request.form['dob']
        qualification = request.form['qualification']

        if not name or not username or not password or not confirm_password:
            flash('Please fill required fields')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        

        password_hash = generate_password_hash(password)

        if dob:
            dob = datetime.strptime(dob, '%Y-%m-%d').date()
        else:
            dob = None
        
        if not qualification:
            qualification = None

        new_user = User(full_name=name, username=username, passhash=password_hash, date_of_birth=dob, qualification=qualification)
        db.session.add(new_user)
        db.session.commit()

        flash('User registered successfully')
        return redirect(url_for('login'))

@app.route('/admin')
@auth_required
def admin():
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('You are not authorized to view this page')
        return redirect(url_for('index'))
    return render_template('admin.html')
    