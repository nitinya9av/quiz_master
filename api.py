from flask import request, session
from flask_restful import Resource, Api
from app import app
from models import db, User, Subject, Chapter, Quiz, Score
from werkzeug.security import check_password_hash
from routes import admin_required

api = Api(app)


class LoginApi(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'error': 'Please provide username and password'}, 400
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.passhash, password):
            return {'error': 'Invalid username or password'}, 401
        
        session['user_id'] = user.id
        
        return {
            'success': True, 
            'user_id': user.id,
            'is_admin': user.is_admin
        }

api.add_resource(LoginApi, '/api/login')


class SubjectApi(Resource):
    @admin_required
    def get(self, subject_id=None):
        if subject_id:
            subject = Subject.query.get(subject_id)
            if not subject:
                return {'error': 'Subject not found'}, 404
            return {
                'id': subject.id,
                'name': subject.name,
                'description': subject.description
            }
        else:
            subjects = Subject.query.all()
            return {'subjects': [
                {
                    'id': subject.id,
                    'name': subject.name,
                    'description': subject.description
                } for subject in subjects
            ]}

    @admin_required
    def post(self):
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        
        if not name:
            return {'error': 'Please fill required fields'}, 400
            
        subject = Subject(name=name, description=description)
        db.session.add(subject)
        db.session.commit()
        
        return {'message': 'Subject added successfully', 'id': subject.id}, 201
    
    @admin_required
    def put(self, subject_id):
        subject = Subject.query.get(subject_id)
        if not subject:
            return {'error': 'Subject not found'}, 404
            
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        
        if not name:
            return {'error': 'Please fill required fields'}, 400
            
        subject.name = name
        subject.description = description
        db.session.commit()
        
        return {'message': 'Subject updated successfully'}
    
    @admin_required
    def delete(self, subject_id):
        subject = Subject.query.get(subject_id)
        if not subject:
            return {'error': 'Subject not found'}, 404
            
        if subject.chapters:
            return {'error': 'Subject has chapters! Delete chapters first.'}, 400
            
        db.session.delete(subject)
        db.session.commit()
        
        return {'message': 'Subject deleted successfully'}

api.add_resource(SubjectApi, '/api/subjects', '/api/subjects/<int:subject_id>') 


class ChapterApi(Resource):
    @admin_required
    def get(self):
        chapters = Chapter.query.all()
        return {'chapters': [ {
            'id': chapter.id,
            'subject_id': chapter.subject_id,
            'name': chapter.name,
            'description': chapter.description
        } for chapter in chapters 
        ] }

api.add_resource(ChapterApi, '/api/chapters')


class QuizzesApi(Resource):
    def get(self):
        quizzes = Quiz.query.all()
        return {'quizzes': [ {
            'id': quiz.id,
            'chapter_id': quiz.chapter_id,
            'date_of_quiz': quiz.date_of_quiz.isoformat() if quiz.date_of_quiz else None,
            'time_duration': quiz.time_duration,
            'remarks': quiz.remarks
        } for quiz in quizzes 
        ] }

api.add_resource(QuizzesApi, '/api/quizzes')


class ScoresApi(Resource):
    @admin_required
    def get(self):
        scores = Score.query.all()
        
        return {'scores': [ {
            'id': score.id,
            'quiz_id': score.quiz_id,
            'user_id': score.user_id,
            'total_scored': score.total_scored,
            'time_stamp_of_attempt': score.time_stamp_of_attempt.isoformat() if score.time_stamp_of_attempt else None
        } for score in scores 
        ] }

api.add_resource(ScoresApi, '/api/scores')
