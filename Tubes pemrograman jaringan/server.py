import socket
import threading
from datetime import datetime
import os
import sys

def _handle_client_disconnection(connection, client_name, error_message, users_table, users_last_message):
    if connection in users_table:
        print(f'{_get_current_time()} {client_name} disconnected.')
        del users_table[connection]
        users_last_message.pop(connection)
        connection.close()
    else:
        print(f'{_get_current_time()} {client_name} left the room !!')

    if "forcibly closed by the remote host" not in error_message:
        print(f"Error: {error_message}")

def forward_file(sender_connection, data, users_table):
    try:
        file_info, file_name, relative_folder, recipient_username = data.split(':', 4)[1:]
        file_size = int(file_info)

        if recipient_username.lower() == 'multicast':
            recipient_conns = [conn for conn in users_table if conn != sender_connection]
        else:
            recipient_conns = [conn for conn, username in users_table.items() if username == recipient_username]

        if not recipient_conns:
            print(f"{_get_current_time()} Error saat meneruskan file: {recipient_username} is not connected.")
            return

        file_info = f"{file_size}:{file_name}:{relative_folder}"
        for recipient_conn in recipient_conns:
            recipient_conn.sendall(bytes(f'file:{file_info}:{recipient_username}', encoding='utf-8'))

        received_bytes = 0
        while received_bytes < file_size:
            file_data = sender_connection.recv(4096)
            if not file_data:
                break

            for recipient_conn in recipient_conns:
                recipient_conn.sendall(file_data)

            received_bytes += len(file_data)

            # Calculate and display loading percentage
            loading_percentage = min(100, int(received_bytes / file_size * 100))
            sys.stdout.write(f"\rFile sedang dikirimkan ke {recipient_username}: {loading_percentage}%")
            sys.stdout.flush()
        print(f"\nFile {file_name} berhasil dikirimkan ke {recipient_username}")
    except Exception as e:
        print(f"{_get_current_time()} Error saat meneruskan file: {str(e)}")
    finally:
        return

def send_private_message(sender, recipient, message, users_table):
    for conn, username in users_table.items():
        if username == recipient:
            data = f'(unicast): {users_table[sender]} : {message}'
            conn.sendall(bytes(data, encoding='utf-8'))
            return

def broadcast(message, owner, users_table):
    for conn in users_table:
        if conn != owner:
            data = f'{_get_current_time()} {users_table[owner]}: {message}'
            conn.sendall(bytes(data, encoding='utf-8'))

def _get_current_time():
    return datetime.now().strftime("%H:%M:%S")

def setup_server():
    users_table = {}
    users_last_message = {}

    socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('192.168.43.185', 13375)  # Ganti dengan alamat IP lokal mesin server
    socket_server.bind(server_address)
    socket_server.setblocking(1)
    socket_server.listen(10)
    print('Starting up on {} port {}'.format(*server_address))
    
    while True:
        connection, _ = socket_server.accept()
        threading.Thread(target=_on_new_client, args=(connection, users_table, users_last_message)).start()

def _on_new_client(connection, users_table, users_last_message):
    try:
        client_name = connection.recv(64).decode('utf-8')
        users_table[connection] = client_name
        users_last_message[connection] = False
        print(f'{_get_current_time()} {client_name} bergabung ke chat !!')

        while True:
            data = connection.recv(1024).decode('utf-8')
            if data != '':
                if data.startswith('unicast'):
                    _,recipient, message = data.split(':', 2)
                    send_private_message(connection, recipient, message, users_table)
                    print(f'{_get_current_time()} {client_name}:{message}')
                elif data.startswith('file:'):
                    forward_file(connection, data, users_table)
                else:
                    broadcast(data, owner=connection, users_table=users_table)
            else:
                return
    except Exception as e:
        _handle_client_disconnection(connection, client_name, str(e), users_table, users_last_message)

if __name__ == "__main__":
    setup_server()
