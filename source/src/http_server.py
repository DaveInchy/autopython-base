import http.server
import socketserver
import json
import time
import os

PORT = 8080
WEBHOOK_PATH = '/webhook'
REQUESTS_DIR = 'requests'

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == WEBHOOK_PATH:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                self.save_request(data)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Webhook received')
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def save_request(self, data):
        if not os.path.exists(REQUESTS_DIR):
            os.makedirs(REQUESTS_DIR)
        
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        filename = os.path.join(REQUESTS_DIR, f'{timestamp}.json')
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

def run_server():
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()