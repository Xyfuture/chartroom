import threading
from queue import Queue


def thread_job():
    print("pid : %s"%threading.current_thread())


def main():
    new_thread = threading.Thread(target=thread_job)
    new_thread.start()
    print(threading.active_count())
    print(threading.enumerate())
    print(threading.current_thread())
    new_thread.join()
    lock = threading.Lock()


if __name__ == '__main__':
    main()










