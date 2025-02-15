from flask import render_template, request, flash, redirect, url_for, session
from app import app
from models import db, User, Subject, Chapter, Quiz, Question
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

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.is_admin:
            flash('You are not authorized to view this page')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

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
    # GET request
    return render_template('login.html')

@app.route('/register' , methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        dob = request.form.get('dob')
        qualification = request.form.get('qualification')

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
        return redirect(url_for('index'))
    # GET request
    return render_template('register.html')

@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    flash('Logged out successfully')
    return redirect(url_for('login'))


@app.route('/profile' , methods=['GET', 'POST'])
@auth_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        opassword = request.form.get('opassword')
        password = request.form.get('password')
        cpassword = request.form.get('cpassword')

        if not name or not opassword or not password or not cpassword:
            flash('Please fill required fields')
            return redirect(url_for('profile'))
        
        user = User.query.get(session['user_id'])
        if not check_password_hash(user.passhash, opassword):
            flash('Incorrect old password')
            return redirect(url_for('profile'))
        
        if password != cpassword:
            flash('Passwords do not match')
            return redirect(url_for('profile'))
        new_passhash = generate_password_hash(password)

        user.full_name = name
        user.passhash = new_passhash
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('admin') if user.is_admin else url_for('index'))
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@app.route('/admin')
@admin_required
def admin():
    user = User.query.get(session['user_id'])
    subjects = Subject.query.all()
    return render_template('admin.html', user=user, subjects=subjects)

@app.route('/users')
@admin_required
def users():
    users = User.query.all()
    user = User.query.get(session['user_id'])
    return render_template('user/users.html', user=user, users=users)


@app.route('/subject/add', methods=['GET', 'POST'])
@admin_required
def add_subject():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if not name:
            flash('Please fill required fields')
            return redirect(url_for('add_subject'))
        subject = Subject(name=name, description=description)
        db.session.add(subject)
        db.session.commit()
        flash('Subject added successfully')
        return redirect(url_for('admin'))
    return render_template('subject/add.html')


