from flask import Flask, request, jsonify
import requests
from threading import Lock
import time
import os

app = Flask(__name__)

class ServerMetrics:
    def __init__(self):
        self.response_times = []
        self.last_used = 0
        self.error_count = 0
        self.max_window = 10  # Keep last 10 responses

    def add_response_time(self, response_time):
        self.response_times.append(response_time)
        if len(self.response_times) > self.max_window:
            self.response_times.pop(0)
        self.last_used = time.time()

    def get_average_response_time(self):
        if not self.response_times:
            return 0.0  # Start with 0 to give new servers a chance
        return sum(self.response_times) / len(self.response_times)

    def record_error(self):
        self.error_count += 1

# Dictionary to store metrics for each server
server_metrics = {}
metrics_lock = Lock()

def initialize_server_metrics(servers):
    with metrics_lock:
        for server in servers:
            if server not in server_metrics:
                server_metrics[server] = ServerMetrics()

def select_best_server():
    with metrics_lock:
        best_server = None
        best_score = float('inf')
        
        # First, check if we have any servers without performance data
        servers_no_data = [server for server, metrics in server_metrics.items() 
                          if not metrics.response_times]
        if servers_no_data:
            # If we have servers without data, try one of those first
            from random import choice
            return choice(servers_no_data)
            
        current_time = time.time()
        for server, metrics in server_metrics.items():
            # Calculate score based on average response time and errors
            avg_response_time = metrics.get_average_response_time()
            error_penalty = metrics.error_count * 1.5
            time_since_last_use = current_time - metrics.last_used
            
            # Score is weighted sum of metrics
            score = avg_response_time + error_penalty - (time_since_last_use * 0.1)
            
            if score < best_score:
                best_score = score
                best_server = server
        
        # If we still don't have a server, pick any random one as fallback
        if best_server is None:
            from random import choice
            return choice(list(server_metrics.keys()))
            
        return best_server

@app.route('/fibonacci', methods=['POST'])
def route_request():
    server = select_best_server()
    
    if not server:
        return jsonify({"error": "No available servers"}), 503
    
    start_time = time.time()
    try:
        response = requests.post(f"http://{server}/fibonacci", data=request.get_data())
        end_time = time.time()
        
        with metrics_lock:
            server_metrics[server].add_response_time(end_time - start_time)
        
        return response.content, response.status_code
    except requests.RequestException as e:
        with metrics_lock:
            server_metrics[server].record_error()
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
    
    initialize_server_metrics(backend_servers)
    print(f"Starting AS Router with backends: {backend_servers}")
    app.run(host='0.0.0.0', port=8082)