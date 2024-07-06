# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import threading

# 托盘图标类
class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent=None):
        super(TrayIcon, self).__init__(parent)
        self.parent = parent
        self.setIcon(QtGui.QIcon("icon.png"))   # 设置托盘图标，确保有icon.png文件
        self.setToolTip("Client Running")  # 设置托盘图标的提示文字
        self.menu = QtWidgets.QMenu(parent)  # 创建托盘图标的右键菜单
        self.show_action = self.menu.addAction("显示")  # 添加显示选项
        self.show_action.triggered.connect(parent.show)  # 绑定显示选项的点击事件
        self.exit_action = self.menu.addAction("退出")  # 添加退出选项
        self.exit_action.triggered.connect(self.exit)  # 绑定退出选项的点击事件
        self.setContextMenu(self.menu)  # 设置右键菜单
        self.activated.connect(self.on_tray_icon_activated)  # 绑定托盘图标激活事件

    # 退出程序
    def exit(self):
        self.parent.close()
        QtWidgets.qApp.quit()

    # 托盘图标激活事件处理
    def on_tray_icon_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.parent.show()  # 显示主窗口

# 客户端应用程序类
class ClientApp(QtWidgets.QMainWindow):
    update_status_signal = QtCore.pyqtSignal(str)  # 定义信号，用于更新状态标签

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.tray_icon = TrayIcon(self)  # 创建托盘图标
        self.setWindowIcon(QtGui.QIcon("icon.png"))  # 设置任务栏图标
        self.init_ui()  # 初始化UI界面

        self.update_status_signal.connect(self.update_status)  # 连接信号到槽函数

    # 初始化UI界面
    def init_ui(self):
        self.setWindowTitle('客户端')  # 设置窗口标题
        self.setGeometry(100, 100, 400, 400)  # 设置窗口位置和大小

        self.label = QtWidgets.QLabel('用户名：', self)  # 创建用户名标签
        self.label.move(20, 20)
        self.username_input = QtWidgets.QLineEdit(self)  # 创建用户名输入框
        self.username_input.move(100, 20)

        self.label_password = QtWidgets.QLabel('密码：', self)  # 创建密码标签
        self.label_password.move(20, 60)
        self.password_input = QtWidgets.QLineEdit(self)  # 创建密码输入框
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)  # 设置密码输入框为密码模式
        self.password_input.move(100, 60)

        self.label_ip = QtWidgets.QLabel('服务器IP：', self)  # 创建服务器IP标签
        self.label_ip.move(20, 100)
        self.ip_input = QtWidgets.QLineEdit(self)  # 创建服务器IP输入框
        self.ip_input.move(100, 100)

        self.label_port = QtWidgets.QLabel('端口号：', self)  # 创建端口号标签
        self.label_port.move(20, 140)
        self.port_input = QtWidgets.QLineEdit(self)  # 创建端口号输入框
        self.port_input.move(100, 140)

        self.label_frequency = QtWidgets.QLabel('频率(秒)：', self)  # 创建频率标签
        self.label_frequency.move(20, 180)
        self.frequency_input = QtWidgets.QLineEdit(self)  # 创建频率输入框
        self.frequency_input.move(100, 180)

        self.login_button = QtWidgets.QPushButton('登录', self)  # 创建登录按钮
        self.login_button.move(100, 220)
        self.login_button.clicked.connect(self.login)  # 绑定登录按钮点击事件

        self.register_button = QtWidgets.QPushButton('注册', self)  # 创建注册按钮
        self.register_button.move(200, 220)
        self.register_button.clicked.connect(self.register)  # 绑定注册按钮点击事件

        self.status_label = QtWidgets.QLabel('', self)  # 创建状态标签
        self.status_label.setWordWrap(True)  # 设置标签文本自动换行
        self.status_label.move(20, 260)
        self.status_label.resize(350, 40)

        self.tray_icon.show()  # 显示托盘图标

    # 登录功能
    def login(self):
        username = self.username_input.text()  # 获取用户名
        password = self.password_input.text()  # 获取密码
        ip = self.ip_input.text()  # 获取服务器IP
        port = int(self.port_input.text())  # 获取端口号
        frequency = int(self.frequency_input.text())  # 获取截屏频率
        self.client.server_ip = ip
        self.client.server_port = port
        self.client.capture_interval = frequency
        threading.Thread(target=self.client.login, args=(username, password, self.update_status_signal)).start()  # 启动登录线程

    # 注册功能
    def register(self):
        username = self.username_input.text()  # 获取用户名
        password = self.password_input.text()  # 获取密码
        ip = self.ip_input.text()  # 获取服务器IP
        port = int(self.port_input.text())  # 获取端口号
        frequency = int(self.frequency_input.text())  # 获取截屏频率
        self.client.server_ip = ip
        self.client.server_port = port
        self.client.capture_interval = frequency
        threading.Thread(target=self.client.register, args=(username, password, self.update_status_signal)).start()  # 启动注册线程

    # 更新状态标签
    def update_status(self, status):
        self.status_label.setText(status)  # 设置状态标签文本
        if status == 'Login successful':
            QtWidgets.QMessageBox.information(self, '成功', '登录成功！')  # 显示登录成功消息框
            self.hide()  # 隐藏主窗口
            self.client.start()  # 启动客户端功能

    # 关闭事件处理
    def closeEvent(self, event):
        self.client.stop()  # 停止客户端功能
        event.accept()  # 接受关闭事件
        QtWidgets.QApplication.quit()  # 确保应用完全停止

# 运行客户端应用程序
def run_client_app(client_class):
    app = QtWidgets.QApplication(sys.argv)
    client = client_class()
    client_app = ClientApp(client)
    client_app.show()
    sys.exit(app.exec_())
