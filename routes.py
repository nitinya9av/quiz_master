from flask import render_template, request, flash, redirect, url_for, session
from app import app
from models import db, User, Subject, Chapter, Quiz, Question, Score
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import time
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
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
    
    current_date = datetime.now().date()
    upcoming_quizes = Quiz.query.filter(Quiz.date_of_quiz >= current_date).all()
    return render_template('index.html', user=user, upcoming_quizes=upcoming_quizes, current_date=current_date)


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


@app.route('/admin/search')
@admin_required
def admin_search():
    user = User.query.get(session['user_id'])
    query = request.args.get('query', '')
    
    if query:
        chapters = Chapter.query.filter(
            (Chapter.name.ilike(f'%{query}%')) |
            (Chapter.description.ilike(f'%{query}%'))
        ).all()
        
        chapter_quizzes = []
        for chapter in chapters:
            chapter_quizzes.extend(chapter.quizzes)
        
        results = {
            'users': User.query.filter(
                (User.username.ilike(f'%{query}%')) | 
                (User.full_name.ilike(f'%{query}%'))
            ).limit(20).all(),
            'subjects': Subject.query.filter(
                (Subject.name.ilike(f'%{query}%')) |
                (Subject.description.ilike(f'%{query}%'))
            ).all(),
            'chapters': chapters,
            'quizzes': chapter_quizzes,
            'questions': Question.query.filter(
                (Question.question_statement.ilike(f'%{query}%')) |
                (Question.question_title.ilike(f'%{query}%'))
            ).all()
        }
    else:
        results = {
            'users': [],
            'subjects': [],
            'chapters': [],
            'quizzes': [],
            'questions': []
        }
    
    return render_template('search.html', user=user, results=results, query=query)



@app.route('/search')
def user_search():
    user = User.query.get(session['user_id'])
    query = request.args.get('query', '')
    
    if query:
        subjects = Subject.query.filter(
            (Subject.name.ilike(f'%{query}%')) |
            (Subject.description.ilike(f'%{query}%'))
        ).all()

        subject_quizzes = []
        for subject in subjects:
            for chapter in subject.chapters: subject_quizzes.extend(chapter.quizzes)

        results = {
            'subjects': subjects,
            'quizzes': subject_quizzes,
        }
    else:
        results = {
            'subjects': [],
            'quizzes': [],
        }
    
    return render_template('user/search.html', user=user, results=results, query=query)


@app.route('/scores')
@auth_required
def scores():
    user = User.query.get(session['user_id'])
    
    scores = Score.query.filter_by(user_id=user.id).order_by(
        Score.time_stamp_of_attempt.desc()
    ).all()
    
    quiz_summary = {}
    for score in scores:
        if score.quiz_id not in quiz_summary:
            quiz_summary[score.quiz_id] = {
                'best_score': score.total_scored,
                'total_attempts': 1,
                'latest_attempt': score.time_stamp_of_attempt,
                'quiz': score.quiz
            }
        else:
            quiz_summary[score.quiz_id]['total_attempts'] += 1
            if score.total_scored > quiz_summary[score.quiz_id]['best_score']:
                quiz_summary[score.quiz_id]['best_score'] = score.total_scored

    total_quizzes = len(quiz_summary)
    total_questions = sum(len(score.quiz.questions) for score in scores)
    total_correct = sum(score.total_scored for score in scores)

    return render_template('scores.html',
        user=user,
        quiz_summary=quiz_summary.values(),
        total_quizzes=total_quizzes,
        total_questions=total_questions,
        total_correct=total_correct,
        scores=scores
    )


