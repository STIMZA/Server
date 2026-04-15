from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import os
import re
import json
import pymongo # type: ignore

# This class adds threading capabilities to the standard HTTPServer
class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Define your routes
        if self.path == '/':
            self.serve_file('index.html')
            
        elif self.path == '/about':
            # You can serve an actual file:
            self.serve_file('about.html')
            # OR send a direct string response:
            # self.send_text_response("<h1>About Us</h1><p>Welcome to the RMM Analytics portal.</p>")

        # 2. Handle static files (CSS, JS, Images) if they exist
        elif os.path.exists(self.path.lstrip('/')):
            self.serve_file(self.path.lstrip('/'))
            
        else:
            self.send_error(404, "Page Not Found")

    def serve_file(self, filename):
        """Helper to read and serve files from the directory"""
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            self.send_response(200)
            # Basic logic to set header based on extension
            if filename.endswith(".html"):
                self.send_header('Content-type', 'text/html')
            elif filename.endswith(".css"):
                self.send_header('Content-type', 'text/css')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f"File {filename} not found")

    def send_text_response(self, html_string):
        """Helper to send raw HTML strings"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_string.encode('utf-8'))
    
    def do_POST(self):

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Send HTTP response
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Data processed")

        raw_data = post_data.decode('utf-8').strip()

        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["rmm_db"]

        # 1. Define your routes
        if self.path == '/sessions': 
            # Regex to find "Key":"Value"
            pattern = r'"?(\w+)"?:"([^"]+)"'            
            collection = db["analytics_data"]

            # Process each line
            for line in raw_data.split('\n'):
                item = dict(re.findall(pattern, line))
                
                # 1. Extract 'name' and 'start' to form the Unique ID
                name_val = item.get("Name")
                start_val = item.get("Week_of_registry")

                if name_val and start_val:
                    # 2. Combine Name and Start for the Primary Key (_id)
                    # Example: "Sensor_A1_2023-10-01"
                    item["_id"] = f"{name_val}_{start_val.replace(' ', '_')}"

                    # 3. Upsert (Update if ID exists, otherwise Insert)
                    collection.replace_one(
                        {"_id": item["_id"]}, 
                        item, 
                        upsert=True
                    )
                    print(f"Upserted ID: {item['_id']}")
                else:
                    print(f"Skipping line: Missing 'name' or 'start' field. Line: {line}")
            
        elif self.path == '/ruller':            
            
            collection = db["ruller_data"]

            # Extract pairs
            matches = re.findall(r'"(\d+)":"([\d.]+)"', raw_data)

            for key, val in matches:
                collection.update_one(
                    {"_id": key},                 # Filter
                    {"$set": {"value": float(val)}}, # Update
                    upsert=True                    # Create if it doesn't exist
                )

            print(f"Processed {len(matches)} ruller updates.")

        elif self.path == '/poi':
            collection = db["page_poi_data"]
            # Split by line and process each entry
            for line in raw_data.strip().split('\n'):
                matches = re.findall(r'"(.*?)"', line)
                
                if len(matches) == 4:
                    # Replace spaces with underscores and append week_of_registry
                    # week_of_registry is assumed to be matches[1] or matches[3] based on your previous structure
                    # I'll use matches[1] here; adjust the index if your data order differs
                    registry_week = matches[3]
                    doc_id = f"{matches[0].replace(' ', '_')}_{registry_week}"
                    
                    # Define the data structure
                    new_data = {
                        "_id": doc_id,
                        "value": matches[1],
                        matches[2]: matches[3]
                    }

                    # replace_one with upsert=True: 
                    # If _id exists, it overwrites. If not, it creates a new record.
                    collection.replace_one({"_id": doc_id}, new_data, upsert=True)
                    print(f"Upserted ID: {doc_id}")
            print("Page POI data update complete.")

        # 2. Handle static files (CSS, JS, Images) if they exist
        elif os.path.exists(self.path.lstrip('/')):
            self.serve_file(self.path.lstrip('/'))
            
        else:
            self.send_error(404, "resource not found")       


def run(port=80):
    server_address = ('localhost', port)
    # Use ThreadingHTTPServer instead of HTTPServer
    httpd = ThreadingHTTPServer(server_address, MyHandler)
    print(f"Multi-threaded server started on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.shutdown()

if __name__ == "__main__":
    run()