@app.route('/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_subject(subject_id):
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if not name:
            flash('Please fill required fields')
            return redirect(url_for('edit_subject', subject_id=subject_id))
        subject = Subject.query.get(subject_id)
        subject.name = name
        subject.description = description
        db.session.commit()
        flash('Subject updated successfully')
        return redirect(url_for('admin'))
    return render_template('subject/edit.html', subject=Subject.query.get(subject_id))


@app.route('/subject/<int:subject_id>/delete')
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if not subject.chapters:
        db.session.delete(subject)
        db.session.commit()
        flash('Subject deleted successfully')
        return redirect(url_for('admin'))
    flash('Subject has chapters! Delete chapters first.')
    return redirect(url_for('admin'))
    

@app.route('/subject/<int:subject_id>/chapter/add', methods=['GET', 'POST'])
@admin_required
def add_chapter(subject_id):
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if not name:
            flash('Please fill required fields')
            return redirect(url_for('add_chapter', subject_id=subject_id))
        chapter = Chapter(name=name, description=description, subject_id=subject_id)
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter added successfully')
        return redirect(url_for('admin'))
    return render_template('chapter/add.html')


@app.route('/subject/<int:subject_id>/chapter/<int:chapter_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_chapter(subject_id, chapter_id):
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if not name:
            flash('Please fill required fields')
            return redirect(url_for('edit_chapter', subject_id=subject_id, chapter_id=chapter_id))
        chapter = Chapter.query.get(chapter_id)
        chapter.name = name
        chapter.description = description
        db.session.commit()
        flash('Chapter updated successfully')
        return redirect(url_for('admin'))
    return render_template('chapter/edit.html', chapter=Chapter.query.get(chapter_id))


@app.route('/subject/<int:subject_id>/chapter/<int:chapter_id>/delete')
@admin_required
def delete_chapter(subject_id, chapter_id):
    chapter = Chapter.query.get(chapter_id)
    if not chapter.questions and not chapter.quizzes:
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter deleted successfully')
        return redirect(url_for('admin'))
    flash('Chapter has questions or quizzes! Delete them first.')
    return redirect(url_for('admin'))


@app.route('/quiz')
@admin_required
def quiz():
    user = User.query.get(session['user_id'])
    quizes = Quiz.query.all()
    return render_template('quiz/home.html', user=user, quizes=quizes)

@app.route('/quiz/add', methods=['GET', 'POST'])
@admin_required
def add_quiz():
    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        duration = int(request.form['duration']) * 60
        description = request.form.get('description')
        if not chapter_id or not date or not duration:
            flash('Please fill required fields')
            return redirect(url_for('add_quiz'))
        
        quiz = Quiz(chapter_id=chapter_id, date_of_quiz=date, time_duration=duration, remarks=description)
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz added successfully')
        return redirect(url_for('quiz'))
    chapters = Chapter.query.all()
    return render_template('quiz/add.html', chapters=chapters)


@app.route('/quiz/<int:quiz_id>')
@admin_required
def show_quiz( quiz_id ):
    return render_template('quiz/details.html', quiz=Quiz.query.get(quiz_id), user=User.query.get(session['user_id']))

@app.route('/quiz/<int:quiz_id>/edit', methods=[ 'GET','POST'])
@admin_required
def edit_quiz( quiz_id ):
    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        duration = int(request.form['duration']) * 60
        remarks = request.form.get('description')
        if not chapter_id or not date or not duration:
            flash('Please fill required fields')
            return redirect(url_for('quiz/edit.html', quiz_id=quiz_id))
        quiz = Quiz.query.get(quiz_id)
        quiz.chapter_id = chapter_id
        quiz.date_of_quiz = date
        quiz.time_duration = duration
        quiz.remarks = remarks
        db.session.commit()
        flash('Quiz updated successfully')
        return redirect(url_for('quiz'))
    return render_template('quiz/edit.html', quiz=Quiz.query.get(quiz_id))


@app.route('/quiz/<int:quiz_id>/delete')
@admin_required
def delete_quiz( quiz_id, ):
    quiz = Quiz.query.get(quiz_id)
    if not quiz.questions:
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully')
        return redirect(url_for('quiz'))
    flash('Quiz has questions! Delete them first.')
    return redirect(url_for('quiz'))


@app.route('/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@admin_required
def add_question(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if request.method == 'POST':
        chapter_id = quiz.chapter_id
        tquestion = request.form.get('tquestion')
        question = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        answer = request.form.get('answer')

        if not tquestion or not question or not option1 or not option2 or not option3 or not option4 or not answer:
            flash('Please fill required fields')
            return redirect(url_for('add_question', quiz_id=quiz_id))

        new_question = Question(chapter_id=chapter_id, quiz_id=quiz_id, question_title=tquestion, question_statement=question, option1=option1, option2=option2, option3=option3, option4=option4, answer=answer)
        db.session.add(new_question)
        db.session.commit()

        flash('Question added successfully')
        return redirect(url_for('quiz', quiz_id=quiz_id))
    return render_template('question/add.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/question/<int:question_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(quiz_id, question_id):
    question = Question.query.get(question_id)
    if request.method == 'POST':
        tquestion = request.form.get('tquestion')
        squestion = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        answer = request.form.get('answer')

        if not tquestion or not question or not option1 or not option2 or not option3 or not option4 or not answer:
            flash('Please fill required fields')
            return redirect(url_for('question/edit.html', quiz_id=quiz_id, question_id=question_id))

        question.question_title = tquestion
        question.question_statement = squestion
        question.option1 = option1
        question.option2 = option2
        question.option3 = option3
        question.option4 = option4
        question.answer = answer
        db.session.commit()

        flash('Question updated successfully')
        return redirect(url_for('quiz', quiz_id=quiz_id))
    return render_template('question/edit.html', question=question)


@app.route('/quiz/<int:quiz_id>/question/<int:question_id>/delete')
@admin_required
def delete_question(quiz_id, question_id):
    question = Question.query.get(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully')
    return redirect(url_for('quiz', quiz_id=quiz_id))