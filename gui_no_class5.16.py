import socket,select
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
import pyaudio as pa
import wave
import pickle

# 可select的队列
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
    tcp_mss = 65495 #  tcp最大包  有用参数
    global_file_seg = 5000
    def mess_len_send(self,mess):  # 获取发送的包的长度,然后发送
        length = struct.pack('i',len(mess))
        self.sock.send(length)
        return length

    def sock_close(self,win):
        if self.sock_sate.isSet():
            self.sock_sate.clear()
            self.sock.close()
            win.destroy()
            self.destroy_queue.put(-1)
            self.video_end=1

    def mess_len_get(self):  # 获取需要接收的包的长度
        try :
            raw_len = self.sock.recv(4)
        except:
            return 0
        if len(raw_len) == 0:
            print('here')
            return 0
        (length,) = struct.unpack('i',raw_len)
        return length

    def json_encode_send(self,num,data):  # 将data打包成json格式,添加到对应队列
        json_data = {'type':str(num),'data':data}
        self.send_queue_list[num].put(json.dumps(json_data).encode('utf-8'))

    def video_byte_send(self,data):
        self.send_queue_list[3].put(data)

    def mess_send(self):
        while self.sock_sate.isSet():
            can_read,_,_ = select.select(self.send_queue_list,[],[],0.05)  # 可以发送的数据
            for i in can_read:
                send_data=i.get()
                self.mess_len_send(send_data)
                self.sock.sendall(send_data)

    def mess_recv(self):  # 接收数据
        while self.sock_sate.isSet():
            length = self.mess_len_get()
            if length == 0:
                mess_info = tk.Toplevel()
                tk.Label(mess_info, text='connection off', width=30, height=2).pack()
                tk.Button(mess_info,text='ok',width=20,height=2,command=lambda : self.sock_close(mess_info)).pack()
                return
            raw_data = b''
            totoal_length = length
            try:
                while length>self.tcp_mss :  # 处理大于tcp_mss的情况
                    raw_data += self.sock.recv(self.tcp_mss)
                    length -= self.tcp_mss
                if length!=0:
                    raw_data += self.sock.recv(length)
            except:
                self.sock_close()
                return
            if raw_data[totoal_length-1] == 118:
                self.recv_queue_list[1].put(raw_data[0:totoal_length-1])
                continue
            try:
                temp_data=raw_data.decode('utf-8')
            except:
                pass
            try:
                recv_data = json.loads(temp_data)  # 解析为str
            except:  # 查错
                print('error')
                print('data length:', length)
                print('true len: ', len(raw_data))
                print('raw_data: ',raw_data)
                print('decode data', temp_data)
            data_type = recv_data['type']  # 数据类型
            data = recv_data['data']  # 数据本身
            if data_type == '0':  # 送至不同函数进行处理
                self.control(data)
            elif data_type == '1':  # 文字信息
                self.text_recv_show(data,2)
            elif data_type == '2':  # 文件信息 base64
                self.recv_queue_list[0].put(data)
            elif data_type == '3':  # 视频信息
                self.recv_queue_list[1].put(data)
            elif data_type == '4':  # 音频信息
                self.recv_queue_list[2].put(data)

    def control(self, data): # 针对控制信息进行处理
        trans_type = data['trans_type']  # 控制类型
        trans_command = data['trans_command']  # 控制命令
        if trans_type == 'file':
            if trans_command == 'start':
                file_len = data['file_len']  # 文件长度
                file_name = data['file_name']  # 文件名
                self.call_queue.put({'num':self.func_count,'func':self.call_file_recv})  # 启用gui,就画个框,没啥用
                self.func_args[self.func_count]=file_name  # gui传参
                file_recv_thread = threading.Thread(target=self.file_recv,args=(self.func_count,file_name,file_len))  # 启用文件接收线程
                self.func_count += 1  # 计数器+1,计数器目的是为了唯一标定一个窗口,方便打开,关闭,传参数
                file_recv_thread.start()
        elif trans_type == 'video':
            if trans_command == 'start': #  视频功能  对面传来请求,这边需要接收也需要发送,因此调用发送给,发送函数中会调用接收
                self.call_queue.put({'num':self.func_count,'func':self.video_accept_window})
                self.func_count+=1
            elif trans_command == 'accept':
                video_send_thread = threading.Thread(target=self.call_video_send,args=(0,))
                video_send_thread.start()
            elif trans_command == 'reject':
                return
            elif trans_command == 'end':
                self.video_end = 1

    def audio_send(self):  # 音频发送 单独线程
        if(self.choose == 2):  #这个目的是为避免测试时同时调用,引发bug
            return
        CHUNK = 4096
        FORMAT = pa.paInt16
        CHANNELS = 2
        RATE = 16000
        p = pa.PyAudio()
        stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,input=True,frames_per_buffer=CHUNK)
        while not self.video_end:
            frame = stream.read(CHUNK)
            self.json_encode_send(4,base64.b64encode(frame).decode('utf-8'))
        stream.stop_stream()
        stream.close()
        p.terminate()

    def audio_recv(self): # 音频接收  单独线程
        if(self.choose == 1):
            return
        CHUNK = 4096
        FORMAT = pa.paInt16
        CHANNELS = 2
        RATE = 16000
        # RECORD_SECONDS = 0.05
        p = pa.PyAudio()
        stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,output=True,frames_per_buffer=CHUNK)
        while not self.video_end:
            if not self.recv_queue_list[2].empty():
                frame = self.recv_queue_list[2].get()
                audio_data = base64.b64decode(frame.encode('utf-8'))
                stream.write(audio_data,CHUNK)
                # print('audio_recv')
        stream.stop_stream()
        stream.close()
        p.terminate()

    def video_accept_reject(self,t,num):
        if t == 1:
            con_data = {'trans_type': 'video', 'trans_command': 'accept'}
            self.json_encode_send(0,con_data)
            self.call_video_send(0)
        elif t == 0:
            con_data = {'trans_type': 'video', 'trans_command': 'reject'}
            self.json_encode_send(0,con_data)
        self.destroy_queue.put(num)

    def video_accept_window(self,num):
        accept_inquire_window = tk.Toplevel()
        accept_inquire_window.geometry("200x300")
        tk.Label(accept_inquire_window,text='Video Request')
        accept = tk.Button(accept_inquire_window,text='yes',command=lambda : self.video_accept_reject(1,num))
        reject = tk.Button(accept_inquire_window,text='no',command=lambda : self.video_accept_reject(0,num))
        accept.pack()
        reject.pack()
        return accept_inquire_window

    def call_video_send(self,con=1):  # 启动视频程序
        if con : # 主动请求
            con_data = {'trans_type':'video','trans_command':'start'}  # 发送相应数据
            # self.send_queue_list[0].put(con_data)
            self.json_encode_send(0,con_data)
            return
        print('call send')
        self.other_args['video_speed'] = 0
        self.video_end = 0 # 标记,video_end = 1所有与视频有关的功能退出
        video_send_thread = threading.Thread(target=self.video_send)  # 视频发送线程
        video_send_thread.start()
        audio_send_thread = threading.Thread(target=self.audio_send)  # 音频发送线程
        audio_recv_thread = threading.Thread(target=self.audio_recv)  # 音频接收线程
        audio_send_thread.start()
        audio_recv_thread.start()
        # self.call_video_recv()
        self.call_queue.put({'num':self.func_count,'func':self.call_video_recv})  # 启动视频接收gui
        self.func_count+=1

    def video_send(self):  # 视频发送程序  需改进 加入速度控制
        # cap = cv.VideoCapture("D:\\北斗创新导航\\submit\\路演视频.flv")  # 本地视频
        if self.choose == 1:
            cap = cv.VideoCapture(0)  # 启动摄像头
        while not self.video_end:
            if self.other_args['video_speed'] == 1:
                continue # 这个地方可能会造成循环降低效率,可以通过event优化掉
            self.other_args['video_speed'] = 1
            if self.choose == 2:  # 避免单机重复调用
                return
            else:
                ret,frame = cap.read()  # 获取一帧
            if ret:
                img = Image.fromarray(cv.cvtColor(frame,cv.COLOR_BGR2RGBA))
                byte_frame = pickle.dumps(img)
                self.video_byte_send(byte_frame+b'v') # v做标识符
        cap.release()
    
    def hang_off_video(self,window):
        self.video_end=1
        window.destroy()
        con_data = {'trans_type':'video','trans_command':'end'}
        self.json_encode_send(0,con_data)

    def call_video_recv(self,num):  # 视频接收gui
        print('call_video_recv')
        window = tk.Toplevel()  # 窗口
        print('call_video_recv2345')
        window.title('video')
        labelPic = tk.Label(window)#,height=self.video_window_height,width=self.video_window_width)
        labelPic.pack()
        # print('call_video_recv_win')
        tk.Button(window, text='hang off', width=20, height=2, command=lambda : self.hang_off_video(window)).pack()
        window.after(5, lambda: self.video_recv(window,labelPic,num))  # 通过定时器 以轮询的方式刷新画面

    def video_recv(self,win,labelPic,num): # 画面刷新   需改进速度
        # print('show func')
        if self.video_end: # 退出
            mess_info = tk.Toplevel()
            tk.Label(mess_info, text='hung off', width=30, height=2).pack()
            tk.Button(mess_info,text='ok',width=20,height=2,command=mess_info.destroy).pack()
            win.destroy()
            self.destroy_queue.put(num)
            return
        self.other_args['video_speed'] = 0  # 控制视频速度,播放一帧发送一帧
        if self.recv_queue_list[1].empty():
            win.after(5, lambda: self.video_recv(win, labelPic,num))
            return
        byte_data =self.recv_queue_list[1].get()
        temp_img = pickle.loads(byte_data)
        self.img_tk = ImageTk.PhotoImage(image=temp_img)
        labelPic.configure(image=self.img_tk)
        win.after(5, lambda: self.video_recv(win, labelPic, num))

    def pic_resize(self,img):  # 图片大小调节,未启用
        temp_img = Image.fromarray(img)
        tk_img = ImageTk.PhotoImage(image=temp_img)
        return tk_img

    def call_file_recv(self,func_num):  # 调用文件接收 再control函数中被启动
        file_name = self.func_args.pop(func_num) # 获取参数
        file_recv_window = tk.Toplevel() #显示窗口
        file_recv_window.title('file receiving')
        file_recv_window.geometry('100x50')
        show_label = tk.Label(file_recv_window,text='File: '+file_name+' is receving')
        show_label.pack()
        return file_recv_window # 将窗口返回方便关闭

    def file_recv(self,func_num,file_name,file_len):
        cur_len = 0 # 文件已接收长度
        with open(file_name,'wb') as f:  # 打开文件
            while cur_len<file_len :
                if not self.recv_queue_list[0].empty():  # 有能接收的东西
                    data = self.recv_queue_list[0].get()
                    cur_len += data['cur_len']
                    f.write(base64.b64decode(data['content'].encode('utf-8'))) # 解码写入文件

        self.destroy_queue.put(func_num)  # 关闭窗口

    def call_file_send(self):  # 用户点击按钮 启动发送
        file_send_window = tk.Toplevel()  # 显示窗口
        file_send_window.wm_attributes('-topmost',1)
        file_send_window.title('file send')
        file_send_window.geometry('200x100')
        file_path_label = tk.Label(file_send_window,text='file path')
        file_path_entry = tk.Entry(file_send_window)
        file_send_button = tk.Button(file_send_window,text='send',width=10,height=2,command=lambda : self.file_send(file_send_window,file_path_entry.get()))
        file_path_label.pack()
        file_path_entry.pack()
        file_send_button.pack()
        # send button 点击后调用发送功能
        # file_send_window.destroy()
        # print('call file successful')

    def file_send_window(self):  # 发送中显示的窗口
        file_sending_window = tk.Toplevel()
        file_sending_window.wm_attributes('-topmost',1)
        file_sending_window.title('sending file')
        file_sending_window.geometry('200x100')
        file_sending_label = tk.Label(file_sending_window,text='sending')
        file_sending_label.pack()
        return file_sending_window

    def file_send(self,win,file_path): #  文件发送, 运行在主线程
        print('file_send',file_path)
        f = open(file_path,'rb')
        file_sending_window = self.file_send_window()# 显示窗口
        file_sending_window.update()  # 刷新一下窗口,可能不刷新显示太慢
        if not f:
            print('file cannot open')
            return
        file_name = os.path.basename(file_path)
        file_len = os.path.getsize(file_path)
        con_data = {'trans_type':'file','trans_command':'start','file_name':file_name,'file_len':file_len}
        self.json_encode_send(0,con_data)  # 发送请求
        cur_len = 0
        print('here')
        while cur_len<file_len:  # 按照 cur_len长度打包
            if file_len-cur_len>self.global_file_seg:
                per_len = self.global_file_seg
            else :
                per_len = file_len-cur_len
            file_data = f.read(per_len)
            send_data = {'cur_len':per_len,'content':base64.b64encode(file_data).decode('utf-8')}
            self.json_encode_send(2,send_data)
            cur_len += per_len
        f.close()
        file_sending_window.destroy()
        win.destroy()
        # 发送结束,关闭这两个窗口

    def login(self):  # 登录界面  需要修改
        log_win = tk.Tk()
        log_win.title('login')
        log_win.geometry('400x250')
        log_win.protocol('WM_DELETE_WINDOW',lambda : exit(0))
        addr_str = tk.StringVar()
        port_str = tk.StringVar()
        name_str = tk.StringVar()
        addr_lable = tk.Label(log_win, text='IP address:', width=30, height=2)
        port_lable = tk.Label(log_win, text='port:', width=30, height=2)
        ser_cli_lable = tk.Label(log_win, text='Mode:', width=30, height=2)
        addr_entry = tk.Entry(log_win,textvariable=addr_str)
        port_entry = tk.Entry(log_win,textvariable=port_str)
        name_entry = tk.Entry(log_win,textvariable=name_str)
        name_lable = tk.Label(log_win,text='Name:',width=30,height=2)
        choose = tk.StringVar()
        choose.set('c')
        ser_check = tk.Radiobutton(log_win, text='Server', variable=choose, value='s')
        cli_check = tk.Radiobutton(log_win, text='Client', variable=choose, value='c')
        quit_button = tk.Button(log_win, text='quit', width=10, height=2, command=lambda : exit(0))
        confirm_button = tk.Button(log_win,text='enter',width=10,height=2,command=lambda : self.confirm(addr_str,port_str,choose,name_str,log_win))
        
        addr_lable.grid(row=0)
        addr_entry.grid(row=0,column=1)
        port_lable.grid(row=1)
        port_entry.grid(row=1,column=1)
        name_lable.grid(row=2)
        name_entry.grid(row=2,column=1)
        ser_cli_lable.grid(row=3)
        ser_check.grid(row=3,column=1,sticky = "w"+"N")
        cli_check.grid(row=3,column=1,sticky = "E"+"N")
        confirm_button.grid(row=4)
        quit_button.grid(row=4,column=1)
        log_win.mainloop()
        log_win.destroy()

    def connection_exit(self):
        self.connection_end=1
        exit(0)

    def connection(self):  # 进行socket连接处理
        if self.choose == 1:
            listen_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            listen_sock.bind(((self.ip_addr,self.tcp_port)))
            listen_sock.listen(1)
            self.connection_end = 0
            win = tk.Tk()
            win.title('listening')
            win.geometry('300x100')
            win.protocol('WM_DELETE_WINDOW',self.connection_exit)
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

    def connect_window(self,window,listen_sock): #  对于监听模式 需要单独开一个线程处理,不过这个实现不好,不应该用多线程,应使用after方法,还没改
        while not self.connection_end:
            ls_scok_list,_,_ = select.select([listen_sock],[],[],0.05)
            for ls_scok in ls_scok_list:
                print(ls_scok)
                self.sock,addr = ls_scok.accept()
                self.peer_name = self.sock.recv(1000).decode('utf-8')
                print('peer_name ',self.peer_name)
                self.sock.send(self.cur_name.encode('utf-8'))
                self.connection_end=1
                window.quit()

    def text_send(self,str):  # 发送文字
        send_str = str.get('0.0','end')  # 获取文字
        str.delete('0.0', 'end')
        check = 1
        for c in send_str:  # 空信息不发送
            if c != '\n' and c != ' ':
                check = 0
                break
        if check:
            return
        # self.send_queue_list[1].put(send_str)
        self.json_encode_send(1,send_str)
        print(send_str)
        self.text_recv_show(send_str,1)

    def text_recv_show(self,show_str,user):  # 文字接收并显示  虽然是多线程(mess_recv中),但是目前没bug
        if user == 1:
            show_str = self.cur_name+':'+show_str
        elif user == 2:
            show_str = self.peer_name+':'+show_str
        self.recv_text.config(state="normal")
        self.recv_text.insert('end',show_str)
        self.recv_text.config(state="disabled")
    
    def main_pro_exit(self):
        self.sock_lock.acquire()
        if self.sock_sate.isSet():
            self.sock_sate.clear()
            self.video_end=1
            self.sock.shutdown(2)
        # self.sock.close()
        self.destroy_queue.put(-1)
        print('in exit func')
        self.sock_lock.release()

    def main_window(self):
        self.root = tk.Tk()
        self.root.geometry('600x450')
        self.root.protocol('WM_DELETE_WINDOW',self.main_pro_exit)
        self.recv_text = tk.Text(self.root)
        self.send_text = tk.Text(self.root,height=6)
        self.recv_text.config(state="disabled")
        self.file_send_button = tk.Button(self.root,text='file',width=20,height=2,command=self.call_file_send)
        send_button = tk.Button(self.root,text='send>',width=20,height=2,command=lambda : self.text_send(self.send_text))
        video_button = tk.Button(self.root,text='video',width=20,height=2,command=self.call_video_send)
        self.recv_text.grid(row=0,columnspan=4)
        self.send_text.grid(row=1,columnspan=4)

        video_button.grid(row=2)
        self.file_send_button.grid(row=2,column=1)
        send_button.grid(row=2,column=2)
        tk.Button(self.root, text='quit', width=20, height=2, command=self.main_pro_exit).grid(row=2,column=3)
        
        self.root.after(10,self.call_destroy_window)  # 定时器
        self.root.mainloop()
        print('main_window')

    def call_destroy_window(self): # 这个函数更改了新窗口显示,原先是多线程直接开一个,这个是在主线程中在root上面显示新窗口
        try:  # 队列中可能没东西,这个是阻塞的取东西
            func_info=self.call_queue.get_nowait() # 需要打开的窗口
            func = func_info['func'] # 窗口函数,可以直接传
            self.window_map[func_info['num']] = func(func_info['num']) # num就是那个计数器唯一表示了一个窗口,把窗口存起来,方便之后关闭
        except:  # 没东西就退出
            pass
        try:
            win_info=self.destroy_queue.get_nowait()  # 去除需要关闭的窗口的num
            if win_info == -1:
                self.root.destroy()
            win = self.window_map.pop(win_info) # 取出窗口
            win.destroy()  # 关闭
        except:
            pass
        self.root.after(5,self.call_destroy_window)  # 定时器 刷新

    def confirm(self,addr,port,ser_cli,name,window): # 将log_in窗口中数据获取处理
        # cur_name 自己的名字 peer_name 对方的名字
        self.ip_addr = addr.get()
        if not re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", self.ip_addr):
            mess_info = tk.Toplevel()
            tk.Label(mess_info, text='IP invaild', width=30, height=2).pack()
            tk.Button(mess_info,text='ok',width=20,height=2,command=mess_info.destroy).pack()
            return 
        ip_port_format = (r"^(1(02[4-9]|0[3-9][0-9]|[1-9][0-9]{2})|[2-9][0-9]{3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$")
        if not re.match(ip_port_format,port.get()):
            mess_info = tk.Toplevel()
            tk.Label(mess_info, text='port invaild', width=30, height=2).pack()
            tk.Button(mess_info,text='ok',width=20,height=2,command=mess_info.destroy).pack()
            return 
        self.tcp_port = int(port.get())
        self.cur_name = name.get()
        if ser_cli.get() == 's':
            self.choose = 1
        elif ser_cli.get() == 'c':
            self.choose = 2
        window.quit()

    def __init__(self):   # 初始化函数
        self.sock_sate = threading.Event()
        # self.video_lock = threading.Lock()
        self.sock_lock = threading.Lock()
        self.video_end = 0
        self.img_tk=0
        self.call_queue=queue.Queue()
        self.destroy_queue=queue.Queue()
        self.window_map={}
        self.func_count = 0
        self.func_args={}
        self.other_args={}
        self.send_queue_list=[]
        self.recv_queue_list=[]
        for i in range(3):
            self.recv_queue_list.append(queue.Queue())
        for i in range(5):
            self.send_queue_list.append(PollableQueue())
        connection_ok = 0
        while(not connection_ok):
            self.login()
            try:
                print(self.ip_addr)
                print(self.tcp_port)
                print(self.choose)
                self.connection()
                connection_ok = 1
            except:
                mess_info = tk.Tk()
                tk.Label(mess_info, text='connection failed', width=30, height=2).pack()
                tk.Button(mess_info,text='ok',width=20,height=2,command=mess_info.destroy).pack()
                tk.mainloop()

        self.sock_sate.set()
        mess_send_thread = threading.Thread(target=self.mess_send)
        mess_recv_thread = threading.Thread(target=self.mess_recv)
        mess_send_thread.start()
        mess_recv_thread.start()
        self.main_window()


if __name__ == '__main__':
    a = chartroom()
    # print(threading.current_thread())
    print('exit')