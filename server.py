import os
import socket
import random
from threading import Thread

# Define user credentials (this should be secured in real applications)
user_credentials = {
    'john': '1234',
    'jane': '5678',
    'joe': 'qwerty'
}

# Global settings (simplified for demonstration)
transfer_mode = "binary"  # or "ascii"
data_structure = "file"  # or "record"
transfer_type = "stream"  # or "block" or "compressed"

# Placeholder for the main directory to prevent escaping to the server filesystem
BASE_DIR = os.path.abspath("main")
os.chdir(BASE_DIR)
def handle_pasv_command(connection):
    """
    Handles the PASV command to open a new socket for the data channel.
    """
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_socket.bind(('', 0))  # Bind to an available port chosen by the OS
    data_socket.listen(1)
    
    # Get the socket's assigned IP address and port number
    ip, port = data_socket.getsockname()
    ip_address = ','.join(ip.split('.'))
    p1, p2 = port // 256, port % 256
    
    # Send the PASV response to the client
    pasv_message = f"227 Entering Passive Mode ({ip_address},{p1},{p2})."
    connection.sendall(pasv_message.encode())
    
    # Wait for a connection on the data socket
    data_conn, _ = data_socket.accept()
    
    return data_conn

def handle_client_connection(connection):
    """
    Handles each client connection in a separate thread.
    """
    # Send the welcome banner message to the client
    welcome_message = "Welcome to NSCOM01 FTP server"
    connection.sendall(welcome_message.encode())
    
    authenticated = False
    username = None
    
    try:
        while True:
            # Receive command from the client
            command_full = connection.recv(1024).decode().strip()
            if not command_full:
                break  # Connection closed by the client
            
            command, *args = command_full.split()
            command = command.upper()
            response = "500 Unknown command."

            if command == 'USER':
                username = args[0] if args else None
                if username in user_credentials:
                    response = "331 Username okay, need password."
                else:
                    response = "332 Need account for login."
            elif command == 'PASS':
                password = args[0] if args else None
                if username and user_credentials.get(username) == password:
                    authenticated = True
                    response = "230 User logged in, proceed."
                else:
                    response = "530 Not logged in."
            elif not authenticated:
                response = "530 Please login with USER and PASS."
            elif command == 'PWD':
                response = f"257 \"{os.getcwd()}\" is the current directory."
            elif command == 'CWD':
                try:
                    os.chdir(args[0])
                    response = "250 Directory successfully changed."
                except Exception as e:
                    response = f"550 Failed to change directory. {e}"
            elif command == 'CDUP':
                try:
                    os.chdir('..')
                    response = "200 Command okay."
                except Exception as e:
                    response = f"550 Failed to change directory. {e}"
            elif command == 'MKD':
                try:
                    os.mkdir(args[0])
                    response = "257 Directory created."
                except Exception as e:
                    response = f"550 Create directory operation failed. {e}"
            elif command == 'RMD':
                try:
                    os.rmdir(args[0])
                    response = "250 Directory removed."
                except Exception as e:
                    response = f"550 Remove directory operation failed. {e}"
            elif command == 'PASV':
                # Handle PASV command
                data_conn = handle_pasv_command(connection)
                continue 
            elif command == 'LIST':
                try:
                    listing = os.listdir('.')
                    response = "\n".join(listing)
                except Exception as e:
                    response = f"550 Failed to list directory. {e}"
            elif command == 'RETR':            
                filename = ' '.join(args)  # Assuming filename is the rest of the command
                filepath = os.path.join(os.getcwd(), filename)
                if os.path.exists(filepath):
                    connection.sendall(b'1')  # Signal client that file transfer will start
                    with open(filepath, 'rb') as file:
                        data = file.read(1024)
                        while data:
                            connection.sendall(data)
                            data = file.read(1024)
                    print(f'{filename} sent successfully.')
                else:
                    connection.sendall(b'0')  # Signal client that file transfer will not start
                    print(f'{filename} does not exist.')
            elif command == 'DELE':
                try:
                    os.remove(args[0])
                    response = "250 File deleted."
                except Exception as e:
                    response = f"550 Delete operation failed. {e}"
            elif command == 'STOR':
                filename = ' '.join(args)
                connection.sendall(b'1')  # Signal client to start sending the file
                with open(filename, 'wb') as file:
                    while True:
                        data = connection.recv(1024)
                        if not data:
                            break  # File transfer done
                        file.write(data)
                print(f'{filename} received successfully.')
            elif command == 'HELP':
                response = ("214-The following commands are recognized and their explanations:\n"
                            "USER <username> - Log in as the user with the specified username.\n"
                            "PASS <password> - Authenticate with the specified password.\n"
                            "PWD - Print the current working directory on the server.\n"
                            "CWD <directory> - Change the current working directory.\n"
                            "CDUP - Change to the parent of the current working directory.\n"
                            "MKD <directory> - Make a new directory on the server.\n"
                            "RMD <directory> - Remove a directory from the server.\n"
                            "PASV - Enter passive transfer mode.\n"
                            "LIST - List the files in the current directory.\n"
                            "RETR <filename> - Retrieve a file from the server.\n"
                            "STOR <filename> - Store a file on the server.\n"
                            "DELE <filename> - Delete a file from the server.\n"
                            "HELP - Show this help message.\n"
                            "QUIT - Log out and close the connection.\n"
                            "Note: Commands are not case-sensitive.")

            elif command == 'QUIT':
                response = "221 Goodbye."
                break
            else:
                response = "502 Command not implemented."

            connection.sendall(response.encode())
    
    finally:
        connection.close()

def start_ftp_server(address='127.0.0.1', port=2121):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((address, port))
    server_socket.listen(5)
    print(f"FTP server started on {address}:{port}")
    
    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")
            client_thread = Thread(target=handle_client_connection, args=(conn,))
            client_thread.start()
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_ftp_server()
