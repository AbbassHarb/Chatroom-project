import socket
import threading
import message_handler
from CONSTANTS import MessageType

clients = {}
client_seq_nums = {}  # Sequence numbers for sending messages to clients
server_seq_nums = {}  # Sequence numbers for receiving messages from clients
rooms = {}  # Dictionary to manage rooms and their members


def return_command_code(command):
    if command["content"] == "qqq":
        return 1


def handle_client(client_socket, address):
    print(f"\nAccepted connection from {address}")
    print(f"\nCurrent active threads: {threading.active_count()}")

    client_seq_nums[client_socket] = 0
    server_seq_nums[client_socket] = 0

    message_handler.send_message(
        client_socket,
        MessageType.INFO,
        "Choose a username:",
        client_seq_nums[client_socket],
    )
    client_seq_nums[client_socket] += 1

    message = message_handler.receive_message(
        client_socket, server_seq_nums[client_socket]
    )
    server_seq_nums[client_socket] += 1
    if message and message["type"] == MessageType.RESP.value:
        username = message["content"].strip()
    else:
        raise ValueError("Invalid username response")

    print(f"\n{address} chose username: {username}")
    clients[client_socket] = username

    current_room = None

    try:
        while True:
            message = message_handler.receive_message(
                client_socket, server_seq_nums[client_socket]
            )
            if not message:
                break

            server_seq_nums[client_socket] += 1

            if message["type"] == MessageType.COMMAND.value:
                command_content = message["content"].strip()
                if command_content.startswith('/create'):
                    room_id = f"room_{len(rooms) + 1}"
                    rooms[room_id] = [client_socket]
                    current_room = room_id
                    message_handler.send_message(
                        client_socket,
                        MessageType.RESP,
                        f"Created and joined room {room_id}",
                        client_seq_nums[client_socket],
                    )
                    client_seq_nums[client_socket] += 1
                elif command_content.startswith('/join'):
                    _, room_id = command_content.split()
                    if room_id in rooms:
                        rooms[room_id].append(client_socket)
                        current_room = room_id
                        message_handler.send_message(
                            client_socket,
                            MessageType.RESP,
                            f"Joined room {room_id}",
                            client_seq_nums[client_socket],
                        )
                        client_seq_nums[client_socket] += 1
                    else:
                        message_handler.send_message(
                            client_socket,
                            MessageType.RESP,
                            "Room does not exist",
                            client_seq_nums[client_socket],
                        )
                        client_seq_nums[client_socket] += 1
                else:
                    code = return_command_code(message)
                    print(f"\n command code {code}")
                    if code == 1:
                        message_handler.send_message(
                            client_socket,
                            MessageType.RESP,
                            1,
                            client_seq_nums[client_socket],
                        )  # command success
                        client_seq_nums[client_socket] += 1
                        break
            else:
                if current_room:
                    print(
                        f"\nReceived from {username} ({address}) in room {current_room}: {message['content']} received at {message['time_sent']}"
                    )
                    broadcast(message["content"], username, current_room)
                    message_handler.send_message(
                        client_socket, MessageType.RESP, 0, client_seq_nums[client_socket]
                    )  # message success
                    client_seq_nums[client_socket] += 1
                else:
                    message_handler.send_message(
                        client_socket,
                        MessageType.RESP,
                        "You are not in a room. Use /create or /join to enter a room.",
                        client_seq_nums[client_socket],
                    )
                    client_seq_nums[client_socket] += 1
    except ValueError as ve:
        print(f" Value Error: {ve}, user disconnected")
        message_handler.send_message(
            client_socket, MessageType.RESP, 2, client_seq_nums[client_socket]
        )  # checksum catchall error
        client_seq_nums[client_socket] += 1
    except Exception as e:
        print(
            f"Exception in thread {threading.current_thread().name} ({username}): {e}"
        )
        message_handler.send_message(
            client_socket, MessageType.RESP, 4, client_seq_nums[client_socket]
        )  # default catchall error
        client_seq_nums[client_socket] += 1
    finally:
        if current_room and client_socket in rooms.get(current_room, []):
            rooms[current_room].remove(client_socket)
        client_socket.close()
        del clients[client_socket]
        del client_seq_nums[client_socket]
        del server_seq_nums[client_socket]
        print(f"Connection with {username} ({address}) closed.")


def broadcast(content, username, room_id):
    for client in rooms.get(room_id, []):
        message_handler.send_message(
            client,
            MessageType.MESSAGE,
            f"{username}: {content}",
            client_seq_nums[client],
        )
        client_seq_nums[client] += 1


def main():
    host = "127.0.0.1"
    port = 5554

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"\nServer listening on {host}:{port}")

    while True:
        client_socket, address = server_socket.accept()
        client_thread = threading.Thread(
            target=handle_client, args=(client_socket, address)
        )
        client_thread.start()


if __name__ == "__main__":
    main()
