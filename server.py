import socket
import threading
import struct
import os

HOST = '127.0.0.1'
PORT = 12345

MSG_TYPE_TEXT = 1
MSG_TYPE_FILE = 2
MSG_TYPE_GIF = 3
MSG_TYPE_USERLIST = 4
MSG_TYPE_VOICE = 5

clients = []
users = {}  # username -> password
client_usernames = {}  # client_socket -> username

def broadcast(sender_socket, data):
    for client in clients:
        if client != sender_socket:
            try:
                client.sendall(data)
            except:
                clients.remove(client)

def send_user_list():
    user_list = ",".join(client_usernames.values()).encode()
    data = bytes([MSG_TYPE_USERLIST]) + struct.pack(">I", len(user_list)) + user_list
    for client in clients:
        try:
            client.sendall(data)
        except:
            clients.remove(client)

def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data.startswith("LOGIN:") or data.startswith("REGISTER:"):
                parts = data.split(":")
                command, username, password = parts[0], parts[1], parts[2]
                if command == "REGISTER":
                    if username in users:
                        client_socket.sendall("Username taken".encode())
                    else:
                        users[username] = password
                        client_socket.sendall("OK".encode())
                elif command == "LOGIN":
                    if users.get(username) == password:
                        client_usernames[client_socket] = username
                        clients.append(client_socket)
                        client_socket.sendall("OK".encode())
                        send_user_list()
                        break
                    else:
                        client_socket.sendall("Invalid credentials".encode())
    except:
        client_socket.close()
        return

    while True:
        try:
            msg_type_data = client_socket.recv(1)
            if not msg_type_data:
                break
            msg_type = msg_type_data[0]

            if msg_type == MSG_TYPE_TEXT:
                msg_len = struct.unpack(">I", client_socket.recv(4))[0]
                msg = client_socket.recv(msg_len).decode()
                full_msg = f"{client_usernames[client_socket]}: {msg}"
                send_data = bytes([MSG_TYPE_TEXT]) + struct.pack(">I", len(full_msg)) + full_msg.encode()
                broadcast(client_socket, send_data)

            elif msg_type == MSG_TYPE_FILE:
                name_len = struct.unpack(">I", client_socket.recv(4))[0]
                size = struct.unpack(">I", client_socket.recv(4))[0]
                name = client_socket.recv(name_len)
                content = b""
                while len(content) < size:
                    chunk = client_socket.recv(min(4096, size - len(content)))
                    if not chunk:
                        break
                    content += chunk
                send_data = bytes([MSG_TYPE_FILE]) + struct.pack(">I", len(name)) + struct.pack(">I", len(content)) + name + content
                broadcast(client_socket, send_data)

            elif msg_type == MSG_TYPE_GIF:
                url_len = struct.unpack(">I", client_socket.recv(4))[0]
                url = client_socket.recv(url_len)
                send_data = bytes([MSG_TYPE_GIF]) + struct.pack(">I", len(url)) + url
                broadcast(client_socket, send_data)

            elif msg_type == MSG_TYPE_VOICE:
                voice_data_len = struct.unpack(">I", client_socket.recv(4))[0]
                voice_data = client_socket.recv(voice_data_len)
                send_data = bytes([MSG_TYPE_VOICE]) + struct.pack(">I", len(voice_data)) + voice_data
                broadcast(client_socket, send_data)

        except Exception as e:
            print("Client error:", e)
            break

    if client_socket in clients:
        clients.remove(client_socket)
    if client_socket in client_usernames:
        del client_usernames[client_socket]
    send_user_list()
    client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_server()
