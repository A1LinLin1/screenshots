# -*- coding: utf-8 -*-

import os
import socket
import threading
import pyautogui
from PIL import Image
from io import BytesIO
import time
import hashlib
from PyQt5 import QtWidgets, QtGui
from client_gui import run_client_app
import uuid
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# 客户端配置
SERVER_IP = '10.122.223.61'  # 替换为实际服务器的地址
SERVER_PORT = 5000
CAPTURE_INTERVAL = 15  # 截屏间隔时间，单位为秒
AES_KEY = b'1234567890123456'  # 16字节密钥

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

class Client:
    def __init__(self, server_ip=SERVER_IP, server_port=SERVER_PORT, capture_interval=CAPTURE_INTERVAL):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = True
        self.capture_interval = capture_interval
        self.mac_address = self.get_mac_address()  # 获取MAC地址
        self.ip_address = self.get_ip_address()  # 获取IP地址
        self.username = None  # 添加用户名属性

    # 连接到服务器
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))

    # 获取MAC地址
    def get_mac_address(self):
        return ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])

    # 获取IP地址
    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.254.254.254', 1))
            ip_address = s.getsockname()[0]
        except Exception:
            ip_address = '127.0.0.1'
        finally:
            s.close()
        return ip_address

    # 注册用户
    def register(self, username, password, signal):
        try:
            self.connect()
            registration_info = f'REGISTER {username} {password} {self.mac_address} {self.ip_address}'
            self.sock.sendall(aes_encrypt(registration_info.encode()))
            response = aes_decrypt(self.sock.recv(1024)).decode()
            if response == 'REGISTERED':
                self.username = username
                signal.emit("Registration successful")
                self.sock.close()  # 关闭连接
            else:
                signal.emit("Registration failed")
        except Exception as e:
            print(f"Registration error: {e}")
            signal.emit(f"Registration error: {e}")

    # 登录用户
    def login(self, username, password, signal):
        try:
            self.connect()
            login_info = f'LOGIN {username} {password}'
            self.sock.sendall(aes_encrypt(login_info.encode()))
            response = aes_decrypt(self.sock.recv(1024)).decode()
            if response == 'LOGGEDIN':
                self.username = username
                signal.emit("Login successful")
                threading.Thread(target=self.receive_updates).start()  # 启动监听更新线程
            else:
                signal.emit("Login failed")
        except Exception as e:
            print(f"Login error: {e}")
            signal.emit(f"Login error: {e}")

    # 接收服务器的更新消息
    def receive_updates(self):
        while self.is_running:
            try:
                data = aes_decrypt(self.sock.recv(1024)).decode()
                if data.startswith('SET_FREQUENCY'):
                    _, new_frequency = data.split()
                    self.capture_interval = int(new_frequency)  # 更新截屏频率
                    print(f"Updated capture interval to: {self.capture_interval} seconds")
            except Exception as e:
                print(f"Error receiving update: {e}")
                break

    # 截屏并发送屏幕图像
    def capture_and_send_screen(self):
        while self.is_running:
            try:
                screenshot = pyautogui.screenshot()  # 截取屏幕
                buffered = BytesIO()
                screenshot.save(buffered, format="JPEG", quality=85)
                img_data = buffered.getvalue()  # 获取图像数据
                img_hash = hashlib.sha256(img_data).hexdigest()
                print(f"Original image hash: {img_hash}")

                length_msg = str(len(img_data)).encode()
                print(f"Sending length: {length_msg}")
                self.sock.sendall(aes_encrypt(length_msg))  # 发送图像数据长度
                self.sock.recv(1024)  # 等待服务器准备
                self.sock.sendall(img_data)  # 发送图像数据
                self.sock.recv(1024)  # 等待服务器结束
                print(f"Sent data of length: {len(img_data)}")
                time.sleep(self.capture_interval)  # 等待下一次截屏
            except Exception as e:
                print(f"Error capturing or sending screen: {e}")
                break

    # 启动客户端
    def start(self):
        self.is_running = True
        capture_thread = threading.Thread(target=self.capture_and_send_screen)
        capture_thread.start()

    # 停止客户端
    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                if self.username:  # 确保在断开连接前有用户名
                    disconnect_info = f'DISCONNECT {self.username} {self.mac_address} {self.ip_address}'
                    self.sock.sendall(aes_encrypt(disconnect_info.encode()))
                self.sock.close()
            except Exception as e:
                print(f"Error sending disconnect info: {e}")

# 主函数
def main():
    run_client_app(Client)

# 程序入口
if __name__ == '__main__':
    main()
