import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def main():
    # 1년 유효 개인 인증 토큰 (2026-04-03 발송분)
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc3NTE3ODAxOCwianRpIjoiMWVhODBmMjItMDUzNC00MTE0LTgzZTctNDdiYzY2MGQ1NmU1IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MSwibmJmIjoxNzc1MTc4MDE4LCJjc3JmIjoiZmU3NjMwZTMtOTc2OC00OWQ5LWJlOTUtYTZkM2NlZjcxZjU2IiwiZXhwIjoxODA2NzE0MDE4fQ._eVNf2CRSSTHl77L2EvoVOQUPjd6_TEjGoMBsuskDLs"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "sender_name": "Antigravity Test (Auth API)",
        "receivers": "tiffanie.kim@samsung.com",
        "subject": "[Leebalso] Email Auth API Test",
        "content": "<h1>성공</h1><p>보안 설정 및 토큰 인증 발송 테스트 결과입니다.</p>"
    }

    print("\nExecuting email send request (With Authentication Token)...")
    # EmailApi has resource_name = 'email'
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
