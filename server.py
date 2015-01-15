from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer

class PullRequestHandler:
    def __init__(self):
        pass

    def handle(event):
        print event
 
class Handler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_POST(self):
        self._set_headers()

        if self.headers["X-GitHub-Event"] == "pull_request":
            PullRequestHandler().handle(self.rfile.read(int(self.headers["Content-Length"])))
        
if __name__ == "__main__":
    try:
        httpd = HTTPServer(('', 8080), Handler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.socket.close()