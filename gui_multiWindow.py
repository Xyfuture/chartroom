import tkinter as tk
import threading


def login_window():
    log_win = tk.Tk()
    log_win.title('login')
    log_win.geometry('500x300')
    addr_lable = tk.Label(log_win,text='IP address',width=30,height=2)
    port_lable = tk.Label(log_win,text='port',width=30,height=2)
    ser_cli_lable = tk.Label(log_win,text='Mode',width=30,height=2)
    addr_entry = tk.Entry(log_win)
    port_entry = tk.Entry(log_win)
    var = tk.StringVar()
    var.set('c')
    ser_check = tk.Radiobutton(log_win,text='Server',variable=var,value='s')
    cli_check = tk.Radiobutton(log_win,text='Client',variable=var,value='c')
    right_button = tk.Button(log_win,text='quit',width=10,height=2,command=log_win.quit)
    addr_lable.pack()
    addr_entry.pack()
    port_lable.pack()
    port_entry.pack()
    ser_cli_lable.pack()
    ser_check.pack()
    cli_check.pack()
    right_button.pack()
    # addr_lable.place(x=10,y=10)
    log_win.mainloop()



if __name__ == '__main__':
    login_window()
    print('here')
    # login_window()