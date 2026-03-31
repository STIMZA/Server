import socket
import time

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind to all interfaces on port 8080 (exposes server to all network interfaces; consider security implications)
server_socket.bind((SERVER_HOST, SERVER_PORT))

# Listen for incoming connections (backlog of 5)
server_socket.listen(5)  
print("Server is listening on port {}...".format(SERVER_PORT))

while True:
    # Accept a connection (blocking call)
    client_socket, client_address = server_socket.accept()  
    request = client_socket.recv(1500).decode()
    #print("Received request from {}: {}".format(client_address, request))
    headers = request.split('\n')
    first_header_components = headers[0].split()
    http_method = first_header_components[0]
    path = first_header_components[1]

    if path == "/":
        fin = open('index.html')
        content = fin.read()
        fin.close()

        #STATUS_LINE
        #HEADER
        #MESSAGE_BODY
        response = 'HTTP/1.1 200 OK \n\n' + content
