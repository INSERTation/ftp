import socket
import os

def authenticate(client_socket):
    """
    Function to send username and password to the server for authentication.
    """
    username = input('Enter your username: ')
    client_socket.sendall(username.encode())
    password = input('Enter your password: ')
    client_socket.sendall(password.encode())
    response = client_socket.recv(1024).decode()
    return response

def main():
    HOST = '127.0.0.1'  # The server's hostname or IP address
    PORT = 2121         # The port used by the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clientSocket:
        print("Connecting to {}:{}...".format(HOST, PORT))
        clientSocket.connect((HOST, PORT))

        # Authenticate with the server
        print("Authenticating...")
        auth_response = authenticate(clientSocket)
        if 'failed' in auth_response.lower():
            print('Authentication failed. Exiting.')
            return
        else:
            print(auth_response)  # Assuming the server sends back a success message

        # Command loop
        while True:
            command = input('Enter your command: ')
            clientSocket.sendall(command.encode())

            if command.lower() == 'quit':
                break

            # Special handling for download command
            if command.startswith('dwld'):
                data_port = int(clientSocket.recv(1024).decode())
                if data_port != 0:  # Assuming a non-zero port indicates a valid response
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dataSocket:
                        dataSocket.connect((HOST, data_port))
                        with open(os.path.join('.', command[5:]), 'wb') as file:
                            while True:
                                fileInfo = dataSocket.recv(4096)
                                if not fileInfo:
                                    break
                                file.write(fileInfo)
                        print('File downloaded successfully.')
                else:
                    print(clientSocket.recv(1024).decode())  # Error message from server
            else:
                # Handle regular response
                response = clientSocket.recv(1024).decode()
                print(response)

if __name__ == "__main__":
    main()
