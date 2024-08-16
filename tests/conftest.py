import pytest
import os
import subprocess
import json
from app import app as flask_app, db, appbuilder
from flask_appbuilder.security.sqla.models import User, Role, PermissionView
from flask_appbuilder import AppBuilder, SQLA
from flask_jwt_extended import create_access_token

"""
@pytest.fixture(scope='module', autouse=True)
def setup_admin_user():
    print("########### setup_admin_user #############.")
    
    # Set the environment variable for the database URI if not already set
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tiffanie:1q2w3e4r!!@localhost:25432/mw_test'
    os.environ['FLASK_APP'] = 'app'  # Set the name of your Flask app

    # Check if the admin user already exists
    with appbuilder.get_app.app_context():
        admin_user = db.session.query(User).filter_by(username='tiffanie').first()
    
    if admin_user:
        print("Admin user already exists. Skipping creation.")
    else:
        # Run the `flask fab create-admin` command programmatically
        try:
            subprocess.run(
                ["flask", "fab", "create-admin", 
                 "--username", "tiffanie",
                 "--firstname", "Hennry",
                 "--lastname", "Kim",
                 "--email", "tiffanie@a.com",
                 "--password", "1q2w3e4r"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while creating admin user: {e}")
            raise
"""
@pytest.fixture(scope='module')
def app():
    # TESTING 설정을 활성화합니다.
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": 'postgresql://tiffanie:1q2w3e4r!!@localhost:25432/mw_test',
        "SCHEDULER_API_ENABLED": True,
    })
    
    # Initialize Flask AppBuilder
    
    with flask_app.app_context():
        db.create_all()  # 데이터베이스 테이블 생성
            
        # Create roles and permissions
        appbuilder.sm.add_role('Admin')
        appbuilder.sm.add_role('User')
        appbuilder.sm.add_role('Public')

        # Check if the admin user already exists
        existing_admin = appbuilder.sm.find_user(username='tiffanie')
        if not existing_admin:
            # Create an admin user with appropriate permissions
            admin_role = appbuilder.sm.find_role('Admin')
            appbuilder.sm.add_user(
                    username='tiffanie',
                    first_name='Admin',
                    last_name='User',
                    email='admin@admin.com',
                    role=admin_role,
                    password='1q2w3e4r!!'
                )
        yield flask_app  # flask_app 객체를 테스트 함수에 제공
        db.session.remove()  # 데이터베이스 세션 제거
#        db.drop_all()  # 데이터베이스 테이블 삭제

@pytest.fixture(scope='module')
def appbuilder_instance(app):
    # Initialize AppBuilder with the testing app context
    return AppBuilder(app, db.session)

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()  # 테스트 클라이언트를 반환

@pytest.fixture(scope='module')
def json_header():
    return {'Content-Type': 'application/json;charset=utf-8'}

@pytest.fixture(scope='module')
def get_test_user():
    """Fixture to retrieve or create a user with the username 'tiffanie'."""
    # Query the database for the user with username 'tiffanie'
    user = db.session.query(User).filter_by(username='tiffanie').first()
    
    if not user:
        # Create the user if it doesn't exist
        role = appbuilder.sm.find_role('User')  # Or 'Admin', depending on the required role
        user = appbuilder.sm.add_user(
            username='tiffanie',
            first_name='Tiffanie',
            last_name='TestUser',
            email='tiffanie@test.com',
            role=role,
            password='1q2w3e4r!!'
        )
        db.session.commit()

    # Ensure the user has the required permission
    permission = db.session.query(PermissionView).filter_by(
        permission=appbuilder.sm.find_permission('can_httpm_config'),
        view_menu=appbuilder.sm.find_view_menu('MWConfiguration')
    ).first()

    if permission and permission not in user.roles[0].permissions:
        user.roles[0].permissions.append(permission)
        db.session.commit()

    return user

@pytest.fixture
def auth_headers(get_test_user):
    """Fixture to generate auth headers for the test user."""
    # Authenticate the user and generate an authentication token
    user = get_test_user
    
    # Generate a JWT token for the user
    auth_token = create_access_token(identity=user.id)  # Use user ID or another identifier
    
    return {
        'Authorization': f'Bearer {auth_token}'
    }