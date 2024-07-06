# -*- coding: utf-8 -*-

import os
import sys
import threading
from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3
import time

# 频率设置对话框类
class FrequencyDialog(QtWidgets.QDialog):
    def __init__(self, current_frequency, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置截屏速率")  # 设置对话框标题
        self.current_frequency = current_frequency  # 当前截屏速率
        self.init_ui()  # 初始化UI界面

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(f"当前截屏速率: {self.current_frequency} 秒", self)  # 显示当前截屏速率
        layout.addWidget(self.label)

        self.input = QtWidgets.QLineEdit(self)
        self.input.setPlaceholderText("输入新的截屏速率 (秒)")  # 提示输入新的截屏速率
        layout.addWidget(self.input)

        self.button = QtWidgets.QPushButton("应用", self)
        self.button.clicked.connect(self.apply_frequency)  # 按钮点击事件绑定
        layout.addWidget(self.button)
        
        self.setLayout(layout)

    def apply_frequency(self):
        try:
            new_frequency = float(self.input.text())  # 获取输入的新截屏速率
            self.current_frequency = new_frequency
            self.accept()  # 接受并关闭对话框
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请输入有效的数字")  # 提示输入错误

    def get_frequency(self):
        return self.current_frequency  # 返回当前截屏速率

# 显示截屏图片和用户信息的对话框类
class ShowDialog(QtWidgets.QDialog):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent, QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowCloseButtonHint)
        self.db_conn = db_conn  # 数据库连接
        self.setWindowTitle("显示截屏图片和用户信息")  # 设置对话框标题
        self.is_fullscreen = False  # 初始化全屏状态
        self.init_ui()  # 初始化UI界面

    def init_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        # 左边栏图像信息
        image_layout = QtWidgets.QVBoxLayout()
        self.image_display = QtWidgets.QLabel(self)
        self.image_display.setMinimumSize(800, 600)  # 设置显示区域最小尺寸
        self.image_display.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.image_display.setAlignment(QtCore.Qt.AlignCenter)  # 居中显示
        image_layout.addWidget(self.image_display)

        main_layout.addLayout(image_layout, 2)

        # 右边栏详细信息
        details_layout = QtWidgets.QVBoxLayout()

        self.start_label = QtWidgets.QLabel("开始时间 (YYYY-MM-DD HH:MM:SS):", self)
        details_layout.addWidget(self.start_label)
        self.start_input = QtWidgets.QLineEdit(self)
        details_layout.addWidget(self.start_input)

        self.end_label = QtWidgets.QLabel("结束时间 (YYYY-MM-DD HH:MM:SS):", self)
        details_layout.addWidget(self.end_label)
        self.end_input = QtWidgets.QLineEdit(self)
        details_layout.addWidget(self.end_input)

        self.ip_label = QtWidgets.QLabel("IP地址：", self)
        details_layout.addWidget(self.ip_label)
        self.ip_input = QtWidgets.QLineEdit(self)
        details_layout.addWidget(self.ip_input)

        self.mac_label = QtWidgets.QLabel("MAC地址：", self)
        details_layout.addWidget(self.mac_label)
        self.mac_input = QtWidgets.QLineEdit(self)
        details_layout.addWidget(self.mac_input)

        self.show_button = QtWidgets.QPushButton("显示", self)
        self.show_button.clicked.connect(self.show_data)  # 按钮点击事件绑定
        details_layout.addWidget(self.show_button)

        self.details_list = QtWidgets.QListWidget(self)
        details_layout.addWidget(self.details_list)

        main_layout.addLayout(details_layout, 1)

        # 添加全屏切换功能
        fullscreen_action = QtWidgets.QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)

    def show_data(self):
        start_time = self.start_input.text().strip()  # 获取输入的开始时间
        end_time = self.end_input.text().strip()  # 获取输入的结束时间
        ip_address = self.ip_input.text().strip()  # 获取输入的IP地址
        mac_address = self.mac_input.text().strip()  # 获取输入的MAC地址

        if not start_time and not end_time and not ip_address and not mac_address:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请至少提供一个查询条件")  # 提示输入错误
            return

        try:
            cursor = self.db_conn.cursor()
            query = '''
                SELECT timestamp, client_mac, ip_address, image_path
                FROM screenshots
                WHERE 1=1
            '''
            params = []

            if start_time and end_time:
                query += ' AND timestamp BETWEEN ? AND ?'
                params.extend([start_time, end_time])

            if ip_address:
                query += ' AND ip_address = ?'
                params.append(ip_address)

            if mac_address:
                query += ' AND client_mac = ?'
                params.append(mac_address)

            query += ' ORDER BY timestamp ASC'
            cursor.execute(query, params)
            rows = cursor.fetchall()

            self.details_list.clear()
            self.image_display.clear()

            print(f"Fetched {len(rows)} rows from database")

            for row in rows:
                timestamp, mac_address, ip_address, image_path = row
                item_text = f"Time: {timestamp}\nMAC: {mac_address}\nIP: {ip_address}\nImage Path: {image_path}"
                list_item = QtWidgets.QListWidgetItem(item_text)
                list_item.setData(QtCore.Qt.UserRole, image_path)
                self.details_list.addItem(list_item)

            if rows:
                self.details_list.itemClicked.connect(self.display_image)
            else:
                QtWidgets.QMessageBox.information(self, "无数据", "没有找到符合条件的截图")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "查询错误", f"查询数据库时出错: {e}")

    def display_image(self, item):
        image_path = item.data(QtCore.Qt.UserRole)
        print(f"Displaying image from path: {image_path}")  # 打印图片路径以确认正确性
        if os.path.exists(image_path):  # 确认图片路径存在
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                self.image_display.setPixmap(pixmap.scaled(
                    self.image_display.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            else:
                QtWidgets.QMessageBox.warning(self, "显示错误", f"无法显示图片: {image_path}")
        else:
            QtWidgets.QMessageBox.warning(self, "路径错误", f"图片路径不存在: {image_path}")

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

# 客户端窗口类
class ClientWindow(QtWidgets.QWidget):
    def __init__(self, client_address, parent=None):
        super().__init__(parent)
        self.client_address = client_address  # 客户端地址
        self.is_fullscreen = False  # 初始化全屏状态
        self.init_ui()  # 初始化UI界面

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(self)
        self.label.setMinimumSize(400, 300)  # 设置显示区域最小尺寸
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.label.setAlignment(QtCore.Qt.AlignCenter)  # 居中显示
        layout.addWidget(self.label)

        self.setLayout(layout)

        self.setWindowTitle(f"Client {self.client_address}")

    def display_image(self, image_path):
        if os.path.exists(image_path):  # 确认图片路径存在
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                self.label.setPixmap(pixmap.scaled(
                    self.label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            else:
                QtWidgets.QMessageBox.warning(self, "显示错误", f"无法显示图片: {image_path}")
        else:
            QtWidgets.QMessageBox.warning(self, "路径错误", f"图片路径不存在: {image_path}")

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

    def mouseDoubleClickEvent(self, event):
        self.toggle_fullscreen()

# 服务器GUI类
class ServerGUI(QtWidgets.QMainWindow):
    def __init__(self, server):
        super().__init__()
        self.server = server  # 服务器实例
        self.server.update_signal.connect(self.display_image)
        self.server.user_status_signal.connect(self.update_user_tree)
        self.client_windows = {}
        self.init_ui()  # 初始化UI界面

    def init_ui(self):
        self.setWindowTitle('屏幕监控服务器')  # 设置主窗口标题
        self.setWindowIcon(QtGui.QIcon("icon.png"))  # 设置任务栏图标
        self.resize(1200, 800)

        toolbar = QtWidgets.QToolBar(self)
        self.addToolBar(toolbar)

        settings_action = QtWidgets.QAction("频率", self)
        settings_action.triggered.connect(self.open_frequency_dialog)
        toolbar.addAction(settings_action)

        show_action = QtWidgets.QAction("历史", self)
        show_action.triggered.connect(self.open_show_dialog)
        toolbar.addAction(show_action)

        central_layout = QtWidgets.QVBoxLayout()
        self.central_widget = QtWidgets.QWidget()
        self.central_widget.setLayout(central_layout)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Ready")  # 状态栏显示准备就绪

        # 上部布局
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QGridLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        central_layout.addWidget(self.scroll_area)

        # 下部布局
        self.user_tree = QtWidgets.QTreeWidget(self)
        self.user_tree.setColumnCount(3)
        self.user_tree.setHeaderLabels(['MAC地址', 'IP地址', '状态'])
        central_layout.addWidget(self.user_tree)

    def open_frequency_dialog(self):
        current_frequency = self.server.get_frequency()  # 获取当前频率
        dialog = FrequencyDialog(current_frequency, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_frequency = dialog.get_frequency()
            self.server.set_frequency(new_frequency)  # 设置新的频率

    def open_show_dialog(self):
        dialog = ShowDialog(self.server.db_conn, self)
        dialog.exec_()

    def display_image(self, image_path, client_address):
        if client_address not in self.client_windows:
            self.create_client_window(client_address)  # 创建新的客户端窗口
        self.client_windows[client_address].display_image(image_path)
        self.statusBar().showMessage(f"Received image from {client_address}")  # 状态栏显示接收到的图像信息
        QtWidgets.QApplication.processEvents()

    def create_client_window(self, client_address):
        client_window = ClientWindow(client_address, self)
        self.client_windows[client_address] = client_window
        row = len(self.client_windows) // 3
        col = len(self.client_windows) % 3
        self.scroll_layout.addWidget(client_window, row, col)
        client_window.show()

    def update_user_tree(self, user_status):
        self.user_tree.clear()
        for (mac, ip), online in user_status.items():
            status = '在线' if online else '离线'
            item = QtWidgets.QTreeWidgetItem(self.user_tree, [mac, ip, status])
            if online:
                item.setBackground(2, QtGui.QColor('green'))
            else:
                item.setBackground(2, QtGui.QColor('gray'))

    def resizeEvent(self, event):
        for client_window in self.client_windows.values():
            client_window.label.resize(client_window.size())
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.server.stop()
        event.accept()

def run_server_app(ServerClass):
    app = QtWidgets.QApplication(sys.argv)
    server = ServerClass()
    threading.Thread(target=server.start).start()
    server_gui = ServerGUI(server)
    server_gui.show()
    sys.exit(app.exec_())
