import socket
import tkinter as tk
import cv2 as cv
import threading
import multiprocessing as mp
import queue
import json
import re
import base64,struct
import os,sys
import time
import numpy
from PIL import Image,ImageTk

global_file_seg = 5000
test_img = 0

class PollableQueue(queue.Queue):
    def __init__(self):
        super().__init__()
        # Create a pair of connected sockets
        if os.name == 'posix':
            self._putsocket, self._getsocket = socket.socketpair()
        else:
            # Compatibility on non-POSIX systems
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            self._putsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._putsocket.connect(server.getsockname())
            self._getsocket, _ = server.accept()
            server.close()

    def fileno(self):
        return self._getsocket.fileno()

    def put(self, item):
        super().put(item)
        self._putsocket.send(b'x')

    def get(self):
        self._getsocket.recv(1)
        return super().get()


class chartroom:
    window_width = 500
    window_height= 700
    button_width=20
    button_height=2
    input_height=100
    input_width= 500
    output_height=500
    output_width=500
    video_window_width=100
    video_window_height=200

    def mess_len_send(self,mess):
        length = struct.pack('i',len(mess))
        self.sock.send(length)
        return length

    def mess_len_get(self):
        raw_len = self.sock.recv(4)
        (length,) = struct.unpack('i',raw_len)
        return length

    def mess_send(self):
        while True:
            for i in range(5):
                if not self.send_queue_list[i].empty():
                    send_data = {"type":str(i),"data":self.send_queue_list[i].get()}
                    json_data = json.dumps(send_data).encode('utf-8')
                    # print('send',send_data)
                    self.mess_len_send(json_data)
                    self.sock.sendall(json_data)

    def mess_recv(self):
        while True:
            length = self.mess_len_get()
            temp_data = self.sock.recv(length).decode('utf-8')
            # print('recv',temp_data+'\n')
            recv_data = json.loads(temp_data)
            data_type = recv_data['type']
            data = recv_data['data']
            if data_type == '0':
                self.control(data)
            elif data_type == '1':  # 文字信息
                self.text_recv_show(data,2)
            elif data_type == '2':  # 文件信息 base64
                self.recv_queue_list[0].put(data)
            elif data_type == '3':  # 视频信息
                self.recv_queue_list[1].put(data)
            elif data_type == '4':  # 音频信息
                self.recv_queue_list[2].put(data)

    def control(self, data):
        trans_type = data['trans_type']
        trans_command = data['trans_command']
        if trans_type == 'file':
            if trans_command == 'start':
                file_len = data['file_len']
                file_name = data['file_name']
                file_recv_thread = threading.Thread(target=self.call_file_recv,args=(file_name,file_len))
                file_recv_thread.start()
        elif trans_type == 'video':
            if trans_command == 'start':
                video_send_thread = threading.Thread(target=self.call_video_send,args=(0,))
                video_send_thread.start()
                print('command ok')

    def call_video_send(self,con=1):
        if con :
            con_data = {'trans_type':'video','trans_command':'start'}
            self.send_queue_list[0].put(con_data)
        self.video_end = 0
        video_send_thread = threading.Thread(target=self.video_send)
        video_send_thread.start()
        self.call_video_recv()


    def video_send(self):
        cap = cv.VideoCapture("D:\\北斗创新导航\\submit\\路演视频.flv")
        while not self.video_end:
            if self.choose == 2:
                ret = 0
            else:
                ret,frame = cap.read()
            if ret:
                byte_img = cv.imencode('.png',frame)[1]
                byte_array = numpy.array(byte_img)
                self.send_queue_list[3].put(base64.b64encode(byte_array.tostring()).decode('utf-8'))

    def call_video_recv(self):
        print('call_video_recv')
        window = tk.Tk()
        window.title('video')
        window.geometry(str(self.video_window_width)+'x'+str(self.video_window_height))
        labelPic = tk.Label(window)#,height=self.video_window_height,width=self.video_window_width)
        labelPic.pack()
        video_recv_thread = threading.Thread(target=self.video_recv,args=(window,labelPic))
        video_recv_thread.start()
        window.mainloop()
        window.destroy()

    def video_recv(self,win,labelPic):
        while not self.video_end:
            a = 0
            if not self.recv_queue_list[1].empty():
                self.video_lock.acquire()
                data = self.recv_queue_list[1].get()
                data = base64.b64decode(data.encode('utf-8'))
                cv_img = cv.imdecode(numpy.frombuffer(data,numpy.uint8),cv.IMREAD_COLOR)
                # cv.imshow('test',cv_img)
                # cv.waitKey(100)
                rgba_img = cv.cvtColor(cv_img,cv.COLOR_BGR2RGBA)
                # tk_img = self.pic_resize(rgba_img)
                temp_img = Image.fromarray(rgba_img)

                global test_img
                test_img = ImageTk.PhotoImage(image=temp_img, master=win)
                # tk_img = ImageTk.PhotoImage(image=temp_img,master=win)
                # labelPic.image = tk_img
                if a==0 :
                    labelPic.configure(image=test_img)
                else:
                    a=1
                self.video_lock.release()
                # print('successful')
        win.quit()

    def pic_resize(self,img):
        temp_img = Image.fromarray(img)
        temp_img.resize((self.video_window_width,self.video_window_height),Image.ANTIALIAS)
        tk_img = ImageTk.PhotoImage(image=temp_img)
        return tk_img

    def call_file_recv(self,file_name,file_len):
        file_recv_window = tk.Tk()
        file_recv_window.wm_attributes('-topmost',1)
        file_recv_window.title('file receiving')
        file_recv_window.geometry('100x50')
        show_label = tk.Label(file_recv_window,text='File: '+file_name+' is receving')
        show_label.pack()
        file_recv_thread = threading.Thread(target=self.file_recv,args=(file_recv_window,file_name,file_len))
        file_recv_thread.start()
        file_recv_window.mainloop()
        file_recv_window.destroy()

    def file_recv(self,window,file_name,file_len):
        cur_len = 0
        print('file_len: ',file_len)
        with open(file_name,'wb') as f:
            while cur_len<file_len :
                # print('in file recv loop')
                if not self.recv_queue_list[0].empty():
                    data = self.recv_queue_list[0].get()
                    cur_len += data['cur_len']
                    f.write(base64.b64decode(data['content'].encode('utf-8')))
                    print('file recv')
        window.quit()

    def call_file_send(self):
        file_send_window = tk.Tk()
        file_send_window.wm_attributes('-topmost',1)
        file_send_window.title('file send')
        file_send_window.geometry('200x100')
        file_path_label = tk.Label(file_send_window,text='file path')
        file_path_entry = tk.Entry(file_send_window)
        file_send_button = tk.Button(file_send_window,text='send',width=10,height=2,command=lambda : self.file_send(file_send_window,file_path_entry.get()))
        file_path_label.pack()
        file_path_entry.pack()
        file_send_button.pack()
        file_send_window.mainloop()
        file_send_window.destroy()

    def file_send(self,window,file_path):
        print('file_send',file_path)
        f = open(file_path,'rb')
        if not f:
            print('file cannot open')
            window.quit()
            return
        file_name = os.path.basename(file_path)
        file_len = os.path.getsize(file_path)
        con_data = {'trans_type':'file','trans_command':'start','file_name':file_name,'file_len':file_len}
        self.send_queue_list[0].put(con_data)
        cur_len = 0
        print('here')
        while cur_len<file_len:
            if file_len-cur_len>global_file_seg:
                per_len = global_file_seg
            else :
                per_len = file_len-cur_len
            file_data = f.read(per_len)
            send_data = {'cur_len':per_len,'content':base64.b64encode(file_data).decode('utf-8')}
            self.send_queue_list[2].put(send_data)
            cur_len += per_len
        f.close()
        window.quit()

    def login(self):
        log_win = tk.Tk()
        log_win.title('login')
        log_win.geometry('300x500')
        addr_str = tk.StringVar()
        port_str = tk.StringVar()
        name_str = tk.StringVar()
        addr_lable = tk.Label(log_win, text='IP address', width=30, height=2)
        port_lable = tk.Label(log_win, text='port', width=30, height=2)
        ser_cli_lable = tk.Label(log_win, text='Mode', width=30, height=2)
        addr_entry = tk.Entry(log_win,textvariable=addr_str)
        port_entry = tk.Entry(log_win,textvariable=port_str)
        name_entry = tk.Entry(log_win,textvariable=name_str)
        name_lable = tk.Label(log_win,text='Name',width=30,height=2)
        choose = tk.StringVar()
        choose.set('c')
        ser_check = tk.Radiobutton(log_win, text='Server', variable=choose, value='s')
        cli_check = tk.Radiobutton(log_win, text='Client', variable=choose, value='c')
        quit_button = tk.Button(log_win, text='quit', width=10, height=2, command=log_win.quit)
        confirm_button = tk.Button(log_win,text='enter',width=10,height=2,command=lambda : self.confirm(addr_str,port_str,choose,name_str,log_win))
        addr_lable.pack()
        addr_entry.pack()
        port_lable.pack()
        port_entry.pack()
        name_lable.pack()
        name_entry.pack()
        ser_cli_lable.pack()
        ser_check.pack()
        cli_check.pack()
        quit_button.pack()
        confirm_button.pack()
        log_win.mainloop()
        log_win.destroy()

    def connection(self):
        if self.choose == 1:
            listen_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            listen_sock.bind(((self.ip_addr,self.tcp_port)))
            listen_sock.listen(1)
            win = tk.Tk()
            win.title('listening')
            win.geometry('100x60')
            label = tk.Label(win,text='Waiting for connection',width=20,height=2)
            label.pack()
            t1 = threading.Thread(target=self.connect_window,args=(win,listen_sock))
            t1.start()
            print('win main loop')
            win.mainloop()
            win.destroy()
            print('connection')
        elif self.choose == 2:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(((self.ip_addr,self.tcp_port)))
            self.sock.send(self.cur_name.encode('utf-8'))
            self.peer_name = self.sock.recv(1000).decode('utf-8')

    def connect_window(self,window,listen_sock):
        self.sock,addr = listen_sock.accept()
        self.peer_name = self.sock.recv(1000).decode('utf-8')
        print('peer_name ',self.peer_name)
        self.sock.send(self.cur_name.encode('utf-8'))
        window.quit()

    def text_send(self,str):
        send_str = str.get('0.0','end')
        str.delete('0.0', 'end')
        check = 1
        for c in send_str:
            if c != '\n' and c != ' ':
                check = 0
                break
        if check:
            return
        self.send_queue_list[1].put(send_str)
        print(send_str)
        self.text_recv_show(send_str,1)

    def text_recv_show(self,show_str,user):
        if user == 1:
            show_str = self.cur_name+':'+show_str
        elif user == 2:
            show_str = self.peer_name+':'+show_str
        self.recv_text.insert('end',show_str)

    def main_window(self):
        root = tk.Tk()
        # send_str = tk.StringVar()
        # recv_scrollbar = tk.Scrollbar(root)
        self.recv_text = tk.Text(root) #  ,yscrollcommand=recv_scrollbar.set)
        self.send_text = tk.Text(root) # ,textvariable=send_str)
        self.file_recv_button = tk.Button(root,text='file',command=self.call_file_send)
        send_button = tk.Button(root,text='send>',width=20,height=2,command=lambda : self.text_send(self.send_text))
        video_button = tk.Button(root,text='video',width=20,height=2,command=self.call_video_send)
        # recv_scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
        self.recv_text.pack()
        self.send_text.pack()
        video_button.pack()
        self.file_recv_button.pack()
        # recv_scrollbar.config(command=self.recv_text.yview)
        send_button.pack()
        root.mainloop()
        print('main_window')

    def confirm(self,addr,port,ser_cli,name,window):
        # cur_name 自己的名字 peer_name 对方的名字
        self.ip_addr = addr.get()
        self.tcp_port = int(port.get())
        self.cur_name = name.get()
        if ser_cli.get() == 's':
            self.choose = 1
        elif ser_cli.get() == 'c':
            self.choose = 2
        window.quit()

    def __init__(self):
        self.video_lock = threading.Lock()
        self.video_end = 0
        self.send_queue_list=[]
        self.recv_queue_list=[]
        for i in range(3):
            self.recv_queue_list.append(queue.Queue())
        for i in range(5):
            self.send_queue_list.append(queue.Queue())
        self.login()
        print(self.ip_addr)
        print(self.tcp_port)
        print(self.choose)
        self.connection()
        mess_send_thread = threading.Thread(target=self.mess_send)
        mess_recv_thread = threading.Thread(target=self.mess_recv)
        # mess_send_thread.start()
        mess_recv_thread.start()
        self.main_window()


if __name__ == '__main__':
    a = chartroom()
