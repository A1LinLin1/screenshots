# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import socket
import threading
import time
from PyQt5 import QtWidgets, QtGui, QtCore
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# 服务器配置
SERVER_IP = '0.0.0.0'
SERVER_PORT = 5000
SCREENSHOT_DIR = 'screenshots'
AES_KEY = b'1234567890123456'  # 16字节密钥

# 确保截屏图片存放目录存在
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# AES 加密和解密函数
def aes_encrypt(data):
    cipher = AES.new(AES_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data, AES.block_size))
    iv = base64.b64encode(cipher.iv)
    ct = base64.b64encode(ct_bytes)
    return iv + b':' + ct

def aes_decrypt(enc_data):
    iv, ct = enc_data.split(b':')
    iv = base64.b64decode(iv)
    ct = base64.b64decode(ct)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt

# 服务器类
class Server(QtCore.QObject):
    # 定义信号，用于在收到截图时更新UI和用户状态
    update_signal = QtCore.pyqtSignal(str, tuple)
    user_status_signal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.server_ip = SERVER_IP
        self.server_port = SERVER_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.user_status = {}
        self.db_conn = sqlite3.connect('screenshots.db', check_same_thread=False)
        self.create_db()  # 创建数据库表
        self.is_running = True
        self.screenshot_interval = 15.0  # 初始截屏间隔为15秒

    # 创建数据库表
    def create_db(self):
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_mac TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT,
                ip_address TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                mac_address TEXT,
                ip_address TEXT
            )
        ''')
        self.db_conn.commit()

    # 处理客户端连接
    def handle_client(self, client_sock, client_address):
        mac_address, ip_address = None, None
        try:
            data = aes_decrypt(client_sock.recv(1024)).decode()
            if data.startswith('REGISTER'):
                _, username, password, mac_address, ip_address = data.split()
                self.register_user(client_sock, username, password, mac_address, ip_address)
            elif data.startswith('LOGIN'):
                _, username, password = data.split()
                cursor = self.db_conn.cursor()
                cursor.execute('SELECT mac_address, ip_address FROM users WHERE username = ? AND password = ?', 
                               (username, password))
                result = cursor.fetchone()
                if result:
                    mac_address, ip_address = result
                    self.login_user(client_sock, username, password, mac_address, ip_address)
                else:
                    client_sock.sendall(aes_encrypt(b'LOGINFAILED'))
                    return
            elif data.startswith('DISCONNECT'):
                _, username, mac_address, ip_address = data.split()
                self.update_user_status((mac_address, ip_address), False)
                client_sock.close()
                return

            self.clients[client_address] = client_sock
            self.send_frequency(client_sock)

            while self.is_running:
                try:
                    length_mesg = aes_decrypt(client_sock.recv(1024)).decode()
                    if not length_mesg.isdigit():
                        raise ValueError(f"Invalid length message: {length_mesg}")
                    length_mesg = int(length_mesg)
                    client_sock.sendall(aes_encrypt(b"ready"))
                    img_data = b''
                    len_recved = 0
                    while len_recved < length_mesg:
                        recved = client_sock.recv(4096)
                        img_data += recved
                        len_recved += len(recved)
                    client_sock.sendall(aes_encrypt(b"finish"))

                    img_hash = hashlib.sha256(img_data).hexdigest()

                    if not img_data:
                        break

                    timestamp = time.strftime("%Y%m%d%H%M%S")
                    image_path = os.path.join(SCREENSHOT_DIR, f"{timestamp}.jpg")
                    with open(image_path, "wb") as img_file:
                        img_file.write(img_data)

                    self.update_ui(image_path, client_address)

                    cursor = self.db_conn.cursor()
                    cursor.execute('INSERT INTO screenshots (client_mac, image_path, ip_address) VALUES (?, ?, ?)',
                                   (mac_address, image_path, ip_address))
                    self.db_conn.commit()
                    
                except Exception as e:
                    print(f'Error receiving image from {client_address}: {e}')
                    break
        except Exception as e:
            print(f'Error handling client {client_address}: {e}')
        finally:
            client_sock.close()
            if mac_address and ip_address:
                self.update_user_status((mac_address, ip_address), False)
            del self.clients[client_address]

    # 注册新用户
    def register_user(self, client_sock, username, password, mac_address, ip_address):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('INSERT INTO users (username, password, mac_address, ip_address) VALUES (?, ?, ?, ?)',
                           (username, password, mac_address, ip_address))
            self.db_conn.commit()
            client_sock.sendall(aes_encrypt(b'REGISTERED'))
        except sqlite3.IntegrityError:
            client_sock.sendall(aes_encrypt(b'REGISTRATIONFAILED'))

    # 登录用户
    def login_user(self, client_sock, username, password, mac_address, ip_address):
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ? AND mac_address = ? AND ip_address = ?',
                       (username, password, mac_address, ip_address))
        user = cursor.fetchone()
        if user:
            client_sock.sendall(aes_encrypt(b'LOGGEDIN'))
            self.update_user_status((mac_address, ip_address), True)
        else:
            client_sock.sendall(aes_encrypt(b'LOGINFAILED'))

    # 更新用户状态
    def update_user_status(self, client_address, online):
        self.user_status[client_address] = online
        self.user_status_signal.emit(self.user_status)

    # 启动服务器
    def start(self):
        self.sock.bind((self.server_ip, self.server_port))
        self.sock.listen(5)
        print(f'Server listening on {self.server_ip}:{self.server_port}')
        while self.is_running:
            client_sock, client_address = self.sock.accept()
            threading.Thread(target=self.handle_client, args=(client_sock, client_address)).start()

    # 停止服务器
    def stop(self):
        self.is_running = False
        self.sock.close()

    # 更新UI
    def update_ui(self, image_path, client_address):
        self.update_signal.emit(image_path, client_address)

    # 获取截屏频率
    def get_frequency(self):
        return self.screenshot_interval

    # 设置截屏频率
    def set_frequency(self, new_frequency):
        self.screenshot_interval = new_frequency
        for client_sock in self.clients.values():
            self.send_frequency(client_sock)

    # 发送截屏频率给客户端
    def send_frequency(self, client_sock):
        message = f"SET_FREQUENCY {self.screenshot_interval}"
        client_sock.sendall(aes_encrypt(message.encode()))

# 主函数
def main():
    from server_gui import run_server_app
    run_server_app(Server)

# 程序入口
if __name__ == '__main__':
    main()
