from socket import *
import os
import json
import struct


server_socket = socket(AF_INET,SOCK_STREAM)
server_addr = (('0.0.0.0',8866))
buffer_size = 1024

server_socket.bind(server_addr)
server_socket.listen(10)
print('idle')

conn,client_addr = server_socket.accept()
print("client info:",client_addr)

file_path = input('enter the file path:\n')
print('here')
file_name = os.path.basename(file_path)
file_size = os.path.getsize(file_path)
if not file_name:
    print('file not exits')
    exit(0)
file_info = {'file_name':file_name,'file_size':file_size}
head_info = json.dumps(file_info)
head_len = struct.pack('i',len(head_info))
conn.send(head_len)
conn.send(head_info.encode('utf-8'))
ack = conn.recv(4)
if not ack:
    print('transport failed')
    exit(0)
with open(file_path,'rb') as f :
    acc = 0
    while acc<file_size:
        if acc+buffer_size<file_size:
            data = f.read(buffer_size)
        else:
            data = f.read(file_size-acc)
        conn.send(data)
        acc += buffer_size
print('file send finish')
server_socket.close()