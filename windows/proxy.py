#encoding:utf-8
# Code from http://xiaoxia.org/2011/11/14/update-sogou-proxy-program-with-https-support/


from threading import Thread, Lock
from struct import unpack
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from httplib import HTTPResponse
from SocketServer import ThreadingMixIn
import socket, os, select
import time, sys, random
import threading
import ConfigParser, codecs

config = ConfigParser.ConfigParser()
with codecs.open('NPUcat.ini', mode='r', encoding='utf-8-sig') as fp:
    config.readfp(fp)
    opt_address_family = config.get('proxy', 'address_family')

# Minimize Memory Usage
threading.stack_size(128*1024)

x_sogou_auth = "9CD285F1E7ADB0BD403C22AD1D545F40/30/853edc6d49ba4e27"
proxy_host = "h0.edu.bj.ie.sogou.com"
proxy_port = 80
BufferSize = 8192
RemoteTimeout = 15

def calc_sogou_hash(t, host):
    s = (t + host + 'SogouExplorerProxy').encode('ascii')
    code = len(s)
    dwords = int(len(s)/4)
    rest = len(s) % 4
    v = unpack(str(dwords) + 'i'+str(rest)+'s', s)
    for vv in v:
        if(type(vv)==type('i')):
            break
        a = (vv & 0xFFFF)
        b = (vv >> 16)
        code += a
        code = code ^ (((code<<5)^b) << 0xb)
        # To avoid overflows
        code &= 0xffffffff
        code += code >> 0xb
    if rest == 3:
        code += ord(s[len(s)-2]) * 256 + ord(s[len(s)-3])
        code = code ^ ((code ^ (ord(s[len(s)-1])*4)) << 0x10)
        code &= 0xffffffff
        code += code >> 0xb
    elif rest == 2:
        code += ord(s[len(s)-1]) * 256 + ord(s[len(s)-2])
        code ^= code << 0xb
        code &= 0xffffffff
        code += code >> 0x11
    elif rest == 1:
        code += ord(s[len(s)-1])
        code ^= code << 0xa
        code &= 0xffffffff
        code += code >> 0x1
    code ^= code * 8
    code &= 0xffffffff
    code += code >> 5
    code ^= code << 4
    code = code & 0xffffffff
    code += code >> 0x11
    code ^= code << 0x19
    code = code & 0xffffffff
    code += code >> 6
    code = code & 0xffffffff
    return hex(code)[2:].rstrip('L').zfill(8)

class Handler(BaseHTTPRequestHandler):
    remote = None
    
    # Ignore Connection Failure
    def handle(self):
        try:
            BaseHTTPRequestHandler.handle(self)
        except socket.error: pass
    def finish(self):
        try:
            BaseHTTPRequestHandler.finish(self)
        except socket.error: pass
    
    # CONNECT Data Transfer
    def transfer(self, a, b):
        fdset = [a, b]
        while True:
            r,w,e = select.select(fdset, [], [])
            if a in r:
                data = a.recv(BufferSize)
                if not data: break
                b.sendall(data)
            if b in r:
                data = b.recv(BufferSize)
                if not data: break
                a.sendall(data)
    
    def sogouProxy(self):
        if self.remote is None or self.lastHost != self.headers["Host"]:
            self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.remote.settimeout(RemoteTimeout)
            self.remote.connect((proxy_host, proxy_port))
        self.remote.sendall(self.requestline.encode('ascii').replace('baike.baidu.com', '220.181.111.247') + b"\r\n")
        # Add Sogou Verification Tags
        self.headers["X-Sogou-Auth"] = x_sogou_auth
        t = hex(int(time.time()))[2:].rstrip('L').zfill(8)
        self.headers["X-Sogou-Tag"] = calc_sogou_hash(t, self.headers['Host'])
        self.headers["X-Sogou-Timestamp"] = t
        headerstr = str(self.headers).replace("\r\n", "\n").replace("\n", "\r\n")
        self.remote.sendall(headerstr.encode('ascii') + b"\r\n")
        # Send Post data
        if self.command == 'POST':
            self.remote.sendall(self.rfile.read(int(self.headers['Content-Length'])))
        response = HTTPResponse(self.remote, method=self.command)
        response.begin()
        
        # Reply to the browser
        status = "HTTP/1.1 " + str(response.status) + " " + response.reason
        self.wfile.write(status.encode('ascii') + b'\r\n')
        hlist = []
        for line in response.msg.headers: # Fixed multiple values of a same name
            if 'TRANSFER-ENCODING' not in line.upper():
                hlist.append(line)
        self.wfile.write("".join(hlist) + b'\r\n')
        
        if self.command == "CONNECT" and response.status == 200:
            return self.transfer(self.remote, self.connection)
        else:
            while True:
                response_data = response.read(BufferSize)
                if not response_data: break
                self.wfile.write(response_data)
    
    do_POST = do_GET = do_CONNECT = sogouProxy

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    if opt_address_family.lower() == 'ipv6':
        address_family = socket.AF_INET6
    else:
        address_family = socket.AF_INET

def start_proxy(app):
    server_address = ("", 1998)
    app.server = server = ThreadingHTTPServer(server_address, Handler)
    # Random Target Proxy Server
    proxy_host = 'h' + str(random.randint(0,int(app.opt_max_server_id))) + '.edu.bj.ie.sogou.com'

    t = threading.Thread(target=app.flash_icon)
    t.setDaemon(True)
    t.start()
    
    print('Proxy over %s.\nPlease set your browser\'s proxy to %s.' % (proxy_host, server_address))
        
    try:
        server.serve_forever()
    except:
        os._exit(1)
        