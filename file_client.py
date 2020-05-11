from socket import *
import os
import json
import struct


client_socket = socket(AF_INET,SOCK_STREAM)
server_addr = (('127.0.0.1',8866))
buffer_size = 1024

client_socket.connect(server_addr)
print('connect to server')
header_len = client_socket.recv(4)
if header_len:
    print('connect successfully')
    client_socket.send(struct.pack('i',1))
header_len = struct.unpack('i',header_len)
header_info = client_socket.recv(header_len[0]).decode('utf-8')
header_info = json.loads(header_info)
file_name = header_info['file_name']
file_size = header_info['file_size']
recv_len = 0
with open(file_name, 'wb+') as f:
    while recv_len < file_size:
        if (recv_len+buffer_size)>file_size:
            data = client_socket.recv(file_size-recv_len)
        else:
            data = client_socket.recv(buffer_size)
        f.write(data)
        recv_len += buffer_size
print('received successfully')
client_socket.close()
