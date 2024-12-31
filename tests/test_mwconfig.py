import pytest
import json
from app.dmlsForAgent import AutorunResult  # Assuming AutorunResult is a model in your application
from app.views.was import MWConfiguration

@pytest.fixture
def mock_protect(monkeypatch):
    monkeypatch.setattr('flask_appbuilder.api.protect', lambda: lambda x: x)

@pytest.fixture
def mw_config(app):
    return MWConfiguration()

def test_httpm_config_missing_content(client, mock_protect):
    #monkeypatch.setattr(mw_config, 'protect', lambda: lambda x: x)
    
    response = client.post('/api/v1/config/httpm', json={
        'host_id': '123'
    })
    
    assert response.status_code == 401
    assert response.json == {'return_code': -2, 'message': 'content must be included'}

"""
def test_httpm_config_missing_host_id(client, auth_headers):
    response = client.post(
        url_for('MWConfiguration.httpm_config'),
        headers=auth_headers,
        data=json.dumps({'content': 'some_content'}),
        content_type='application/json'
    )
    assert response.status_code == 401
    assert response.json['return_code'] == -2
    assert response.json['message'] == 'host_id must be included'

def test_httpm_config_success(client, auth_headers, mocker):
    mocker.patch.object(AutorunResult, '_update_httpm', return_value=(0, 'success'))

    response = client.post(
        url_for('MWConfiguration.httpm_config'),
        headers=auth_headers,
        data=json.dumps({'host_id': '1234', 'content': 'some_content'}),
        content_type='application/json'
    )

    assert response.status_code == 201
    assert response.json['return_code'] == 0
    assert response.json['msg'] == 'success'

def test_jeusDomainConfig(client, auth_headers):
    response = client.post(
        url_for('MWConfiguration.jeusDomainConfig'),
        headers=auth_headers,
        data=json.dumps({'some_key': 'some_value'}),
        content_type='application/json'
    )

    assert response.status_code == 201
    assert response.json['some_key'] == 'some_value'  # Replace with actual expected key
"""