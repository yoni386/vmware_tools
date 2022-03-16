#!/usr/local/python

import socket, thread, time

test_msg = "This is just a test message"

total_sent = 0

NUMTHREADS = 20


def send_request():
    start = time.time()
    global total_sent
    for i in range(0, 100):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 8888))
        s.send("%s\n\r\n" % test_msg)
        s.recv(512)
        s.close()
        total_sent += total_sent + 1
        if total_sent % 100 == 0:
            print ("total sent = %s" % total_sent)
    end = time.time()
    print ("exiting thread. duration %s" % (end - start))


total_sent = 0
for i in range(0, NUMTHREADS):
    thread.start_new_thread(send_request, ())

