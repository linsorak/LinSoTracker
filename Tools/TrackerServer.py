import socket


class TrackerServer:
    # https://codesource.io/creating-python-socket-server-with-multiple-clients/
    def __init__(self, port):
        host = "127.0.0.1"
        self.server_socket = socket.socket()

        try:
            self.server_socket.bind((host, port))
        except socket.error as e:
            print(str(e))
        print(f'Server is listing on the port {port}...')
        self.server_socket.listen()

    def multi_threaded_client(self, connection):
        connection.send(str.encode('Server is working:'))
        while True:
            data = connection.recv(2048)
            response = 'Server message: ' + data.decode('utf-8')
            if not data:
                break
            connection.sendall(str.encode(response))
        connection.close()