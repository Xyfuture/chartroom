import multiprocessing as mp
import socket
import cv2 as cv
import numpy as np


buffer_size = 3276800000


def video_recv(sock):
    while True:
        byte_img = sock.recv(buffer_size)
        # print(byte_img)
        # img = np.fromstring(byte_img, np.uint8)
        img=cv.imdecode(np.frombuffer(byte_img,np.uint8),cv.IMREAD_COLOR)
        # print(img.shape)
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
