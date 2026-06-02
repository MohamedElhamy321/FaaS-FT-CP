from flask import Flask, request
import time

app = Flask(__name__)

def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

@app.route('/fibonacci', methods=['POST'])
def calculate_fibonacci():
    try:
        n = int(request.get_data())
        result = []
        for i in range(n):
            result.append(str(fib(i)))
        return ','.join(result)
    except Exception as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)