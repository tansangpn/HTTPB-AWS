import pytest
import json
import os
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    """Setup test client"""
    # Create test data directory
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    os.makedirs(test_data_dir, exist_ok=True)
    test_data_file = os.path.join(test_data_dir, 'test_tasks.json')

    # Configure app for testing
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SECRET_KEY='test-secret-key',
        DATA_FILE=test_data_file
    )
    
    # Create tables and test client
    with app.test_client() as client:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Create test user
            user = User(
                username='testuser',
                password=generate_password_hash('testpass'),
                email='test@example.com'
            )
            db.session.add(user)
            db.session.commit()
            
            # Clear test tasks file if it exists
            if os.path.exists(test_data_file):
                os.remove(test_data_file)
            
            yield client
            
            # Cleanup
            db.session.remove()
            db.drop_all()

            # Remove test file
            if os.path.exists(test_data_file):
                os.remove(test_data_file)

@pytest.fixture
def auth_client(client):
    """Client with authenticated user"""
    with client.session_transaction() as sess:
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)
    return client

def test_login_page(client):
    """Test login page"""
    rv = client.get('/login')
    assert rv.status_code == 200
    assert b'ng nh' in rv.data

def test_login(client):
    """Test login functionality"""
    rv = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert rv.status_code == 302  # Redirect after login

def test_home_page(auth_client):
    """Test trang chủ"""
    rv = auth_client.get('/')
    assert rv.status_code == 200
    assert b"Task Tracker" in rv.data

def test_about_page(client):
    """Test trang about"""
    rv = client.get('/about')
    assert rv.status_code == 200

def test_health_check(client):
    """Test API health check"""
    rv = client.get('/api/health')
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert json_data['status'] == 'healthy'

def test_create_task(auth_client):
    """Test tạo task mới"""
    task_data = {
        'title': 'Test Task',
        'description': 'Test Description',
        'priority': 'high'
    }
    rv = auth_client.post('/api/tasks',
                    data=json.dumps(task_data),
                    content_type='application/json')
    assert rv.status_code == 201
    json_data = rv.get_json()
    assert json_data['title'] == 'Test Task'

def test_get_tasks(auth_client):
    """Test lấy danh sách tasks"""
    # Make sure we start with an empty task list
    test_data_file = app.config['DATA_FILE']
    if os.path.exists(test_data_file):
        os.remove(test_data_file)

    task_data = {
        'title': 'Test Task',
        'description': 'Test Description',
        'priority': 'high'
    }
    auth_client.post('/api/tasks',
                data=json.dumps(task_data),
                content_type='application/json')
    
    rv = auth_client.get('/api/tasks')
    assert rv.status_code == 200
    tasks = rv.get_json()
    assert len(tasks) == 1
    assert tasks[0]['title'] == 'Test Task'

def test_update_task_status(auth_client):
    """Test cập nhật trạng thái task"""
    task_data = {
        'title': 'Test Task',
        'description': 'Test Description',
        'priority': 'high'
    }
    rv = auth_client.post('/api/tasks',
                    data=json.dumps(task_data),
                    content_type='application/json')
    task_id = rv.get_json()['id']
    
    update_data = {'status': 'completed'}
    rv = auth_client.put(f'/api/tasks/{task_id}',
                   data=json.dumps(update_data),
                   content_type='application/json')
    assert rv.status_code == 200
    assert rv.get_json()['status'] == 'completed'

def test_task_validation(auth_client):
    """Test validation khi tạo task"""
    task_data = {'title': 'Test Task'}
    rv = auth_client.post('/api/tasks',
                    data=json.dumps(task_data),
                    content_type='application/json')
    assert rv.status_code == 201

def test_invalid_task_id(auth_client):
    """Test xử lý task ID không tồn tại"""
    update_data = {'status': 'completed'}
    rv = auth_client.put('/api/tasks/invalid_id',
                   data=json.dumps(update_data),
                   content_type='application/json')
    assert rv.status_code == 404

def test_data_persistence(auth_client):
    """Test dữ liệu được lưu trữ đúng"""
    task_data = {
        'title': 'Persistence Test',
        'description': 'Test Description',
        'priority': 'high'
    }
    auth_client.post('/api/tasks',
                data=json.dumps(task_data),
                content_type='application/json')
    
    data_file = app.config['DATA_FILE']
    assert os.path.exists(data_file)
    
    with open(data_file, 'r') as f:
        tasks = json.load(f)
        assert len(tasks) == 1
        assert tasks[0]['title'] == 'Persistence Test'