"""
Simple HTTP Server for Frontend (Windows Compatible)
Run with: python serve_frontend.py

This server handles Windows file system quirks properly.
"""

import http.server
import socketserver
import os
import sys
import mimetypes
from pathlib import Path

PORT = 3000
DIRECTORY = "frontend"

class WindowsCompatibleHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP handler that works properly on Windows."""
    
    def __init__(self, *args, **kwargs):
        self.base_directory = Path(DIRECTORY).resolve()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse the path
            path = self.path.split('?')[0]  # Remove query string
            if path == '/':
                path = '/index.html'
            
            # Build file path safely
            file_path = self.base_directory / path.lstrip('/')
            file_path = file_path.resolve()
            
            # Security: ensure path is within base directory
            try:
                file_path.relative_to(self.base_directory)
            except ValueError:
                self.send_error(403, "Forbidden")
                return
            
            # Check if file exists
            if not file_path.exists() or not file_path.is_file():
                self.send_error(404, "File not found")
                return
            
            # Get content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # Read file content
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
            except Exception as e:
                self.send_error(500, f"Error reading file: {e}")
                return
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(500, f"Server error: {e}")
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{self.log_date_time_string()}] {args[0]}")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded HTTP server for better performance."""
    allow_reuse_address = True
    daemon_threads = True


def run_server():
    """Start the HTTP server."""
    # Change to script directory
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    # Check if frontend directory exists
    frontend_path = script_dir / DIRECTORY
    if not frontend_path.exists():
        print(f"Error: '{DIRECTORY}' directory not found!")
        print(f"Expected at: {frontend_path}")
        sys.exit(1)
    
    # Verify index.html exists
    index_path = frontend_path / "index.html"
    if not index_path.exists():
        print(f"Error: 'index.html' not found in {DIRECTORY}!")
        sys.exit(1)
    
    print(f"Frontend directory: {frontend_path}")
    print(f"Files found: {list(frontend_path.glob('*'))}")
    print()
    
    try:
        with ThreadedHTTPServer(("0.0.0.0", PORT), WindowsCompatibleHandler) as httpd:
            print("=" * 50)
            print(f"  Frontend server running!")
            print(f"  Open: http://localhost:{PORT}")
            print("=" * 50)
            print()
            print("Press Ctrl+C to stop the server")
            print()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except OSError as e:
        if "Address already in use" in str(e) or "10048" in str(e):
            print(f"Error: Port {PORT} is already in use!")
            print("Either stop the other process or change PORT in this script.")
        else:
            raise


if __name__ == "__main__":
    run_server()
