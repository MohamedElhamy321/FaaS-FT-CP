import requests
import time

def test_router(router_url):
    print(f"\nTesting {router_url}")
    try:
        response = requests.post(router_url, data="15", timeout=10)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Test RR router
rr_router_url = "http://localhost:31028/fibonacci"
print("\nTesting Round Robin Router...")
rr_success = test_router(rr_router_url)

# Test AS router
as_router_url = "http://localhost:30081/fibonacci"
print("\nTesting Adaptive Scaling Router...")
as_success = test_router(as_router_url)

print("\nSummary:")
print(f"RR Router: {'SUCCESS' if rr_success else 'FAILED'}")
print(f"AS Router: {'SUCCESS' if as_success else 'FAILED'}")