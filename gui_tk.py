from tkinter import *

root = Tk()


def create():
    top = Toplevel()
    top.title('Python')
    but = Button(top,text='exit',command=top.quit).pack()
    msg = Message(top, text='I love study')
    msg.pack()
    # time.sleep(5)
    # top.after(100,lambda :heat(top))
    return top

def heat(ele):
    print('a')
    ele.after(100,lambda :heat(ele))

Button(root, text='创建顶级窗口', command=create).pack()
# i = create()
root.mainloop()