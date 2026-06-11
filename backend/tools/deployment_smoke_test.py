import sys
import urllib.request
import urllib.error
import json
import os

def check_endpoint(url):
    print(f"Checking endpoint: {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            print(f"Response Code: {status}")
            return status, body
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        try:
            body = e.read().decode('utf-8')
        except Exception:
            body = ""
        return e.code, body
    except Exception as e:
        print(f"Connection Error: {e}")
        return None, str(e)

def main():
    host = os.getenv("SMOKE_TEST_HOST", "http://localhost:8000")
    print(f"Starting deployment smoke test targeting: {host}")
    
    # 1. Check health endpoint
    status, body = check_endpoint(f"{host}/health")
    if status != 200:
        print("FAIL: Health endpoint did not return 200 OK")
        sys.exit(1)
        
    try:
        health_data = json.loads(body)
        if health_data.get("status") != "ok":
            print(f"FAIL: Health status is not 'ok': {health_data}")
            sys.exit(1)
        print(f"Health Status: {health_data.get('status')}")
    except Exception as e:
        print(f"FAIL: Health body is not valid JSON: {e}")
        sys.exit(1)
        
    # 2. Check health details
    status, body = check_endpoint(f"{host}/health/details")
    # Details check could return 500 or 503 if DB or Redis is down, which is a real failure!
    if status != 200:
        print(f"FAIL: Health details returned unexpected status {status}")
        sys.exit(1)
        
    try:
        details_data = json.loads(body)
        print(f"Database Health: {details_data.get('database')}")
        print(f"Redis Health: {details_data.get('redis')}")
        if details_data.get("status") != "ok":
            print(f"FAIL: Health details status is not 'ok': {details_data}")
            sys.exit(1)
    except Exception as e:
        print(f"FAIL: Health details body is not valid JSON: {e}")
        sys.exit(1)
        
    # 3. Check public API metadata (should return 401, not 500)
    status, body = check_endpoint(f"{host}/api/v1/groups/templates")
    if status == 500:
        print("FAIL: Templates endpoint returned HTTP 500 (indicates code or startup issues)")
        sys.exit(1)
        
    print("SUCCESS: Deployment smoke test completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
