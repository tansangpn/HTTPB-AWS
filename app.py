from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import json
from datetime import datetime
import os
import socket

app = Flask(__name__, instance_relative_config=True)
# Đảm bảo thư mục instance tồn tại
try:
    os.makedirs(app.instance_path)
except OSError:
    pass
# Set base directory for the app


# Basic configurations
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    TESTING=False,
    DATA_FILE=os.path.join(app.instance_path, 'tasks.json')
)

# Set the database URI based on testing mode
if app.config['TESTING']:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "app.db")}'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables if not testing
if not app.config['TESTING']:
    with app.app_context():
        db.create_all()

def get_data_file():
    return app.config['DATA_FILE']

def load_tasks():
    data_file = get_data_file()
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    data_file = get_data_file()
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    with open(data_file, 'w') as f:
        json.dump(tasks, f)

def get_system_info():
    return {
        'hostname': socket.gethostname(),
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_user': os.getenv('USER', 'unknown')
    }

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')

            if not username or not password or not email:
                flash('All fields are required')
                return redirect(url_for('register'))

            if User.query.filter_by(username=username).first():
                flash('Username already exists')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Email already registered')
                return redirect(url_for('register'))

            user = User(
                username=username,
                password=generate_password_hash(password),
                email=email
            )
            
            db.session.add(user)
            db.session.commit()

            flash('Registration successful!')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during registration')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))

        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    tasks = load_tasks()
    return render_template('index.html', tasks=tasks, system_info=get_system_info())

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    return jsonify(load_tasks())

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    task = request.get_json()
    tasks = load_tasks()
    
    new_task = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S'),
        'title': task.get('title'),
        'description': task.get('description', ''),
        'status': 'pending',
        'priority': task.get('priority', 'medium'),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    tasks.append(new_task)
    save_tasks(tasks)
    return jsonify(new_task), 201

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    tasks = load_tasks()
    task_update = request.get_json()
    
    for task in tasks:
        if task['id'] == task_id:
            task.update(task_update)
            save_tasks(tasks)
            return jsonify(task)
            
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)