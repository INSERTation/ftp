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
transfer_mode = None 
data_structure = None
transfer_type = None

# Placeholder for the main directory to prevent escaping to the server filesystem
BASE_DIR = os.path.abspath("main")
os.chdir(BASE_DIR)

def handle_pasv():
    try:
        pasv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pasv_socket.bind(('127.0.0.1', 0))
        pasv_socket.listen(1)

        host, port = pasv_socket.getsockname()

        host_str = ','.join(host.split('.'))
        port_str = ','.join(str(i) for i in (port // 256, port % 256))

        response = f"227 Entering Passive Mode ({host_str},{port_str})"
        print("Generated PASV response:", response)  # Print generated response for debugging
        return response, pasv_socket
    except Exception as e:
        print(f"Error in PASV command. {e}")
        return "500 Error in PASV command.", None

def remove_record_markers(data):
    records = data.split(b'\n')
    records = [record for record in records if record.strip()]
    return b'\n'.join(records)

def send_stream(file, data_conn):
    try:
        while True:
            data = file.read(1024)
            if not data:
                break
            data_conn.sendall(data)
        return True
    except Exception as e:
        print(f"Error sending data: {e}")
        return False

def send_block(file, data_conn):
    try:
        block_size = 1024  # Define your block size
        while True:
            data = file.read(block_size)
            if not data:
                break
            data_conn.sendall(data)
            ack = data_conn.recv(1)  # Wait for acknowledgment
            if ack != b'1':
                print("Error: Block not acknowledged by server.")
                return False
        return True
    except Exception as e:
        print(f"Error sending block: {e}")
        return False

def send_compressed(file, data_conn):
    try:
        import zlib
        compressor = zlib.compressobj()
        while True:
            data = file.read(1024)
            if not data:
                break
            compressed_data = compressor.compress(data)
            if compressed_data:
                data_conn.sendall(compressed_data)
        data_conn.sendall(compressor.flush())
        return True
    except Exception as e:
        print(f"Error sending compressed data: {e}")
        return False

def handle_stor(filename, pasv_socket, client_socket):
    try:
        data_conn, _ = pasv_socket.accept()  # Unpack the returned tuple
        # Check if transfer settings are all set
        if not all([transfer_type, transfer_mode, data_structure]):
            data_conn.close()
            client_socket.sendall(b'0')
            return "503 Bad sequence of commands. Set TYPE, MODE, and STRU before transfer."
        client_socket.sendall(b'1')
        with open(filename, 'rb') as file:
            if transfer_type == "stream":
                if transfer_mode == "binary":
                    success = receive_stream(file, data_conn)
                else:
                    success = False  # Unsupported transfer mode
            elif transfer_type == "block":
                if transfer_mode == "binary":
                    success = receive_block(file, data_conn)
                else:
                    success = False  # Unsupported transfer mode
            elif transfer_type == "compressed":
                if transfer_mode == "binary":
                    success = receive_compressed(file, data_conn)
                else:
                    success = False  # Unsupported transfer mode
            else:
                success = False  # Unsupported transfer type
            if success:
                print(f'{filename} sent successfully.')
                return "226 File transferred successfully."
            else:
                client_socket.sendall(b'0')
                return "550 Error in File transfer."
    except Exception as e:
        print(f"Error in STOR command. {e}")
        client_socket.sendall(b'0')
        return "550 Error in File transfer."

def receive_stream(file, data_conn):
    try:
        while True:
            data = data_conn.recv(1024)
            if not data:
                break
            file.write(data)
        return True
    except Exception as e:
        print(f"Error receiving data: {e}")
        return False

def receive_block(file, data_conn):
    try:
        block_size = 1024  # Define your block size
        while True:
            data = data_conn.recv(block_size)
            if not data:
                break
            file.write(data)
            data_conn.sendall(b'1')  # Acknowledge block received
        return True
    except Exception as e:
        print(f"Error receiving block: {e}")
        return False

def receive_compressed(file, data_conn):
    try:
        import zlib
        decompressor = zlib.decompressobj()
        while True:
            compressed_data = data_conn.recv(1024)
            if not compressed_data:
                break
            data = decompressor.decompress(compressed_data)
            if data:
                file.write(data)
        file.write(decompressor.flush())
        return True
    except Exception as e:
        print(f"Error receiving compressed data: {e}")
        return False


def handle_retr(filename, pasv_socket, client_socket):
    try:
        data_conn = pasv_socket.accept()
        # Check if transfer settings are all set
        if not all([transfer_type, transfer_mode, data_structure]):
            data_conn.close()
            client_socket.sendall()
            return "503 Bad sequence of commands. Set TYPE, MODE, and STRU before transfer."

        client_socket.sendall(b'1')  # Signal client that file transfer will start
        if transfer_type == "stream":
            success = send_stream(open(filename, 'rb'), data_conn)
        elif transfer_type == "block":
            success = send_block(open(filename, 'rb'), data_conn)
        elif transfer_type == "compressed":
            success = send_compressed(open(filename, 'rb'), data_conn)
        else:
            data_conn.close()
            client_socket.sendall(b'0')
            return "504 Unsupported transfer type."
        if success:
            print(f'{filename} received successfully.')
            return "226 File received successfully."
        else:
            client_socket.sendall(b'0')
            return "550 Error in File transfer."
    except Exception as e:
        client_socket.sendall(b'0')
        print(f"Error in RETR command. {e}")
        return "550 Error in File transfer."

def handle_client_connection(connection):
    """
    Handles each client connection in a separate thread.
    """
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
                    if not args:
                        raise ValueError("Directory name not provided")

                    dirname = args[0]
                    if not dirname:
                        raise ValueError("Invalid directory name")
                    if '..' in dirname:
                        raise ValueError("Invalid directory name")

                    os.mkdir(dirname)
                    response = "257 Directory created."
                except ValueError as ve:
                    response = f"501 {ve}"
                except FileExistsError:
                    response = f"550 Directory already exists."
                except Exception as e:
                    response = f"550 Create directory operation failed. {e}"

            elif command == 'RMD':
                try:
                    os.rmdir(args[0])
                    response = "250 Directory removed."
                except Exception as e:
                    response = f"550 Remove directory operation failed. {e}"

            elif command == 'PASV':
                # This is a simplified version, actual PASV command handling requires opening a new port for data transfer
                response, pasv_socket = handle_pasv()

            elif command == 'LIST':
                try:
                    listing = os.listdir('.')
                    response = "\n".join(listing)
                except Exception as e:
                    response = f"550 Failed to list directory. {e}"

            elif command == 'RETR':       
                try:     
                    filename = ' '.join(args)  # Assuming filename is the rest of the command
                    if '..' in filename:
                        raise ValueError("Invalid filename")
                    response = handle_retr(filename, pasv_socket, connection)
                except ValueError as ve:
                    respone = f"501 {ve}"
                except Exception as e:
                    response = f"550 Retrieve operation failed. {e}"
                    
            elif command == 'DELE':
                try:
                    os.remove(args[0])
                    response = "250 File deleted."
                except Exception as e:
                    response = f"550 Delete operation failed. {e}"
            elif command == 'STOR':
                try:
                    filename = ' '.join(args)
                    if '..' in filename:
                        raise ValueError("Invalid filename")
                    response = handle_stor(filename, pasv_socket, connection)
                except ValueError as ve:
                    response = f"501 {ve}"
                except Exception as e:
                    response = f"550 Store operation faliled {e}"

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

            elif command == 'TYPE':
                global transfer_type
                try:
                    new_type = args[0]
                    if new_type in ['stream', 'block', 'compressed']:
                        transfer_type = new_type
                        response = f"200 OK. Data transfer mode set to {transfer_type}"
                    else:
                        response = "504 Invalid mode. Supported modes: stream, block, compressed"
                except Exception as e:
                    response = f"500 Error setting transfer type. {e}"

            elif command == 'MODE':
                global transfer_mode
                try:
                    new_mode = args[0]
                    if new_mode in ['binary', 'ascii']:
                        transfer_mode = new_mode
                        response = f"200 OK. Data transfer mode set to {transfer_mode}"
                    else:
                        response = "504 Invalid mode. Supported modes: binary, ascii"
                except Exception as e:
                    response = f"500 Error setting data transfer mode. {e}"

            elif command == 'STRU':
                global data_structure
                try:
                    new_stru = args[0]
                    if new_stru in ['file', 'record']:
                        data_structure = new_stru
                        response = f"200 OK. Data transfer mode set to {data_structure}"
                    else:
                        response = "504 Invalid mode. Supported modes: binary, ascii"
                except Exception as e:
                    response = f"500 Error setting file structure. {e}"

            elif command == 'QUIT':
                response = "221 Goodbye."
                break
            else:
                response = "502 Command not implemented."

            connection.sendall(response.encode())
    
    finally:
        connection.close()

def start_ftp_server(address='127.0.0.1', port=21):
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
