from tkinter import*

#第二窗口定义
def windows2():
   master = Tk()  # 导入tkinter中的tk模块
   master.title('小黑的翻译器2')
   master.geometry('460x120+1200+500')
   label1 = Label(master, text='输入内容:', font=('GB2312', 16), fg='SteelBlue')
   label1.grid(row=0, column=0)
   label2 = Label(master, text='结果:', font=('C71585', 16), fg='SteelBlue')
   label2.grid(row=1, column=0)
   entry1 = Entry(master, font=('GB2312', 18), fg='Plum')
   entry1.grid(row=0, column=1, )
   s = StringVar()
   entry2 = Entry(master, font=('GB2312', 18), fg='DarkCyan', textvariable=s)
   entry2.grid(row=1, column=1)
   button1 = Button(master, text='打开', width=10, font=('GB2312', 18), background='Tan')
   button1.grid(row=2, column=0, sticky=W)
   button2 = Button(master, text='退出', width=10, font=('GB2312', 18), background='Tan', command=master.quit)
   button2.grid(row=2, column=1, sticky=E)
   master.mainloop()

#第一窗口设置

master=Tk()#导入tkinter中的tk模块
master.title('小黑的翻译器')
master.geometry('460x120+1100+400')
#显示框样式
label1=Label(master,text='输入内容:',font=('GB2312',16),fg='SteelBlue')
label1.grid(row=0,column=0)

label2=Label(master,text='结果:',font=('C71585',16),fg='SteelBlue')
label2.grid(row=1,column=0)
#输入框设置
entry1=Entry(master,font=('GB2312',18),fg='Plum')
entry1.grid(row=0,column=1,)

s=StringVar()
entry2=Entry(master,font=('GB2312',18),fg='DarkCyan',textvariable=s)
entry2.grid(row=1,column=1)

#按钮设置

#第二窗口导入
button1=Button(master,text='打开',width=10,font=('GB2312',18),background='Tan',command=windows2)   #window2不带括号
button1.grid(row=2,column=0,sticky=W)

button2=Button(master,text='退出',width=10,font=('GB2312',18),background='Tan',command=master.quit)
button2.grid(row=2,column=1,sticky=E)

master.mainloop()#一直运行，不停止