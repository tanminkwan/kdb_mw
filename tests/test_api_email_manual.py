import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def main():
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "sender_name": "Antigravity Test (Open API)",
        "receivers": "tiffanie.kim@samsung.com",
        "subject": "[Leebalso] Email Open API Test",
        "content": "<h1>성공</h1><p>보안 설정 해제 후 발송 테스트 결과입니다.</p>"
    }

    print("\nExecuting email send request (No Authentication)...")
    # EmailApi has resource_name = 'email'
    # FAB automatically adds /api/v1 prefix for REST APIs
    res = requests.post(f"{BASE_URL}/api/v1/email/send", headers=headers, json=payload, timeout=15)
    
    print(f"Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Response is not JSON:")
        print(res.text[:500])

    if res.status_code == 200:
        print("\nTest PASSED.")
    else:
        print("\nTest FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
