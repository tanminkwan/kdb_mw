import pytest
import json

def test_send_email(client, auth_headers):
    payload = {
        "sender_name": "리발소 테스트(Pytest)",
        "receivers": "tiffanie.kim@samsung.com",
        "subject": "[테스트] 리발소 메일 발송 API 테스트 (Pytest)",
        "content": "<h1>메일 발송 테스트</h1><p>Pytest를 통해 발송된 테스트 메일입니다.</p>"
    }
    
    # EmailApi has route_base = '/email'
    response = client.post(
        '/email/send',
        data=json.dumps(payload),
        headers=auth_headers,
        content_type='application/json'
    )
    
    print(f"\nResponse: {response.json}")
    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"] == "Email sent successfully"
