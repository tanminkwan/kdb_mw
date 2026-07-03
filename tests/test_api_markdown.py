import pytest
import json

def test_convert_markdown_to_html(client, auth_headers):
    payload = {
        "content": "# Markdown 테스트\n\n- 항목 1\n- 항목 2\n\n```mermaid\ngraph TD; A-->B;\n```"
    }
    
    # MarkdownApi has route_base = '/markdown'
    response = client.post(
        '/markdown/to_html',
        data=json.dumps(payload),
        headers=auth_headers,
        content_type='application/json'
    )
    
    print(f"\nResponse: {response.json}")
    assert response.status_code == 200
    assert "html" in response.json
    assert "<h1>Markdown 테스트</h1>" in response.json["html"]
