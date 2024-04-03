import socket
import os

transfer_type = None
transfer_mode = None
data_structure = None

def send_command(client_socket, command):
    """
    Sends a command to the server and waits for a short response.
    """
    client_socket.sendall(command.encode())
    response = client_socket.recv(1024).decode()
    return response

def authenticate(client_socket):
    """
    Function to send username and password to the server for authentication using USER and PASS commands.
    """
    username = input('Enter your username: ')
    response = send_command(client_socket, f"USER {username}")
    print(response)
    password = input('Enter your password: ')
    response = send_command(client_socket, f"PASS {password}")
    print(response)
    return "230" in response  # Assuming 230 response code for successful login

def parse_pasv_response(response):
    """
    Parses the PASV response from the FTP server.
    Extracts and returns the data channel's IP address and port.
    """
    try:
        if isinstance(response, bytes):
            response = response.decode()

        # Example PASV response: "227 Entering Passive Mode (192,168,1,2,197,143)."
        parts = response.split('(')
        values = parts[1].strip(')').split(',')

        ip_address = '.'.join(values[:4])
        port = int(values[4].strip("b'")) * 256 + int(values[5].strip("b'"))

        return ip_address, port
    except Exception as e:
        print("Error parsing PASV response:", e)
        raise ValueError("Invalid PASV response format")

def setup_data_channel(client_socket):
    """
    Requests passive mode with PASV, parses the server's response,
    and establishes a connection to the data channel.
    """
    # Request passive mode
    pasv_response = send_command(client_socket, "PASV")
    print("Received PASV response:", pasv_response)
    
    # Parse the response to get IP and port
    ip_address, port = parse_pasv_response(pasv_response)
    
    # Connect to the data channel
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_socket.connect((ip_address, port))
    
    return data_socket

def execute_stor_command(client_socket, data_channel_socket, command):
    try:
        client_socket.sendall(command.encode())  # Send STOR command with filename
        server_response = client_socket.recv(1).decode()  # Wait for server acknowledgment
        if server_response == '1':
            filename = command.split(maxsplit=1)[1] if ' ' in command else ''
            with open(filename, 'rb') as file:
                data = file.read(1024)
                while data:
                    data_channel_socket.sendall(data)
                    data = file.read(1024)
            print('File uploaded successfully.')
        elif server_response == '0':
            print('Server refused to accept the file.')
        else:
            print("503 Bad sequence of commands. Set TYPE, MODE, and STRU before transfer.")
    except Exception as e:
        print(f'Error in STOR command: {e}')

def execute_retr_command(client_socket, data_channel_socket, command):
    try:
        client_socket.sendall(command.encode())  # Send RETR command with filename
        server_response = client_socket.recv(1024).decode()  # Wait for server to confirm file exists
        if server_response == '1':
            filename = command.split(maxsplit=1)[1] if ' ' in command else ''
            with open(filename, 'wb') as file:
                while True:
                    data = data_channel_socket.recv(1024)
                    if not data:
                        break  # File transfer done
                    file.write(data)
            print('File downloaded successfully.')
        elif server_response == '0':
            print('File does not exist on server.')
        else:
            print(server_response)
    except Exception as e:
        print(f'Error in RETR command: {e}')

def main():
    # Get server IP and Port from user input
    HOST = input('Enter the server IP address: ')  # The server's hostname or IP address
    PORT = int(input('Enter the server port: '))   # The port used by the server
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
        print(f"Connecting to {HOST}:{PORT}...")
        clientSocket.connect((HOST, PORT))

        # Authenticate with the server
        print("Authenticating...")
        if not authenticate(clientSocket):
            print('Authentication failed. Exiting.')
            return
        else:
            print('Authentication successful.')
        data_channel_socket = None
        # Command loop
        while True:
            command = input('Enter your command: ').strip()
            if not command:
                print("Please enter a valid command.")
                continue

            # Handle quit command locally to close the connection properly
            if command.lower() == 'quit':
                send_command(clientSocket, command)
                break

            # For uploading a file to the server (STOR)
            elif command.lower() == 'pasv':
                try:
                    # Setup the data channel
                    data_channel_socket = setup_data_channel(clientSocket)
                    print("Data channel set up successfully.")
                except Exception as e:
                    print(f"Error setting up data channel: {e}")

            elif command.lower().startswith('stor'):
                if data_channel_socket is None:
                    print("Data channel not set up. Please execute PASV command.")
                else:
                    execute_stor_command(clientSocket, data_channel_socket, command)

            # For downloading a file from the server (RETR)
            elif command.lower().startswith('retr'):
                if data_channel_socket is None:
                    print("Data channel not set up. Please execute PASV command.")
                else:
                    execute_retr_command(clientSocket, data_channel_socket, command)

            else:
                # Send any other command and display the response
                response = send_command(clientSocket, command)
                print(response)

if __name__ == "__main__":
    main()