@app.route('/admin/summary')
@admin_required
def admin_summary():
    user = User.query.get(session['user_id'])
    # Fetch subjects and their related data
    subjects = Subject.query.all()
    
    # Prepare data for charts
    subject_names = []
    best_scores = []
    total_attempts = []

    for subject in subjects:
        subject_names.append(subject.name)
        
        # Calculate best score for each subject
        quizzes = [quiz.id for chapter in subject.chapters for quiz in chapter.quizzes]
        scores = Score.query.filter(Score.quiz_id.in_(quizzes)).all()
        if scores:
            best_scores.append(max(score.total_scored for score in scores))
        else:
            best_scores.append(0)

        # Calculate total attempts for each subject
        total_attempts.append(len(scores))

    # Create bar chart for best scores
    plt.figure(figsize=(8, 6))
    plt.bar(subject_names, best_scores, color='skyblue')
    plt.title('Best Scores Achieved Subject-wise', fontsize=14)
    plt.xlabel('Subjects', fontsize=12)
    plt.ylabel('No. of times Best Score Achieved', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save bar chart to static/images directory
    output_dir = os.path.join(app.root_path, 'static', 'images')
    os.makedirs(output_dir, exist_ok=True)
    bar_chart_path = os.path.join(output_dir, 'best_scores_bar_chart.png')
    plt.savefig(bar_chart_path)
    plt.close()

    # Create pie chart for total attempts
    plt.figure(figsize=(8, 6))
    plt.pie(total_attempts, labels=subject_names, autopct='%1.1f%%', startangle=140,
            colors=['gold', 'lightcoral', 'lightskyblue', 'lightgreen', 'violet'])
    plt.title('Total Quiz Attempts Subject-wise', fontsize=14)

    # Save pie chart to static/images directory
    pie_chart_path = os.path.join(output_dir, 'quiz_attempts_pie_chart.png')
    plt.savefig(pie_chart_path)
    plt.close()

    return render_template('summary.html', user=user)


@app.route('/summary')
@auth_required
def user_summary():
    user = User.query.get(session['user_id'])
    scores = Score.query.filter_by(user_id=user.id).all()
    
    # Prepare data for charts
    subjects = {}
    for score in scores:
        subject = score.quiz.chapter.subject.name
        if subject not in subjects:
            subjects[subject] = {'total_score': 0, 'attempts': 0}
        subjects[subject]['total_score'] += score.total_scored
        subjects[subject]['attempts'] += 1

    # Create bar chart for average scores
    subject_names = list(subjects.keys())
    average_scores = [subjects[subject]['total_score'] / subjects[subject]['attempts'] for subject in subject_names]

    plt.figure(figsize=(8, 6))
    plt.bar(subject_names, average_scores, color='skyblue')
    plt.title('Average Scores by Subject', fontsize=14)
    plt.xlabel('Subjects', fontsize=12)
    plt.ylabel('Average Score', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save bar chart to static/images directory
    output_dir = os.path.join(app.root_path, 'static', 'images')
    os.makedirs(output_dir, exist_ok=True)
    bar_chart_path = os.path.join(output_dir, f'user_{user.id}_average_scores_bar_chart.png')
    plt.savefig(bar_chart_path)
    plt.close()

    # Create pie chart for total attempts
    total_attempts = [subjects[subject]['attempts'] for subject in subject_names]
    plt.figure(figsize=(8, 6))
    plt.pie(total_attempts, labels=subject_names, autopct='%1.1f%%', startangle=140,
            colors=['gold', 'lightcoral', 'lightskyblue', 'lightgreen', 'violet'])
    plt.title('Total Attempts by Subject', fontsize=14)

    # Save pie chart to static/images directory
    pie_chart_path = os.path.join(output_dir, f'user_{user.id}_total_attempts_pie_chart.png')
    plt.savefig(pie_chart_path)
    plt.close()

    return render_template('user/summary.html', 
                           user=user, 
                           bar_chart=f'images/user_{user.id}_average_scores_bar_chart.png',
                           pie_chart=f'images/user_{user.id}_total_attempts_pie_chart.png')


@app.route('/subject/add', methods=['GET', 'POST'])
@admin_required
def add_subject():
    user = User.query.get(session['user_id'])
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
    return render_template('subject/add.html', user=user)


@app.route('/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_subject(subject_id):
    user = User.query.get(session['user_id'])
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
    return render_template('subject/edit.html', user=user, subject=Subject.query.get(subject_id))


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
    user = User.query.get(session['user_id'])
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
    return render_template('chapter/add.html', user=user)


@app.route('/subject/<int:subject_id>/chapter/<int:chapter_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_chapter(subject_id, chapter_id):
    user = User.query.get(session['user_id'])
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
    return render_template('chapter/edit.html', user=user, chapter=Chapter.query.get(chapter_id))


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
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        hours = int(request.form['hours'])
        minutes = int(request.form['minutes'])
        total_duration = hours * 60 + minutes
        description = request.form.get('description')
        if not chapter_id or not date or not total_duration:
            flash('Please fill required fields')
            return redirect(url_for('add_quiz'))
        
        quiz = Quiz(chapter_id=chapter_id, date_of_quiz=date, time_duration=total_duration, remarks=description)
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz added successfully')
        return redirect(url_for('quiz'))
    chapters = Chapter.query.all()
    return render_template('quiz/add.html', user=user, chapters=chapters)


@app.route('/quiz/<int:quiz_id>')
@auth_required
def show_quiz( quiz_id ):
    return render_template('quiz/details.html', quiz=Quiz.query.get(quiz_id), user=User.query.get(session['user_id']))


@app.route('/quiz/<int:quiz_id>/attempt', methods=['GET', 'POST'])
@auth_required
def attempt_quiz(quiz_id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get(quiz_id)

    if quiz.date_of_quiz > datetime.now().date():
        flash('This quiz is not available yet')
        return redirect(url_for('index'))

    if 'quiz_data' not in session:
        session['quiz_data'] = {
            'start_time': time.time(),
            'answers': {},
            'duration': quiz.time_duration
        }
        session.modified = True

    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('answer_'):
                question_id = key.split('_')[1]
                session['quiz_data']['answers'][question_id] = value
        session.modified = True
        
        time_elapsed = time.time() - session['quiz_data']['start_time']
        if time_elapsed > quiz.time_duration * 60:  # Convert minutes to seconds
            return redirect(url_for('submit_quiz', quiz_id=quiz_id))

        if 'submit_button' in request.form:
            return redirect(url_for('submit_quiz', quiz_id=quiz_id))

    return render_template('quiz/attempt.html',
                           user=user,
                           quiz=quiz,
                           start_time=session['quiz_data']['start_time'])


@app.route('/submit-quiz/<int:quiz_id>')
@auth_required
def submit_quiz(quiz_id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get(quiz_id)
    
    if 'quiz_data' not in session:
        flash('No quiz data found')
        return redirect(url_for('index'))
    

    quiz_data = session.pop('quiz_data', None)
    score = 0
    time_taken = time.time() - quiz_data['start_time']
    
    for question in quiz.questions:
        user_answer = quiz_data['answers'].get(str(question.id))
        if user_answer and user_answer == question.answer:
            score += 1

    if time_taken > quiz.time_duration:
        time_taken = quiz.time_duration
    
    result = Score(
        user_id=user.id,
        quiz_id=quiz_id,
        total_scored=score,
        time_stamp_of_attempt=datetime.now(),
    )
    db.session.add(result)
    db.session.commit()
    
    return redirect(url_for('quiz_result', quiz_id=quiz_id, score_id=result.id))


@app.route('/quiz/<int:quiz_id>/result/<int:score_id>')
@auth_required
def quiz_result(quiz_id, score_id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get(quiz_id)
    score = Score.query.get(score_id)
    return render_template('quiz/result.html', user=user, quiz=quiz, score=score)


@app.route('/quiz/<int:quiz_id>/edit', methods=[ 'GET','POST'])
@admin_required
def edit_quiz( quiz_id ):
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        hours = int(request.form['hours'])
        minutes = int(request.form['minutes'])
        total_duration = hours * 60 + minutes
        remarks = request.form.get('description')
        if not chapter_id or not date or not total_duration:
            flash('Please fill required fields')
            return redirect(url_for('quiz/edit.html', quiz_id=quiz_id))
        quiz = Quiz.query.get(quiz_id)
        quiz.chapter_id = chapter_id
        quiz.date_of_quiz = date
        quiz.time_duration = total_duration
        quiz.remarks = remarks
        db.session.commit()
        flash('Quiz updated successfully')
        return redirect(url_for('quiz'))
    return render_template('quiz/edit.html', user=user, quiz=Quiz.query.get(quiz_id))


@app.route('/quiz/<int:quiz_id>/delete')
@admin_required
def delete_quiz( quiz_id, ):
    quiz = Quiz.query.get(quiz_id)
    if quiz.questions:
        flash('Quiz has questions! Delete them first.')
        return redirect(url_for('quiz'))
    
    # Delete associated scores
    Score.query.filter_by(quiz_id=quiz_id).delete()
    
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz and its associated scores deleted successfully.')
    return redirect(url_for('quiz'))


@app.route('/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@admin_required
def add_question(quiz_id):
    user = User.query.get(session['user_id'])
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
    return render_template('question/add.html', user=user, quiz=quiz)


@app.route('/quiz/<int:quiz_id>/question/<int:question_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(quiz_id, question_id):
    user = User.query.get(session['user_id'])
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
    return render_template('question/edit.html', user=user, question=question)


@app.route('/quiz/<int:quiz_id>/question/<int:question_id>/delete')
@admin_required
def delete_question(quiz_id, question_id):
    question = Question.query.get(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully')
    return redirect(url_for('quiz', quiz_id=quiz_id))


@app.route('/quiz/summary/<int:quiz_id>')
@auth_required
def quiz_summary(quiz_id):
    user = User.query.get(session['user_id'])
    
    attempts = Score.query.filter_by(
        user_id=user.id,
        quiz_id=quiz_id
    ).order_by(Score.time_stamp_of_attempt.desc()).all()
    
    return render_template('quiz/summary.html',
        user=user,
        quiz=attempts[0].quiz if attempts else None,
        attempts=attempts
    )