import multiprocessing as mp
import socket
import cv2 as cv
import numpy as np
import pickle
import struct

buffer_size = 921600
tcp_mss = 65495
def video_recv(sock):
    while True:
        cur_len =0
        raw_length = sock.recv(4)
        (length,) = struct.unpack('i',raw_length)
        raw_data = b''
        while length>tcp_mss:
            raw_data+=sock.recv(tcp_mss)
            length-=tcp_mss
        if length:
            raw_data+=sock.recv(length)

        # byte_img = sock.recv(buffer_size)
        # print(byte_img)
        # img = np.fromstring(byte_img, np.uint8)
        # img = np.frombuffer(byte_img,np.uint8)
        img = pickle.loads(raw_data)
        # img=cv.imdecode(np.frombuffer(byte_img,np.uint8),cv.IMREAD_COLOR)
        print(img.shape)
        # print(type(img))
        # print(img)
        cv.imshow('test', img)
        cv.waitKey(10)

if __name__ == '__main__':
    client_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client_sock.connect((('127.0.0.1',12378)))
    client_sock.getpeername()
    print(client_sock.getpeername())
    video_recv(client_sock)
