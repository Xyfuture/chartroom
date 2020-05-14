import multiprocessing as mp
import cv2 as cv
import socket
import numpy as np
import pickle
import struct

cap = cv.VideoCapture(0)


def f(conn):
    ret = 1
    while ret:
        ret,frame = cap.read()
        conn.send(frame)
        if(conn.recv()):
            break
    conn.close()


def trans(conn,sock):
    while True:
        img = conn.recv()
        # byte_img = cv.imencode('.png',img)[1]
        # trans_byte=np.array(byte_img)
        trans_byte=pickle.dumps(img)

        # print(img.shape)
        # print(type(byte_img))
        # byte_img = cv.imencode('jpg',img)[1]
        sock.send(struct.pack('i',len(trans_byte)))
        sock.sendall(trans_byte)
        conn.send(0)


if __name__ == "__main__":
    parent_conn,child_conn = mp.Pipe()
    p = mp.Process(target=f,args=(child_conn,))
    server_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_sock.bind((('0.0.0.0',12378)))
    server_sock.listen(1)
    client_sock,client_addr = server_sock.accept()
    print("client addr:",client_addr)
    print(client_sock.getsockname())
    p.start()
    trans(parent_conn,client_sock)
    p.join()
    # while True:
    #     frame = parent_conn.recv()
    #     cv.imshow('img',frame)
    #     if cv.waitKey(10)==ord('q'):
    #         parent_conn.send(1)
    #         break
    #     else:
    #         parent_conn.send(0)
    # parent_conn.close()
    # p.join()
