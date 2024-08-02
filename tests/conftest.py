import pytest
from app import app as flask_app, db

@pytest.fixture(scope='module')
def app():
    # TESTING 설정을 활성화합니다.
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": 'postgresql://tiffanie:1q2w3e4r!!@localhost:25432/mw_test',
        "SCHEDULER_API_ENABLED": True,
    })
    
    with flask_app.app_context():
        db.create_all()  # 데이터베이스 테이블 생성
        yield flask_app  # flask_app 객체를 테스트 함수에 제공
        db.session.remove()  # 데이터베이스 세션 제거
#        db.drop_all()  # 데이터베이스 테이블 삭제

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()  # 테스트 클라이언트를 반환
