import socket
import os

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
            elif command.lower().startswith('stor'):
                filename = command.split(maxsplit=1)[1] if ' ' in command else ''
                if os.path.exists(filename):
                    clientSocket.sendall(command.encode())  # Send STOR command with filename
                    server_response = clientSocket.recv(1).decode()  # Wait for server acknowledgment
                    if server_response == '1':
                        with open(filename, 'rb') as file:
                            data = file.read(1024)
                            while data:
                                clientSocket.sendall(data)
                                data = file.read(1024)
                        print('File uploaded successfully.')
                    else:
                        print('Server refused to accept the file.')
                else:
                    print(f'File {filename} does not exist.')

            # For downloading a file from the server (RETR)
            elif command.lower().startswith('retr'):
                clientSocket.sendall(command.encode())  # Send RETR command with filename
                server_response = clientSocket.recv(1).decode()  # Wait for server to confirm file exists
                if server_response == '1':
                    filename = command.split(maxsplit=1)[1] if ' ' in command else ''
                    with open(filename, 'wb') as file:
                        while True:
                            data = clientSocket.recv(1024)
                            if not data:
                                break  # File transfer done
                            file.write(data)
                    print('File downloaded successfully.')
                else:
                    print('File does not exist on server.')

            else:
                # Send any other command and display the response
                response = send_command(clientSocket, command)
                print(response)

if __name__ == "__main__":
    main()
