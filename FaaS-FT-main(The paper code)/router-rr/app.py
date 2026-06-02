from flask import Flask, request, jsonify
import requests
from threading import Lock
import os

app = Flask(__name__)

# List of backend servers (will be populated by environment variables)
backend_servers = []
current_server_index = 0
index_lock = Lock()

@app.route('/fibonacci', methods=['POST'])
def route_request():
    global current_server_index
    
    # Get the next server in round-robin fashion
    with index_lock:
        server = backend_servers[current_server_index]
        current_server_index = (current_server_index + 1) % len(backend_servers)
    
    # Forward the request
    try:
        response = requests.post(f"http://{server}/fibonacci", data=request.get_data())
        return response.content, response.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Get backend servers from environment variable
    servers_env = os.getenv('BACKEND_SERVERS', '')
    if servers_env:
        backend_servers = servers_env.split(',')
    else:
        # Default test backends
        backend_servers = ['localhost:8001', 'localhost:8002', 'localhost:8003']
    
    print(f"Starting RR Router with backends: {backend_servers}")
    app.run(host='0.0.0.0', port=8082)