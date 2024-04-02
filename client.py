import socket
import os

def send_command(client_socket, command):
    """
    Sends a command to the server and waits for a response.
    """
    client_socket.sendall(command.encode())
    response = client_socket.recv(1024).decode()
    print(response)
    return response

def authenticate(client_socket):
    """
    Function to send username and password to the server for authentication using USER and PASS commands.
    """
    username = input('Enter your username: ')
    send_command(client_socket, f"USER {username}")
    password = input('Enter your password: ')
    response = send_command(client_socket, f"PASS {password}")
    return response

def main():
    HOST = '127.0.0.1'  # The server's hostname or IP address
    PORT = 2121         # The port used by the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
        print("Connecting to {}:{}...".format(HOST, PORT))
        clientSocket.connect((HOST, PORT))

        # Authenticate with the server
        print("Authenticating...")
        if '230' not in authenticate(clientSocket):  # Assuming 230 response code for successful login
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

            # Special handling for RETR command (download)
            if command.lower().startswith('retr'):
                send_command(clientSocket, command)
                # Server should respond with port number for PASV mode (simplified scenario)
                data_port = int(clientSocket.recv(1024).decode())
                filename = command.split()[1]
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dataSocket:
                    dataSocket.connect((HOST, data_port))
                    with open(filename, 'wb') as file:
                        while True:
                            data = dataSocket.recv(4096)
                            if not data:
                                break
                            file.write(data)
                    print('File downloaded successfully.')
            else:
                # For all other commands, send and display the response
                response = send_command(clientSocket, command)

if __name__ == "__main__":
    main()
