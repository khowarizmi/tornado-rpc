# -*- coding: utf-8 -*-
from functools import partial
from tornado import gen, tcpserver
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError

import config
import netutils


class TCPServer(tcpserver.TCPServer):
    def __init__(self, callback):
        super(TCPServer, self).__init__()
        self.callback = callback

    def handle_stream(self, stream, address):
        self.callback(stream, address)


class Server():
    def __init__(self, handler):
        self.handler = handler
        self.tcp_server = TCPServer(self.handle_stream)

    def bind(self, port=8000):
        self.port = port
        self.tcp_server.bind(self.port)
        return self

    def start(self, process=1):
        self.process = process
        self.tcp_server.start(process)
        return self

    @gen.coroutine
    def handle_stream(self, stream, address):
        while True:
            try:
                data = yield netutils.recv(stream)
                self.handle_line(data, stream)
            except StreamClosedError:
                break

    def handle_line(self, data, stream):
        send_msg = partial(netutils.send, stream=stream)
        result = {'id': data.get('id', None)}

        # handle key miss error
        key_miss_error = None
        for key in config.keyMissMap:
            if key_miss_error:
                break
            if key not in data:
                key_miss_error = config.keyMissMap[key]
        if key_miss_error:
            result['error'] = key_miss_error
            return send_msg(result)

        mode = data['mode']
        method = data['method']
        params = data['params']

        # handle method invalid
        if not hasattr(self.handler, method):
            result['error'] = config.METHOD_INVALID
            return send_msg(result)

        if mode == config.CALL_MODE:
            result['result'] = getattr(self.handler, method)(*params)
        elif mode == config.NOTI_MODE:
            IOLoop.current().add_callback(getattr(self.handler, method), *params)
            result['result'] = config.SUCCESS
        else:
            result['error'] = config.MODE_INVALID
        return send_msg(result)


if __name__ == '__main__':
    class Handler(object):
        def sum(self, a, b):
            # print 'sum', a, b, a + b
            return a + b

    server = Server(Handler())
    server.bind()
    server.start(1)

    IOLoop.current().start()
