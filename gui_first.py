import tkinter as tk
import cv2 as cv
from PIL import Image,ImageTk
import threading
import multiprocessing as mp
import sys
import queue


class ui_surface:
    window_width = 500
    window_height= 700
    button_width=100
    button_height=50
    input_height=300
    input_width=500
    output_height=400
    output_width=500


    def mess_send(self):
        for q in self.send_queue_list:
            if not q.empty():
                self.sock.send(q.get())

    def mess_recv(self):
        while True:
            mess = self.sock.recv()

    def login(self):


    def __init__(self):
        self.send_queue_list[5]
        self.recv_queue_list[5]
        for i in range(5):
            self.send_queue_list.append(queue.Queue())
        for i in range(5):
            self.recv_queue_list.append(queue.Queue())
