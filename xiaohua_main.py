import sys
import os
import subprocess
import math
import json
import time
import threading

from xiaohua_setting import xiaohua_work_thread
from xiaohua_setting import XiaohuaSettingWidget
from xiaohua_setting import fresh_display_info
from PyQt5.QtGui import QTextCursor, QFont, QIcon
from PyQt5.QtCore import QSize

from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QStyleOptionButton
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFontMetrics, QPainter

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QFont

# 使用环境变量抑制PyQt5的警告
os.environ['QT_LOGGING_RULES'] = '*.warning=false;*.critical=false'

# 更直接地抑制所有DeprecationWarning
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 首先导入Qt核心模块，确保在创建QApplication前设置高DPI属性
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QComboBox

# 设置高DPI缩放属性，必须在创建QApplication之前设置
sys.argv += ['--no-sandbox']
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 导入其他模块
import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QLabel, QDesktopWidget, QMainWindow,
                              QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QTextEdit, QMenu, QAction)
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QColor, QGuiApplication, QScreen, QIcon

# 尝试导入markdown库，如果没有则使用简单的文本格式
markdown_available = False
try:
    import markdown
    markdown_available = True
except ImportError:
    print("未找到markdown库，将使用纯文本显示。请安装markdown库以支持markdown格式。")

# 用于进程间通信的文件路径
INPUT_FILE = "data/input_message.json"
OUTPUT_FILE = "data/output_message.json"
# 用于控制悬浮球输入框禁用状态的标志文件路径
INPUT_DISABLE_FLAG = "data/input_disabled.flag"

class MessageCommunicator(QObject):
    """消息通信器，负责与test_float.py进行通信"""
    response_received = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.listener_thread = None
        self.last_output_time = 0
        self.current_request_id = None
    
    def start(self):
        """启动通信器"""
        self.running = True
        self.listener_thread = threading.Thread(target=self.listen_for_responses)
        self.listener_thread.daemon = True
        self.listener_thread.start()
    
    def stop(self):
        """停止通信器"""
        self.running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1.0)
    
    def send_message(self, message, screenshot_filename=None):
        """发送消息到test_float.py"""
        try:
            # 确保数据目录存在
            if not os.path.exists("data"):
                os.makedirs("data")
            
            # 创建请求ID
            request_id = str(time.time())
            self.current_request_id = request_id
            
            # 构建消息数据
            data = {
                'request_id': request_id,
                'content': message,
                'timestamp': time.time()
            }
            
            # 添加缩略图文件名（如果有）
            if screenshot_filename:
                data['screenshot_filename'] = screenshot_filename
                print(f"缩略图文件名已添加: {screenshot_filename}")
            
            # 写入输入文件
            with open(INPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            print(f"消息已发送: {message}")
            return True
        except Exception as e:
            print(f"发送消息失败: {e}")
            return False
    
    def listen_for_responses(self):
        """监听test_float.py的响应，任何时候OUTPUT_FILE内容被修改都会显示"""
        while self.running:
            try:
                # 检查输出文件是否存在且有更新
                if os.path.exists(OUTPUT_FILE):
                    file_time = os.path.getmtime(OUTPUT_FILE)
                    if file_time > self.last_output_time:
                        # 读取响应消息
                        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 直接获取content，不检查request_id，确保任何修改都能显示
                        response = data.get('content', '')
                        if response:  # 确保内容不为空
                            print(f"检测到OUTPUT_FILE更新，显示内容: {response}")
                            # 通过信号发送响应
                            self.response_received.emit(response)
                        
                        # 记录最后读取时间
                        self.last_output_time = file_time
            
            except Exception as e:
                print(f"监听响应时出错: {e}")
            
            # 短暂休眠，减少CPU占用
            time.sleep(0.1)

# 创建全局消息通信器实例
comm_manager = MessageCommunicator()
app_background_color = "#933"

class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            # 处理 Ctrl + Enter 的情况，在当前行末尾添加换行符
            cursor = self.textCursor()
            cursor.insertText("\n")
            print("ctrl+enter\n")
            # 移动光标到末尾并插入文本
            cursor.movePosition(QTextCursor.End)       
            # 确保光标可见（滚动到底部）
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 阻止默认行为，即不插入换行符
            event.ignore()
            print("enter\n")
            # self.sendMessage()
            self.send_task_info_to_ai()
            #self.send_task_info_to_ai()
        else:
            # 对于其他按键，调用基类的 keyPressEvent
            super().keyPressEvent(event)

    def sendMessage(self):
        message = self.toPlainText()
        if message.strip():
            print(f"Message sent: {message}")
            self.clear()
            QMessageBox.information(self, "Message Sent", "Your message has been sent.")

    def send_task_info_to_ai(self):     
        # 检查父窗口是否处于等待状态
        if self.parent() is None:
            print("父窗口不存在")
            return
        if self.parent().parent is None:
            print("父窗口的父窗口不存在")
            return
        grandparent = self.parent().parent()
        if self.parent().parent() and hasattr(self.parent().parent(), 'is_waiting') and self.parent().parent().is_waiting:
            # 显示等待提示
            if self.parent().parent() and hasattr(self.parent().parent(), 'display_widget') and self.parent().parent().display_widget:
                self.parent().parent().display_widget.show_waiting_message()
            return
        print(f"父窗口的父窗口: {grandparent}")
        print(f"父窗口的父窗口的父窗口: {grandparent.parent()}")
        text = self.toPlainText().strip()
        if text:
            if hasattr(self.parent().parent(), 'display_widget') is None:
                print("父窗口的父窗口的display_widget不存在")
                return
            if grandparent.parent().display_widget is None:
                print("父窗口的父窗口的display_widget不存在")
                return
            if grandparent and hasattr(grandparent.parent(), 'display_widget') and grandparent.parent().display_widget:
                grandparent.parent().display_widget.show_message(text)
                text = "工作任务：" + text 
                # 通过通信管理器发送消息
                comm_manager.send_message(text)
                print(f"comm_manager 已发送消息: {text}")
            print(f"发送消息: {text}")
            self.clear()

class FloatHouse(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.width = 500
        self.height = 50
        # 暂时设置一个默认值
        #self.small_size = (100, 50)
        #self.current_size = self.small_size
        self.setGeometry(0, 0, self.width, self.height)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setText("小华工作台")
        # 隐藏时的透明绿色背景标签 - 使用更醒目的颜色和更高的透明度
        self.edge_label = QLabel(self)
        self.edge_label.setGeometry(0, 0, 0, 0)
        self.edge_label.setStyleSheet("background-color: rgba(128, 0, 0, 0); border-radius: 3px;")
        self.edge_label.hide()
        # 为边缘标签添加鼠标跟踪
        self.edge_label.setMouseTracking(True)
        self.load_image()

    def load_image(self):
        img_path = "icons/house.png"
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.small_pixmap = self.original_pixmap.scaled(
                    self.width, self.height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.label.setPixmap(self.small_pixmap)
                #self.label.setPixmap(pixmap)
                self.label.setGeometry(0, 0, self.width, self.height)
                return

    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           # self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
           # self.move(event.globalPos() - self.drag_position)
            event.accept()


class FloatFlower(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.width = 50
        self.height = 50
        # 暂时设置一个默认值
        #self.small_size = (100, 50)
        #self.current_size = self.small_size
        self.setGeometry(0, 0, self.width, self.height)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setText("小霞")
        # 隐藏时的透明绿色背景标签 - 使用更醒目的颜色和更高的透明度
        self.edge_label = QLabel(self)
        self.edge_label.setGeometry(0, 0, 0, 0)
        self.edge_label.setStyleSheet("background-color: rgba(128, 0, 0, 0); border-radius: 3px;")
        self.edge_label.hide()
        # 为边缘标签添加鼠标跟踪
        self.edge_label.setMouseTracking(True)
        self.load_image()
        self.show()


    def load_image(self):
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio()

        img_path = "icons/小霞.png"
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.small_pixmap = self.original_pixmap.scaled(
                    #self.width, self.height,
                    int(self.width * ratio), int(self.height * ratio),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.small_pixmap.setDevicePixelRatio(ratio)
                self.label.setPixmap(self.small_pixmap)

                self.label.setGeometry(0, 0, self.width, self.height)
                return


    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           # self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            print('小霞 clicked!')
            QMessageBox.information(self, '友情提示', '我是小霞，是小华的助手，我的工作内容待规划。')
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
           # self.move(event.globalPos() - self.drag_position)
            event.accept()

class FloatDocer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.width = 50
        self.height = 50
        # 暂时设置一个默认值
        #self.small_size = (100, 50)
        #self.current_size = self.small_size
        self.setGeometry(0, 0, self.width, self.height)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setText("docer")
        # 隐藏时的透明绿色背景标签 - 使用更醒目的颜色和更高的透明度
        self.edge_label = QLabel(self)
        self.edge_label.setGeometry(0, 0, 0, 0)
        self.edge_label.setStyleSheet("background-color: rgba(128, 0, 0, 0); border-radius: 3px;")
        self.edge_label.hide()
        # 为边缘标签添加鼠标跟踪
        self.edge_label.setMouseTracking(True)
        self.load_image()
        self.show()


    def load_image(self):
        img_path = "icons/docer.png"
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.small_pixmap = self.original_pixmap.scaled(
                    self.width, self.height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.label.setPixmap(self.small_pixmap)
                #self.label.setPixmap(pixmap)
                self.label.setGeometry(0, 0, self.width, self.height)
                return


    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           # self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            print('小霞 clicked!')
            QMessageBox.information(self, '友情提示', '我是小霞，是小华的助手，我的工作内容待规划。')
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
           # self.move(event.globalPos() - self.drag_position)
            event.accept()


class BotLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.width = 50
        self.height = 50
        # 暂时设置一个默认值
        #self.small_size = (100, 50)
        #self.current_size = self.small_size
        #self.setGeometry(0, 0, self.width, self.height)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setText("bot")
        # 隐藏时的透明绿色背景标签 - 使用更醒目的颜色和更高的透明度
        self.edge_label = QLabel(self)
        #self.edge_label.setGeometry(0, 0, 0, 0)
        self.edge_label.setStyleSheet("background-color: rgba(128, 0, 0, 0); border-radius: 3px;")
        self.edge_label.hide()
        # 为边缘标签添加鼠标跟踪
        self.edge_label.setMouseTracking(True)
        self.load_image()
        self.show()


    def load_image(self):
        img_path = "icons/docer.png"
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.small_pixmap = self.original_pixmap.scaled(
                    self.width, self.height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.label.setPixmap(self.small_pixmap)
                #self.label.setPixmap(pixmap)
                #self.label.setGeometry(0, 0, self.width, self.height)
                return


    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           # self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            print('Docer clicked!')
            QMessageBox.information(self, '友情提示', '我是小霞，是小华的助手，我的工作内容待规划。')
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
           # self.move(event.globalPos() - self.drag_position)
            event.accept()


class FloatSendButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        button_color = "green"
        #if app_background_color == "#393":
        #    button_color = "white"
        #    print("背景颜色为绿色，按钮颜色设置为白色")
        #print(f"按钮颜色为: {button_color}")

        # 创建按钮
        self.sendbutton = QPushButton('↑', self)
        self.sendbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: {button_color};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.sendbutton.resize(30, 30)
        self.sendbutton.setFont(QFont('Calibri', 12))
        if app_background_color == "#393":
            icon = QIcon('icons/whitearrow.png')
        else:
            icon = QIcon('icons/newarrow.png')
        
        self.sendbutton.setIcon(icon)
        self.sendbutton.setIconSize(QSize(20, 20))

        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.sendbutton.clicked.connect(self.on_send_button_clicked)

    def on_send_button_clicked(self):
        print('Send Button clicked!')
        #self.parent().input_widget.input_line.send_task_info_to_ai()
            # 检查父窗口是否处于等待状态
        if self.parent() and hasattr(self.parent(), 'is_waiting') and self.parent().is_waiting:
            # 显示等待提示
            if self.parent() and hasattr(self.parent(), 'display_widget') and self.parent().display_widget:
                self.parent().display_widget.show_waiting_message()
            return

        text = self.parent().input_widget.input_line.toPlainText().strip()
        if text:
            if self.parent() and hasattr(self.parent(), 'display_widget') and self.parent().display_widget:
                text = "工作任务：" + text 
                self.parent().display_widget.show_message(text)
                # 通过通信管理器发送消息
                comm_manager.send_message(text)
                print(f"sendbutton 发送消息: {text}")
          
            self.parent().input_widget.input_line.clear()
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()
class FloatPenDraw(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建按钮
        self.pendrawbutton = QPushButton('p', self)
        self.pendrawbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 6px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.pendrawbutton.resize(30, 30)
        
        icon = QIcon('icons/pen.png')
        self.pendrawbutton.setIcon(icon)
        self.pendrawbutton.setIconSize(QSize(19, 19))
        
        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.pendrawbutton.clicked.connect(self.on_pen_draw_clicked)

    def on_pen_draw_clicked(self):
        print('PenDraw clicked!')
        global app_background_color
        app_background_color = "#933"
        QMessageBox.information(self, '友情提示', '这是一个画笔圈图识图 智能绘制按钮,待后续实现。')
	
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()

class FloatVoiceChat(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建按钮
        self.voicechatbutton = QPushButton('v', self)
        self.voicechatbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')

        # 调整按钮大小
        self.voicechatbutton.resize(30, 30)
        #self.voicechatbutton.setFont(QFont('Calibri', 12)) 不生效
        icon = QIcon('voice.png')
        self.voicechatbutton.setIcon(icon)
        self.voicechatbutton.setIconSize(QSize(20, 20))
        
        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.voicechatbutton.clicked.connect(self.on_voice_chat_clicked)

    def on_voice_chat_clicked(self):
        print('VoiceChat clicked!')
        global app_background_color
        app_background_color = "#339"
        QMessageBox.information(self, '友情提示', '这是一个语音聊天，用户语音交互的按钮,待后续实现。')
	
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()

class FloatAddButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        #self.show()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建按钮
        self.addbutton = QPushButton('+', self)
        self.addbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.addbutton.resize(30, 30)
        #self.addbutton.setFont(QFont('Calibri', 12))
        #icon = QIcon('icons/jia.png')
        #self.addbutton.setIcon(icon)
        #self.addbutton.setIconSize(QSize(20, 20))

        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.addbutton.clicked.connect(self.on_add_button_clicked)

    def on_add_button_clicked(self):
        print('AddButton clicked!')
        QMessageBox.information(self, '友情提示', '这是一个添加附件，如图片、视频、文档的按钮,待后续实现。')
	
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()

class FloatQuoteButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建按钮
        self.quotebutton = QPushButton('#', self)
        self.quotebutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 7px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.quotebutton.resize(30, 30)
        self.quotebutton.setFont(QFont('Calibri', 12))
        icon = QIcon('icons/newsharp.png')
        self.quotebutton.setIcon(icon)
        self.quotebutton.setIconSize(QSize(20, 20))
        
        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.quotebutton.clicked.connect(self.on_quote_button_clicked)

    def on_quote_button_clicked(self):
        print('QuoteButton clicked!')
        global app_background_color
        app_background_color = "#393"
        QMessageBox.information(self, '友情提示', '这是一个引用上下文的按钮,待后续实现。')
	
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()


class FloatAtButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建按钮
        self.atbutton = QPushButton('@', self)
        self.atbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                text-align: left; 
                padding-left: 5px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')

        # 调整按钮大小
        self.atbutton.resize(30, 30)
        self.atbutton.setFont(QFont('Calibri', 12))
        icon = QIcon('icons/newat.png')
        self.atbutton.setIcon(icon)
        self.atbutton.setIconSize(QSize(20, 20))

        # 计算屏幕中心位置并移动窗口
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        #self.move(x, y)
        
        # 连接按钮点击事件
        self.atbutton.clicked.connect(self.on_at_button_clicked)

    def on_at_button_clicked(self):
        print('AtButton clicked!')
        global app_background_color
        app_background_color = "#111"
        QMessageBox.information(self, '友情提示', '这是一个@内置智能体，如MCP工具的按钮,待后续实现。')
	
    # 实现窗口拖动功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            #self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #self.move(event.globalPos() - self.dragPosition)
            event.accept()

    '''
    def paintEvent(self, event):
        # 重写paintEvent方法，根据按钮大小自动调整字体
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
       
        # 绘制按钮背景
        rect = self.rect()
        radius = min(rect.width(), rect.height()) // 5
        
        # 根据状态设置背景颜色
        if self.isDown():
            painter.setBrush(QColor('#4CAF50'))
        elif self.underMouse():
            painter.setBrush(QColor('#3e8e41'))
        else:
            painter.setBrush(QColor('#244a39'))

        painter.drawRoundedRect(rect, radius, radius)

        rect = self.rect()
        painter.setPen(Qt.NoPen)
        
        # 计算字体大小（根据按钮大小的60%）
        font_size = int(min(rect.width(), rect.height())*3)
        font = QFont('Microsoft YaHei', font_size, QFont.Bold)
        painter.setFont(font)
        
        # 绘制文本
        painter.setPen(QColor('white'))
        print(f"rect: {rect}")
        print(f"text: {self.atbutton.text()}")
        painter.drawText(rect, Qt.AlignCenter, self.atbutton.text())
    '''

class FloatComboBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        #global app_background_color
        # 设置窗口为透明和无边框
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        base_width = 112
        base_height = 30

        # 添加模型选择框
        self.model_combo = QComboBox(self)
        #self.model_combo.setPlaceholderText("Model")
        #self.model_combo.addItem('HuoShan-Vision')
        #self.model_combo.addItem('Model')
        self.model_combo.addItem('HuoShan-Vision')
        self.model_combo.addItem('Other Model 1')
        self.model_combo.addItem('Other Model 2')
        self.model_combo.setStyleSheet(f'''
            QComboBox {{
                background-color: {app_background_color}; 
                color: #fff; 
                border: 1px solid #121212; 
                border-radius: 10px; 
                padding: 5px; 
                font-family: "Microsoft YaHei"; 
                font-size: 10px; 
            }}
            QComboBox::drop-down {{
                border-left: 1px solid #121212; 
            }}
            QComboBox QAbstractItemView {{
                background-color: #222; 
                color: #fff; 
                border: 1px solid #121212; 
                text-align: left; /* 或者使用 center 来居中文本 */
                min-width: 150px;
            }}
            QComboBox::down-arrow {{
                image: url(icons/down.png);
                width: 12px;
                height: 12px;
            }}
        ''')

        '''
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin: 3px;
            }
        '''

        # 调整按钮大小
        self.model_combo.resize(112, 30)
        #self.update_combo_box_text()
        # 注册一个槽来更新文本，例如在窗口大小改变时
        self.model_combo.currentIndexChanged.connect(self.update_combo_box_text)

    def update_combo_box_text(self):
        font = self.model_combo.font()
        metrics = QFontMetrics(font)
        width = self.model_combo.width() - self.model_combo.iconSize().width() - 10  # 减去图标大小和边距
        elided_text = metrics.elidedText(self.model_combo.currentText(), Qt.ElideRight, width)
        self.model_combo.setItemText(self.model_combo.currentIndex(), elided_text)
        #self.model_combo.setCurrentText(elided_text)

    def get_scaled_size(self, base_width, base_height):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_width * scale_factor), int(base_height * scale_factor)
            except Exception as e:
                print(f"Error getting scaled size: {e}")
        return base_width, base_height

def get_scaled_font_size(self, base_size):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_size * scale_factor)
            except Exception as e:
                print(f"Error getting scaled font size: {e}")
        return base_size


class FloatInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui()

    def init_ui(self):
        #global app_background_color
        self.setWindowTitle("输入框")
        base_width, base_height = 280, 40
        scaled_width, scaled_height = self.get_scaled_size(base_width, base_height)
        self.setGeometry(0, 0, scaled_width, scaled_height)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        input_container = QFrame()
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
            }}
        """)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(self.get_scaled_size(4, 4)[0])

        self.input_line = CustomTextEdit(self)
        self.input_line.setPlaceholderText("与小华交流吧")
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.input_line.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 1px solid #666;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size}px;
            }}
            QTextEdit:focus {{
                border-color: #0078d4;
                outline: none;
            }}
        """)
        #self.input_line.returnPressed.connect(self.handle_return_pressed)
        self.input_line.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.input_line.installEventFilter(self)
        
        # 创建按钮
        self.addbutton = QPushButton('+', self)
        self.addbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.addbutton.resize(30, 30)
        self.addbutton.setFixedHeight(30)
        self.addbutton.setFixedWidth(30)
        #self.addbutton.setFont(QFont('Calibri', 12))
        #icon = QIcon('icons/newat.png')
        #self.addbutton.setIcon(icon)
        #self.addbutton.setIconSize(QSize(20, 20))
         
        # 连接按钮点击事件
        self.addbutton.clicked.connect(self.on_add_button_clicked)
        #self.add_button = FloatAddButton(self)

        # 创建按钮
        self.atbutton = QPushButton('@', self)
        self.atbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                text-align: left; 
                padding-left: 5px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')

        # 调整按钮大小
        self.atbutton.resize(30, 30)
        self.atbutton.setFixedHeight(30)
        self.atbutton.setFixedWidth(30)
        self.atbutton.setFont(QFont('Calibri', 12))
        icon = QIcon('icons/newat.png')
        self.atbutton.setIcon(icon)
        self.atbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.atbutton.clicked.connect(self.on_at_button_clicked)


        # 创建按钮
        self.quotebutton = QPushButton('#', self)
        self.quotebutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 7px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.quotebutton.resize(30, 30)
        self.quotebutton.setFixedHeight(30)
        self.quotebutton.setFixedWidth(30)
        self.quotebutton.setFont(QFont('Calibri', 12))
        icon = QIcon('icons/newsharp.png')
        self.quotebutton.setIcon(icon)
        self.quotebutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.quotebutton.clicked.connect(self.on_quote_button_clicked)


        # 创建按钮
        self.voicechatbutton = QPushButton('v', self)
        self.voicechatbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.voicechatbutton.resize(30, 30)
        self.voicechatbutton.setFixedHeight(30)
        self.voicechatbutton.setFixedWidth(30)
        #self.voicechatbutton.setFont(QFont('Calibri', 12)) 不生效
        icon = QIcon('icons/voice.png')
        self.voicechatbutton.setIcon(icon)
        self.voicechatbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.voicechatbutton.clicked.connect(self.on_voice_chat_clicked)

	
        # 创建按钮
        self.pendrawbutton = QPushButton('p', self)
        self.pendrawbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 6px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.pendrawbutton.resize(30, 30)
        self.pendrawbutton.setFixedHeight(30)
        self.pendrawbutton.setFixedWidth(30)

        icon = QIcon('icons/pen.png')
        self.pendrawbutton.setIcon(icon)
        self.pendrawbutton.setIconSize(QSize(19, 19))
        
        # 连接按钮点击事件
        self.pendrawbutton.clicked.connect(self.on_pen_draw_clicked)

        
        button_color = "green"
        #if app_background_color == "#393":
        #    button_color = "white"
        #    print("背景颜色为绿色，按钮颜色设置为白色")
        #print(f"按钮颜色为: {button_color}")
        
        # 创建按钮
        self.sendbutton = QPushButton('↑', self)
        self.sendbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: {button_color};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.sendbutton.resize(30, 30)
        self.sendbutton.setFixedHeight(30)
        self.sendbutton.setFixedWidth(30)
        self.sendbutton.setFont(QFont('Calibri', 12))
        if app_background_color == "#393":
            icon = QIcon('icons/whitearrow.png')
        else:
            icon = QIcon('icons/newarrow.png')
        
        self.sendbutton.setIcon(icon)
        self.sendbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.sendbutton.clicked.connect(self.on_send_button_clicked)

        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(self.get_scaled_size(4, 4)[0])
        #button_layout.setAlignment(Qt.AlignLeft) 
        button_layout.addWidget(self.addbutton)
        button_layout.addWidget(self.atbutton)
        button_layout.addWidget(self.quotebutton)
        button_layout.addWidget(self.voicechatbutton)
        button_layout.addWidget(self.pendrawbutton)
        button_layout.addWidget(self.sendbutton)

        input_layout.addWidget(self.input_line)
        input_container.setLayout(input_layout)
        main_layout.addWidget(input_container)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)


    def on_add_button_clicked(self):
        print('AddButton clicked!')
        QMessageBox.information(self, '友情提示', '这是一个添加附件，如图片、视频、文档的按钮,待后续实现。')


    def on_at_button_clicked(self):
        print('AtButton clicked!')
        global app_background_color
        app_background_color = "#111"
        QMessageBox.information(self, '友情提示', '这是一个@内置智能体，如MCP工具的按钮,待后续实现。')
 
 
    def on_quote_button_clicked(self):
        print('QuoteButton clicked!')
        global app_background_color
        app_background_color = "#393"
        QMessageBox.information(self, '友情提示', '这是一个引用上下文的按钮,待后续实现。')


    def on_voice_chat_clicked(self):
        print('VoiceChat clicked!')
        global app_background_color
        app_background_color = "#339"
        QMessageBox.information(self, '友情提示', '这是一个语音聊天，用户语音交互的按钮,待后续实现。')

    
    def on_pen_draw_clicked(self):
        print('PenDraw clicked!')
        global app_background_color
        app_background_color = "#933"
        QMessageBox.information(self, '友情提示', '这是一个画笔圈图识图 智能绘制按钮,待后续实现。')


    def on_send_button_clicked(self):
        print('SendButton clicked!')
        QMessageBox.information(self, '友情提示', '这是一个发送消息的按钮,待后续实现。')


    def get_scaled_size(self, base_width, base_height):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_width * scale_factor), int(base_height * scale_factor)
            except Exception as e:
                print(f"Error getting scaled size: {e}")
        return base_width, base_height

    def get_scaled_font_size(self, base_size):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_size * scale_factor)
            except Exception as e:
                print(f"Error getting scaled font size: {e}")
        return base_size

    def hide_input(self):
        self.hide()

        if self.parent():
            self.parent().is_input_visible = False
            self.parent().is_hovered_on_input = False

    def set_scaled_geometry(self, x, y):
        if self.parent():
            current_screen = self.parent().get_current_screen()
            if current_screen:
                self.move(x, y)
                return
        self.move(x, y)


class FloatWorkBenchWidget(QWidget):
    def __init__(self, parent=None, saved_content=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.workbench_text = saved_content  # 初始化时使用保存的内容
        # 高度调整相关变量
        self.is_resizing = False
        self.resize_start_y = 0
        self.min_height = 50  # 最小高度限制
        self.init_ui()
        #self.show()


    def init_ui(self):
        #global app_background_color
        self.setWindowTitle("小华")
        base_width, base_height = 280,75   #280, 200
        scaled_width, scaled_height = self.get_scaled_size(base_width, base_height)
        self.setGeometry(0, 0, scaled_width, scaled_height)
        print(f"workbench scaled_width: {scaled_width}, scaled_height: {scaled_height}")
        #self.setGeometry(0, 0, 280, 20)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        workbench_container = QFrame()
        workbench_container.setFixedHeight(scaled_height)
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        workbench_container.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
                border: 0.2px solid #555;  /* 更细的边框 */
            }}
        """)

        # 使用QTextEdit支持文本选择和复制
        self.workbench_text_edit = QTextEdit()
        self.workbench_text_edit.setReadOnly(True)  # 设置为只读
        self.workbench_text_edit.setUndoRedoEnabled(False)
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.workbench_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 0.5px solid #555;  /* 更细的边框 */
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size+5}px;
            }}
        """)
        self.workbench_text_edit.setWordWrapMode(True)
        self.workbench_text_edit.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # 启用HTML支持以显示markdown
        self.workbench_text_edit.setAcceptRichText(True)
        self.workbench_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 初始化时设置保存的内容
        #if self.display_text:
        #    self.set_display_content(self.display_text)
        #else:
        #    self.workbench_text_edit.clear()
        #self.workbench_text_edit.setAlignment(Qt.AlignCenter)
        #self.workbench_text_edit.setText("小华工作台")
        self.workbench_text_edit.setHtml('<b><p align="center">小华工作台</p><p align="center">^_^</p></b>')
        
        layout.addWidget(self.workbench_text_edit)
        workbench_container.setLayout(layout)

        layout1 = QVBoxLayout()
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(0)
        workbench_container1 = QFrame()
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        workbench_container1.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
                border: 0.2px solid #555;  /* 更细的边框 */
            }}
        """)

        # 使用QTextEdit支持文本选择和复制
        self.workbench_text_edit1 = QTextEdit()
        self.workbench_text_edit1.setReadOnly(True)  # 设置为只读
        self.workbench_text_edit1.setUndoRedoEnabled(False)
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.workbench_text_edit1.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 0.5px solid #555;  /* 更细的边框 */
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size+5}px;
            }}
        """)
        self.workbench_text_edit1.setWordWrapMode(True)
        self.workbench_text_edit1.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # 启用HTML支持以显示markdown
        self.workbench_text_edit1.setAcceptRichText(True)
        self.workbench_text_edit1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 初始化时设置保存的内容
        #if self.display_text:
        #    self.set_display_content(self.display_text)
        #else:
        #    self.workbench_text_edit.clear()
        #self.workbench_text_edit.setAlignment(Qt.AlignCenter)
        #self.workbench_text_edit.setText("小华工作台")
        self.workbench_text_edit1.setHtml('<b><p align="center">小华工作台二</p><p align="center">^_^</p></b>')
        
        layout1.addWidget(self.workbench_text_edit1)
        workbench_container1.setLayout(layout1)

        self.docer_enable = True
        self.docer = QLabel(self)
        self.docer.setAlignment(Qt.AlignCenter)
        #self.set_role_label(self.docer, "docer", "小华.png")
        self.set_role_label(self.docer, "docer", "icons/docer1.png")
        self.docer.mousePressEvent = self.docer_clicked
        
        self.configer_enable = False
        self.configer = QLabel(self)
        self.configer.setAlignment(Qt.AlignCenter)
        self.set_role_label(self.configer, "configer", "icons/configer2.png")
        self.configer.mousePressEvent = self.configer_clicked

        self.worker_enable = False
        self.worker = QLabel(self)
        self.worker.setAlignment(Qt.AlignCenter)
        self.set_role_label(self.worker, "worker", "icons/worker2.png")
        self.worker.mousePressEvent = self.worker_clicked


        self.coder_enable = False
        self.coder = QLabel(self)
        self.coder.setAlignment(Qt.AlignCenter)
        self.set_role_label(self.coder, "coder", "icons/coder2.png")
        self.coder.mousePressEvent = self.coder_clicked

        self.xiaoxia_enable = False
        self.xiaoxia = QLabel(self)
        self.xiaoxia.setAlignment(Qt.AlignCenter)
        self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia2.png")
        self.xiaoxia.mousePressEvent = self.xiaoxia_clicked

        bot_layout = QHBoxLayout()
        bot_layout.setContentsMargins(0, 0, 0, 0)
        bot_layout.setSpacing(0)
        bot_layout.addWidget(self.docer)
        bot_layout.addWidget(self.configer)
        bot_layout.addWidget(self.worker)
        bot_layout.addWidget(self.coder)
        bot_layout.addWidget(self.xiaoxia)
        #layout.addWidget(self.xiaoxia)
        #layout.addWidget(self.workbench_text_edit)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(workbench_container)
        #main_layout.addWidget(workbench_container1) 
        main_layout.addLayout(bot_layout)
        
        #self.setLayout(main_layout)

        # dispaly widget 

        self.display_text = ""  # 初始化时使用保存的内容
        # 高度调整相关变量
        self.is_resizing = False
        self.resize_start_y = 0
        self.min_height = 100  # 最小高度限制
        # 连接通信器的响应信号
        comm_manager.response_received.connect(self.on_response_received)


        #global app_background_color
        #self.setWindowTitle("显示框")
        display_base_width, display_base_height = 280, 220
        display_scaled_width, display_scaled_height = self.get_scaled_size(display_base_width, display_base_height)
        #self.setGeometry(0, 0, display_scaled_width, display_scaled_height)

        display_layout = QVBoxLayout()
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(0)

        display_container = QFrame()
        display_container.setFixedHeight(display_scaled_height)
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        display_container.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
                border: 0.2px solid #555;  /* 更细的边框 */
            }}
        """)

        # 使用QTextEdit支持文本选择和复制
        self.display_text_edit = QTextEdit()
        self.display_text_edit.setReadOnly(True)  # 设置为只读
        self.display_text_edit.setUndoRedoEnabled(False)
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.display_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 0.5px solid #555;  /* 更细的边框 */
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size}px;
            }}
        """)
        self.display_text_edit.setWordWrapMode(True)
        self.display_text_edit.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # 启用HTML支持以显示markdown
        self.display_text_edit.setAcceptRichText(True)
        self.display_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.display_text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 初始化时设置保存的内容
        if self.display_text:
            self.set_display_content(self.display_text)
        else:
            self.display_text_edit.clear()

        self.set_display_content('我是docer。')

        self.waiting_label = QLabel("等待中...\n请快速将鼠标移动到被控窗口并单击😁")
        self.waiting_label.setStyleSheet(f"""
            QLabel {{
                background-color: #444;
                border: 1px solid #666;
                border-radius: {self.get_scaled_size(4, 4)[0]}px;
                padding: {self.get_scaled_size(6, 4)[1]}px {self.get_scaled_size(6, 4)[0]}px;
                color: white;
                font-size: {self.get_scaled_font_size(12)}px;
            }}
        """)
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.hide()

        # 等待提示标签
        self.waiting_input_label = QLabel("等待时不能上传指令")
        self.waiting_input_label.setStyleSheet(f"""
            QLabel {{
                background-color: #444;
                border: 1px solid #ff4444;
                border-radius: {self.get_scaled_size(4, 4)[0]}px;
                padding: {self.get_scaled_size(6, 4)[1]}px {self.get_scaled_size(6, 4)[0]}px;
                color: #ff4444;
                font-size: {self.get_scaled_font_size(12)}px;
            }}
        """)
        self.waiting_input_label.setAlignment(Qt.AlignCenter)
        self.waiting_input_label.hide()

        display_layout.addWidget(self.display_text_edit)
        display_layout.addWidget(self.waiting_label)
        display_layout.addWidget(self.waiting_input_label)
        display_container.setLayout(display_layout)

        main_layout.addWidget(display_container)
        
        #self.setLayout(main_layout)

        # input widget 
        input_base_width, input_base_height = 280, 100   
        input_scaled_width, input_scaled_height = self.get_scaled_size(input_base_width, input_base_height)
        #self.setGeometry(0, 0, input_scaled_width, input_scaled_height)

        #input_main_layout = QVBoxLayout()
        #input_main_layout.setContentsMargins(0, 0, 0, 0)
        #input_main_layout.setSpacing(0)

        input_container = QFrame()
        input_container.setFixedHeight(input_scaled_height)
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
            }}
        """)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(self.get_scaled_size(4, 4)[0])

        self.input_line = CustomTextEdit(self)
        self.input_line.setPlaceholderText("与小华交流吧")
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.input_line.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 1px solid #666;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size}px;
            }}
            QTextEdit:focus {{
                border-color: #0078d4;
                outline: none;
            }}
        """)
        #self.input_line.returnPressed.connect(self.handle_return_pressed)
        self.input_line.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.input_line.installEventFilter(self)
        
        # 创建按钮
        self.addbutton = QPushButton('+', self)
        self.addbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 20px;
                font-weight: bold;
                text-align: left; 
                padding-left: 6px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.addbutton.resize(30, 30)
        self.addbutton.setFixedHeight(30)
        self.addbutton.setFixedWidth(30)
        self.addbutton.setFont(QFont('Calibri', 12))
        #icon = QIcon('newat.png')
        icon = QIcon('icons/jia.png')
        self.addbutton.setIcon(icon)
        self.addbutton.setIconSize(QSize(20, 20))
         
        # 连接按钮点击事件
        self.addbutton.clicked.connect(self.on_add_button_clicked)
        #self.add_button = FloatAddButton(self)

        # 创建按钮
        self.atbutton = QPushButton('@', self)
        self.atbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                text-align: left; 
                padding-left: 5px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')

        # 调整按钮大小
        self.atbutton.resize(30, 30)
        self.atbutton.setFixedHeight(30)
        self.atbutton.setFixedWidth(30)
        self.atbutton.setFont(QFont('Calibri', 12))
       #icon = QIcon('icons/newat.png')
        icon = QIcon('icons/jingat.png')
        self.atbutton.setIcon(icon)
        self.atbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.atbutton.clicked.connect(self.on_at_button_clicked)


        # 创建按钮
        self.quotebutton = QPushButton('#', self)
        self.quotebutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 7px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.quotebutton.resize(30, 30)
        self.quotebutton.setFixedHeight(30)
        self.quotebutton.setFixedWidth(30)
        self.quotebutton.setFont(QFont('Calibri', 12))
        #icon = QIcon('newsharp.png')
        icon = QIcon('icons/jing.png')
        self.quotebutton.setIcon(icon)
        self.quotebutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.quotebutton.clicked.connect(self.on_quote_button_clicked)


        # 创建按钮
        self.voicechatbutton = QPushButton('v', self)
        self.voicechatbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.voicechatbutton.resize(30, 30)
        self.voicechatbutton.setFixedHeight(30)
        self.voicechatbutton.setFixedWidth(30)
        #self.voicechatbutton.setFont(QFont('Calibri', 12)) 不生效
        icon = QIcon('icons/voice.png')
        self.voicechatbutton.setIcon(icon)
        self.voicechatbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.voicechatbutton.clicked.connect(self.on_voice_chat_clicked)

	
        # 创建按钮
        self.pendrawbutton = QPushButton('p', self)
        self.pendrawbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                text-align: left; 
                padding-left: 6px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.pendrawbutton.resize(30, 30)
        self.pendrawbutton.setFixedHeight(30)
        self.pendrawbutton.setFixedWidth(30)

        icon = QIcon('icons/pen.png')
        self.pendrawbutton.setIcon(icon)
        self.pendrawbutton.setIconSize(QSize(19, 19))
        
        # 连接按钮点击事件
        self.pendrawbutton.clicked.connect(self.on_pen_draw_clicked)

        
        button_color = "green"
        #if app_background_color == "#393":
        #    button_color = "white"
        #    print("背景颜色为绿色，按钮颜色设置为白色")
        #print(f"按钮颜色为: {button_color}")
        
        # 创建按钮
        self.sendbutton = QPushButton('↑', self)
        self.sendbutton.setStyleSheet(f'''
            QPushButton {{
                background-color: {app_background_color};
                color: {button_color};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left; 
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: #222;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        ''')
  
        # 调整按钮大小
        self.sendbutton.resize(30, 30)
        self.sendbutton.setFixedHeight(30)
        self.sendbutton.setFixedWidth(30)
        self.sendbutton.setFont(QFont('Calibri', 12))
        if app_background_color == "#393":
            icon = QIcon('icons/whitearrow.png')
        else:
            icon = QIcon('icons/newarrow.png')
        
        icon = QIcon('icons/whitearrow.png')

        self.sendbutton.setIcon(icon)
        self.sendbutton.setIconSize(QSize(20, 20))
        
        # 连接按钮点击事件
        self.sendbutton.clicked.connect(self.on_send_button_clicked)

        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(self.get_scaled_size(4, 4)[0])
        #button_layout.setAlignment(Qt.AlignLeft) 
        button_layout.addWidget(self.addbutton)
        button_layout.addWidget(self.atbutton)
        button_layout.addWidget(self.quotebutton)
        button_layout.addWidget(self.voicechatbutton)
        button_layout.addWidget(self.pendrawbutton)
        button_layout.addWidget(self.sendbutton)

        input_layout.addWidget(self.input_line)
        input_container.setLayout(input_layout)

        #input_main_layout.addWidget(input_container)
        #input_main_layout.addLayout(button_layout)

        main_layout.addWidget(input_container)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)


    def on_add_button_clicked(self):
        print('AddButton clicked!')
        QMessageBox.information(self, '友情提示', '这是一个添加附件，如图片、视频、文档的按钮,待后续实现。')


    def on_at_button_clicked(self):
        print('AtButton clicked!')
        global app_background_color
        app_background_color = "#111"
        QMessageBox.information(self, '友情提示', '这是一个@内置智能体，如MCP工具的按钮,待后续实现。')
 
 
    def on_quote_button_clicked(self):
        print('QuoteButton clicked!')
        global app_background_color
        app_background_color = "#393"
        QMessageBox.information(self, '友情提示', '这是一个引用上下文的按钮,待后续实现。')


    def on_voice_chat_clicked(self):
        print('VoiceChat clicked!')
        global app_background_color
        app_background_color = "#339"
        QMessageBox.information(self, '友情提示', '这是一个语音聊天，用户语音交互的按钮,待后续实现。')

    
    def on_pen_draw_clicked(self):
        print('PenDraw clicked!')
        global app_background_color
        app_background_color = "#933"
        QMessageBox.information(self, '友情提示', '这是一个画笔圈图识图 智能绘制按钮,待后续实现。')


    def on_send_button_clicked(self):
        print('SendButton clicked!')
        QMessageBox.information(self, '友情提示', '这是一个发送消息的按钮,待后续实现。')

    def docer_clicked(self, event):
        if event.button() == Qt.LeftButton:
            if not self.docer_enable:
                self.docer_enable = True
                self.configer_enable = False
                self.worker_enable = False
                self.coder_enable = False
                self.xiaoxia_enable = False
                
                self.set_role_label(self.docer, "docer", "icons/docer1.png")
                self.set_role_label(self.configer, "configer", "icons/configer2.png")
                self.set_role_label(self.worker, "worker", "icons/worker2.png")
                self.set_role_label(self.coder, "coder", "icons/coder2.png")
                self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia2.png")
            
            print('docer clicked!')
            self.set_display_content('我是docer。')
            QMessageBox.information(self, '友情提示', '我是docer。')

    def configer_clicked(self, event):
        if event.button() == Qt.LeftButton:
            if not self.configer_enable:
                self.docer_enable = False
                self.configer_enable = True
                self.worker_enable = False
                self.coder_enable = False
                self.xiaoxia_enable = False
                
                self.set_role_label(self.docer, "docer", "icons/docer2.png")
                self.set_role_label(self.configer, "configer", "icons/configer1.png")
                self.set_role_label(self.worker, "worker", "icons/worker2.png")
                self.set_role_label(self.coder, "coder", "icons/coder2.png")
                self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia2.png")

            print('configer clicked!')
            self.set_display_content('我是configer。')
            QMessageBox.information(self, '友情提示', '我是configer。')

    def worker_clicked(self, event):
        if event.button() == Qt.LeftButton:
            if not self.worker_enable:
                self.docer_enable = False
                self.configer_enable = False
                self.worker_enable = True
                self.coder_enable = False
                self.xiaoxia_enable = False
                
                self.set_role_label(self.docer, "docer", "icons/docer2.png")
                self.set_role_label(self.configer, "configer", "icons/configer2.png")
                self.set_role_label(self.worker, "worker", "icons/worker1.png")
                self.set_role_label(self.coder, "coder", "icons/coder2.png")
                self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia2.png")
            
            print('worker clicked!')
            self.set_display_content('我是worker。')
            QMessageBox.information(self, '友情提示', '我是worker。')
    
    def coder_clicked(self, event):
        if event.button() == Qt.LeftButton:
            if not self.coder_enable:
                self.docer_enable = False
                self.configer_enable = False
                self.worker_enable = False
                self.coder_enable = True
                self.xiaoxia_enable = False
                
                self.set_role_label(self.docer, "docer", "icons/docer2.png")
                self.set_role_label(self.configer, "configer", "icons/configer2.png")
                self.set_role_label(self.worker, "worker", "icons/worker2.png")
                self.set_role_label(self.coder, "coder", "icons/coder1.png")
                self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia2.png")
            
            print('coder clicked!')
            self.set_display_content('我是coder。')
            QMessageBox.information(self, '友情提示', '我是coder。')

    def xiaoxia_clicked(self, event):
        if event.button() == Qt.LeftButton:
            if not self.xiaoxia_enable:
                self.docer_enable = False
                self.configer_enable = False
                self.worker_enable = False
                self.coder_enable = False
                self.xiaoxia_enable = True
                
                self.set_role_label(self.docer, "docer", "icons/docer2.png")
                self.set_role_label(self.configer, "configer", "icons/configer2.png")
                self.set_role_label(self.worker, "worker", "icons/worker2.png")
                self.set_role_label(self.coder, "coder", "icons/coder2.png")
                self.set_role_label(self.xiaoxia, "xiaoxia", "icons/xiaoxia1.png")
            
            print('xiaoxia clicked!')
            self.set_display_content('我是小霞。')
            QMessageBox.information(self, '友情提示', '我是小霞。')

    def set_role_label(self, role_label, role_name, role_img_path):
        role_label.setText(role_name)
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio()
        #print("screen ratio:", ratio)
        #print(f"screen ratio: {ratio:.2f}")

        if os.path.exists(role_img_path):
            pixmap = QPixmap(role_img_path)
            if not pixmap.isNull():
                small_pixmap = pixmap.scaled(
                    int(60 * ratio), int(60 * ratio), # self.get_scaled_font_size(80), self.get_scaled_font_size(80),
                    #80, 80,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                small_pixmap.setDevicePixelRatio(ratio)
                role_label.setPixmap(small_pixmap)

    def get_scaled_size(self, base_width, base_height):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_width * scale_factor), int(base_height * scale_factor)
            except Exception as e:
                print(f"Error getting scaled size: {e}")
        return base_width, base_height

    def get_scaled_font_size(self, base_size):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_size * scale_factor)
            except Exception as e:
                print(f"Error getting scaled font size: {e}")
        return base_size

    def hide_input(self):
        self.hide()

        if self.parent():
            self.parent().is_input_visible = False
            self.parent().is_hovered_on_input = False

    def set_scaled_geometry(self, x, y):
        if self.parent():
            current_screen = self.parent().get_current_screen()
            if current_screen:
                self.move(x, y)
                return
        self.move(x, y)

    def show_message(self, text):
        self.workbench_text = text
        self.workbench_text_edit.setText(text)

    def set_display_content(self, text):
        """设置显示内容，支持markdown格式"""
        self.workbench_text = text
        
        # 创建禁用输入标志文件，确保显示内容后2秒内无法输入
        try:
            #with open(INPUT_DISABLE_FLAG, 'w') as f:
            #    f.write('')
            #print(f"已创建输入禁用标志，2秒内无法输入")
            print(f"已入不禁用")
            # 设置2秒后自动删除标志文件，恢复输入功能
            #QTimer.singleShot(2000, self.remove_disable_flag)
            
        except Exception as e:
            print(f"设置输入禁用标志失败: {e}")
            
        if markdown_available:
            # 将markdown转换为HTML
            html_content = markdown.markdown(text)
            # 添加基本的CSS样式以美化显示
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        color: white;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #0078d4;
                        margin-top: 10px;
                        margin-bottom: 5px;
                    }}
                    p {{
                        margin: 5px 0;
                    }}
                    code {{
                        background-color: #555;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #555;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    blockquote {{
                        border-left: 3px solid #0078d4;
                        margin-left: 0;
                        padding-left: 10px;
                        color: #aaa;
                    }}
                    ul, ol {{
                        margin: 5px 0;
                        padding-left: 20px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            self.workbench_text_edit.setHtml(styled_html)
        else:
            # 不支持markdown时，使用纯文本
            self.workbench_text_edit.setText(text)
    
    def on_response_received(self, response_text):
        # 收到响应时显示
        self.workbench_text = response_text
        self.waiting_label.hide()
        self.set_display_content(response_text)

        maximum = self.workbench_text_edit.verticalScrollBar().maximum()
        self.workbench_text_edit.verticalScrollBar().setValue(maximum)
        # 移动光标到末尾并插入文本
        cursor = self.workbench_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)       
        # 确保光标可见（滚动到底部）
        self.workbench_text_edit.setTextCursor(cursor)
        self.workbench_text_edit.ensureCursorVisible()
        self.workbench_text_edit.show()
        # 通知父窗口等待状态结束
        if self.parent() and hasattr(self.parent(), 'set_waiting_state'):
            self.parent().set_waiting_state(False)
            # 将内容保存到父窗口
            self.parent().saved_display_content = response_text

    def mousePressEvent(self, event):
        # 检查是否点击了窗口顶部边缘用于调整高度
        #if event.button() == Qt.LeftButton and event.pos().y() <= 10:
        #    self.is_resizing = True
        #    self.resize_start_y = event.globalY()
        #    self.setCursor(Qt.SizeVerCursor)

        if event.button() == Qt.LeftButton:
            print('into clicked!')
            """
            sender = self.sender()
            if sender == self.label:
                print('docer clicked!')
                QMessageBox.information(self, '友情提示', '我是docer。')
            elif sender == self.label1:
                print('worker clicked!')
                QMessageBox.information(self, '友情提示', '我是worker')
            elif sender == self.label2:
                print('chater clicked!')
                QMessageBox.information(self, '友情提示', '我是chater')
            """
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        # 处理高度调整
        if self.is_resizing:
            current_y = event.globalY()
            delta = self.resize_start_y - current_y
            new_height = self.height() + delta
            
            # 确保高度不小于最小值
            if new_height >= self.min_height:
                self.resize(self.width(), new_height)
                self.resize_start_y = current_y
                
                # 调整显示文本框的大小
                #self.display_text_edit.setMinimumHeight(new_height - 40)
                print("不设置最小高度")
                
                # 更新父窗口中的位置信息
                if self.parent() and hasattr(self.parent(), 'update_display_position'):
                    self.parent().update_display_position()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 结束调整大小
        if self.is_resizing:
            self.is_resizing = False
            self.setCursor(Qt.ArrowCursor)
            # 保存高度到父窗口
            if self.parent() and hasattr(self.parent(), 'saved_display_height'):
                self.parent().saved_display_height = self.height()
        super().mouseReleaseEvent(event)
    
    def hide_display(self):
        self.hide()
        if self.parent():
            self.parent().is_display_visible = False
            # 隐藏时保存内容到父窗口
            self.parent().saved_display_content = self.display_text


    def show_message(self, text):
        self.display_text = text
        self.display_text_edit.setText(text)
        #self.display_text_edit.hide()
        #self.waiting_label.setText("等待中...\n请快速将鼠标移动到被控窗口并单击😁")
        #self.waiting_label.show()
        #self.waiting_input_label.hide()
        #self.wait_timer.start(5000)  # 5秒后显示回答

    def set_display_content(self, text):
        """设置显示内容，支持markdown格式"""
        self.display_text = text
        
        # 创建禁用输入标志文件，确保显示内容后2秒内无法输入
        try:
            #with open(INPUT_DISABLE_FLAG, 'w') as f:
            #    f.write('')
            #print(f"已创建输入禁用标志，2秒内无法输入")
            print(f"已入不禁用")
            # 设置2秒后自动删除标志文件，恢复输入功能
            #QTimer.singleShot(2000, self.remove_disable_flag)
            
        except Exception as e:
            print(f"设置输入禁用标志失败: {e}")
            
        if markdown_available:
            # 将markdown转换为HTML
            html_content = markdown.markdown(text)
            # 添加基本的CSS样式以美化显示
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        color: white;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #0078d4;
                        margin-top: 10px;
                        margin-bottom: 5px;
                    }}
                    p {{
                        margin: 5px 0;
                    }}
                    code {{
                        background-color: #555;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #555;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    blockquote {{
                        border-left: 3px solid #0078d4;
                        margin-left: 0;
                        padding-left: 10px;
                        color: #aaa;
                    }}
                    ul, ol {{
                        margin: 5px 0;
                        padding-left: 20px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            self.display_text_edit.setHtml(styled_html)
        else:
            # 不支持markdown时，使用纯文本
            self.display_text_edit.setText(text)
    
    def on_response_received(self, response_text):
        # 收到响应时显示
        self.display_text = response_text
        self.waiting_label.hide()
        self.set_display_content(response_text)
        # 移动光标到末尾并插入文本
        cursor = self.display_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)       
        # 确保光标可见（滚动到底部）
        self.display_text_edit.setTextCursor(cursor)
        self.display_text_edit.ensureCursorVisible()
        self.display_text_edit.show()
        # 通知父窗口等待状态结束
        if self.parent() and hasattr(self.parent(), 'set_waiting_state'):
            self.parent().set_waiting_state(False)
            # 将内容保存到父窗口
            self.parent().saved_display_content = response_text

    def show_waiting_message(self):
        self.waiting_input_label.show()
        QTimer.singleShot(2000, self.hide_waiting_message)

    def hide_waiting_message(self):
        self.waiting_input_label.hide()
    
    def remove_disable_flag(self):
        """删除输入禁用标志文件，恢复输入功能"""
        try:
            if os.path.exists(INPUT_DISABLE_FLAG):
                os.remove(INPUT_DISABLE_FLAG)
                print("已删除输入禁用标志，恢复输入功能")
                # 隐藏等待消息标签
                if hasattr(self, 'waiting_input_label'):
                    self.waiting_input_label.hide()
        except Exception as e:
            print(f"删除输入禁用标志失败: {e}")

    def mousePressEvent(self, event):
        # 检查是否点击了窗口顶部边缘用于调整高度
        if event.button() == Qt.LeftButton and event.pos().y() <= 10:
            self.is_resizing = True
            self.resize_start_y = event.globalY()
            self.setCursor(Qt.SizeVerCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        # 处理高度调整
        if self.is_resizing:
            current_y = event.globalY()
            delta = self.resize_start_y - current_y
            new_height = self.height() + delta
            
            # 确保高度不小于最小值
            if new_height >= self.min_height:
                self.resize(self.width(), new_height)
                self.resize_start_y = current_y
                
                # 调整显示文本框的大小
                self.display_text_edit.setMinimumHeight(new_height - 40)
                
                # 更新父窗口中的位置信息
                if self.parent() and hasattr(self.parent(), 'update_display_position'):
                    self.parent().update_display_position()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 结束调整大小
        if self.is_resizing:
            self.is_resizing = False
            self.setCursor(Qt.ArrowCursor)
            # 保存高度到父窗口
            if self.parent() and hasattr(self.parent(), 'saved_display_height'):
                self.parent().saved_display_height = self.height()
        super().mouseReleaseEvent(event)
    
    def hide_display(self):
        self.hide()
        if self.parent():
            self.parent().is_display_visible = False
            # 隐藏时保存内容到父窗口
            self.parent().saved_display_content = self.display_text



class FloatDisplayWidget(QWidget):
    def __init__(self, parent=None, saved_content=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.display_text = saved_content  # 初始化时使用保存的内容
        # 高度调整相关变量
        self.is_resizing = False
        self.resize_start_y = 0
        self.min_height = 100  # 最小高度限制
        self.init_ui()
        # 连接通信器的响应信号
        comm_manager.response_received.connect(self.on_response_received)


    def init_ui(self):
        #global app_background_color
        self.setWindowTitle("显示框")
        base_width, base_height = 280, 200
        scaled_width, scaled_height = self.get_scaled_size(base_width, base_height)
        self.setGeometry(0, 0, scaled_width, scaled_height)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        display_container = QFrame()
        scaled_radius, scaled_padding = self.get_scaled_size(8, 6)
        display_container.setStyleSheet(f"""
            QFrame {{
                background-color: {app_background_color};
                border-radius: {scaled_radius}px;
                padding: {scaled_padding}px;
                margin: {self.get_scaled_size(5, 5)[0]}px;
                border: 0.2px solid #555;  /* 更细的边框 */
            }}
        """)

        # 使用QTextEdit支持文本选择和复制
        self.display_text_edit = QTextEdit()
        self.display_text_edit.setReadOnly(True)  # 设置为只读
        self.display_text_edit.setUndoRedoEnabled(False)
        scaled_border_radius = self.get_scaled_size(4, 4)[0]
        scaled_padding_lr, scaled_padding_tb = self.get_scaled_size(6, 4)
        input_font_size = self.get_scaled_font_size(12)
        self.display_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #222;
                border: 0.5px solid #555;  /* 更细的边框 */
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_tb}px {scaled_padding_lr}px;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: {input_font_size}px;
            }}
        """)
        self.display_text_edit.setWordWrapMode(True)
        self.display_text_edit.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # 启用HTML支持以显示markdown
        self.display_text_edit.setAcceptRichText(True)
        self.display_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 初始化时设置保存的内容
        if self.display_text:
            self.set_display_content(self.display_text)
        else:
            self.display_text_edit.clear()

        self.waiting_label = QLabel("等待中...\n请快速将鼠标移动到被控窗口并单击😁")
        self.waiting_label.setStyleSheet(f"""
            QLabel {{
                background-color: #444;
                border: 1px solid #666;
                border-radius: {self.get_scaled_size(4, 4)[0]}px;
                padding: {self.get_scaled_size(6, 4)[1]}px {self.get_scaled_size(6, 4)[0]}px;
                color: white;
                font-size: {self.get_scaled_font_size(12)}px;
            }}
        """)
        self.waiting_label.setAlignment(Qt.AlignCenter)
        self.waiting_label.hide()

        # 等待提示标签
        self.waiting_input_label = QLabel("等待时不能上传指令")
        self.waiting_input_label.setStyleSheet(f"""
            QLabel {{
                background-color: #444;
                border: 1px solid #ff4444;
                border-radius: {self.get_scaled_size(4, 4)[0]}px;
                padding: {self.get_scaled_size(6, 4)[1]}px {self.get_scaled_size(6, 4)[0]}px;
                color: #ff4444;
                font-size: {self.get_scaled_font_size(12)}px;
            }}
        """)
        self.waiting_input_label.setAlignment(Qt.AlignCenter)
        self.waiting_input_label.hide()

        layout.addWidget(self.display_text_edit)
        layout.addWidget(self.waiting_label)
        layout.addWidget(self.waiting_input_label)
        display_container.setLayout(layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(display_container)
        self.setLayout(main_layout)

    def get_scaled_size(self, base_width, base_height):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_width * scale_factor), int(base_height * scale_factor)
            except Exception as e:
                print(f"Error getting scaled size: {e}")
        return base_width, base_height

    def get_scaled_font_size(self, base_size):
        if self.parent():
            try:
                parent = self.parent()
                current_screen = parent.screen() if hasattr(parent, 'screen') else None
                if not current_screen and hasattr(parent, 'get_current_screen'):
                    screen_rect = parent.get_current_screen()
                    for screen in QApplication.screens():
                        if screen.geometry() == screen_rect:
                            current_screen = screen
                            break
                if not current_screen:
                    current_screen = QApplication.primaryScreen()
                if current_screen:
                    scale_factor = current_screen.logicalDotsPerInch() / 96.0
                    return int(base_size * scale_factor)
            except Exception as e:
                print(f"Error getting scaled font size: {e}")
        return base_size

    def show_message(self, text):
        self.display_text = text
        self.display_text_edit.setText(text)
        #self.display_text_edit.hide()
        #self.waiting_label.setText("等待中...\n请快速将鼠标移动到被控窗口并单击😁")
        #self.waiting_label.show()
        #self.waiting_input_label.hide()
        #self.wait_timer.start(5000)  # 5秒后显示回答

    def set_display_content(self, text):
        """设置显示内容，支持markdown格式"""
        self.display_text = text
        
        # 创建禁用输入标志文件，确保显示内容后2秒内无法输入
        try:
            #with open(INPUT_DISABLE_FLAG, 'w') as f:
            #    f.write('')
            #print(f"已创建输入禁用标志，2秒内无法输入")
            print(f"已入不禁用")
            # 设置2秒后自动删除标志文件，恢复输入功能
            #QTimer.singleShot(2000, self.remove_disable_flag)
            
        except Exception as e:
            print(f"设置输入禁用标志失败: {e}")
            
        if markdown_available:
            # 将markdown转换为HTML
            html_content = markdown.markdown(text)
            # 添加基本的CSS样式以美化显示
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        color: white;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #0078d4;
                        margin-top: 10px;
                        margin-bottom: 5px;
                    }}
                    p {{
                        margin: 5px 0;
                    }}
                    code {{
                        background-color: #555;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #555;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    blockquote {{
                        border-left: 3px solid #0078d4;
                        margin-left: 0;
                        padding-left: 10px;
                        color: #aaa;
                    }}
                    ul, ol {{
                        margin: 5px 0;
                        padding-left: 20px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            self.display_text_edit.setHtml(styled_html)
        else:
            # 不支持markdown时，使用纯文本
            self.display_text_edit.setText(text)
    
    def on_response_received(self, response_text):
        # 收到响应时显示
        self.display_text = response_text
        self.waiting_label.hide()
        self.set_display_content(response_text)
        # 移动光标到末尾并插入文本
        cursor = self.display_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)       
        # 确保光标可见（滚动到底部）
        self.display_text_edit.setTextCursor(cursor)
        self.display_text_edit.ensureCursorVisible()
        self.display_text_edit.show()
        # 通知父窗口等待状态结束
        if self.parent() and hasattr(self.parent(), 'set_waiting_state'):
            self.parent().set_waiting_state(False)
            # 将内容保存到父窗口
            self.parent().saved_display_content = response_text

    def show_waiting_message(self):
        self.waiting_input_label.show()
        QTimer.singleShot(2000, self.hide_waiting_message)

    def hide_waiting_message(self):
        self.waiting_input_label.hide()
    
    def remove_disable_flag(self):
        """删除输入禁用标志文件，恢复输入功能"""
        try:
            if os.path.exists(INPUT_DISABLE_FLAG):
                os.remove(INPUT_DISABLE_FLAG)
                print("已删除输入禁用标志，恢复输入功能")
                # 隐藏等待消息标签
                if hasattr(self, 'waiting_input_label'):
                    self.waiting_input_label.hide()
        except Exception as e:
            print(f"删除输入禁用标志失败: {e}")

    def mousePressEvent(self, event):
        # 检查是否点击了窗口顶部边缘用于调整高度
        if event.button() == Qt.LeftButton and event.pos().y() <= 10:
            self.is_resizing = True
            self.resize_start_y = event.globalY()
            self.setCursor(Qt.SizeVerCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        # 处理高度调整
        if self.is_resizing:
            current_y = event.globalY()
            delta = self.resize_start_y - current_y
            new_height = self.height() + delta
            
            # 确保高度不小于最小值
            if new_height >= self.min_height:
                self.resize(self.width(), new_height)
                self.resize_start_y = current_y
                
                # 调整显示文本框的大小
                self.display_text_edit.setMinimumHeight(new_height - 40)
                
                # 更新父窗口中的位置信息
                if self.parent() and hasattr(self.parent(), 'update_display_position'):
                    self.parent().update_display_position()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 结束调整大小
        if self.is_resizing:
            self.is_resizing = False
            self.setCursor(Qt.ArrowCursor)
            # 保存高度到父窗口
            if self.parent() and hasattr(self.parent(), 'saved_display_height'):
                self.parent().saved_display_height = self.height()
        super().mouseReleaseEvent(event)
    
    def hide_display(self):
        self.hide()
        if self.parent():
            self.parent().is_display_visible = False
            # 隐藏时保存内容到父窗口
            self.parent().saved_display_content = self.display_text


class FloatXiaoHua(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_hover_effects()
        self.setup_context_menu()  # 添加右键菜单设置
        x,y =self.move_to_corner()
        self.dragging = False
        self.drag_position = QPoint()
        self.trajectory_points = []
        self.current_screen = None
        self.saved_display_content = ""  # 用于保存显示框内容的变量
        self.saved_display_height = None  # 用于保存显示框高度的变量

        #self.docer_widget = FloatDocer(self)
        #self.docer_widget.move(x, y - 56)
        self.flower_widget = FloatFlower(self)
        self.flower_widget.move(x, y + 56)
        self.house_widget = FloatHouse(self)
        self.float_workbench_widget = FloatWorkBenchWidget(self)
        self.input_widget = FloatInputWidget(self)
        self.display_widget = FloatDisplayWidget(self)
        self.float_send_button_widget = FloatSendButton(self)
        self.float_model_combo_widget = FloatComboBox(self)
        self.float_pen_draw_widget = FloatPenDraw(self)
        self.float_voice_chat_widget = FloatVoiceChat(self)
        self.float_add_button_widget = FloatAddButton(self)
        self.float_quote_button_widget = FloatQuoteButton(self)
        self.float_at_button_widget = FloatAtButton(self)

        self.is_workbench_visible = False
        self.is_house_visible = False
        self.is_input_visible = False
        self.is_display_visible = False
        self.is_float_send_button_visible = False
        self.is_float_model_combo_visible = False
        self.is_float_pen_draw_visible = False
        self.is_float_voice_chat_visible = False
        self.is_float_add_button_visible = False
        self.is_float_quote_button_visible = False
        self.is_float_at_button_visible = False

        self.is_hovered_on_workbench = False
        self.is_house_hovered = False
        self.is_hovered_on_input = False
        self.is_hovered_on_display = False
        self.is_hovered_on_float_send_button = False
        self.is_hovered_on_float_model_combo = False
        self.is_hovered_on_float_pen_draw = False
        self.is_hovered_on_float_voice_chat = False
        self.is_hovered_on_float_add_button = False
        self.is_hovered_on_float_quote_button = False
        self.is_hovered_on_float_at_button = False

        self.is_hovered = False
        self.last_screen_geometry = None
        self.leave_check_timer = QTimer()
        self.leave_check_timer.setSingleShot(True)
        self.leave_check_timer.timeout.connect(self.check_mouse_leave)
        self.is_waiting = False  # 等待状态标记
        self.screenshot_path = None  # 保存当前截图路径
        # 边缘隐藏相关属性
        self.is_hidden = False  # 悬浮球是否隐藏在边缘
        self.edge_margin = 10  # 边缘检测的像素范围
        self.hidden_width = 8  # 隐藏时显示的宽度，增加可见性
        self.setting_window = None  # 用于保存设置窗口的引用

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.small_size = 50
        self.large_size = 52
        self.current_size = self.small_size
        self.setGeometry(0, 0, self.small_size, self.small_size)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        # 隐藏时的透明红色背景标签 - 使用更醒目的颜色和更高的透明度
        self.edge_label = QLabel(self)
        self.edge_label.setGeometry(0, 0, 0, 0)
        self.edge_label.setStyleSheet("background-color: rgba(128, 0, 0, 180); border-radius: 2px;")
        self.edge_label.hide()
        # 为边缘标签添加鼠标跟踪
        self.edge_label.setMouseTracking(True)
        self.load_image()
        self.show()

    def load_image(self):
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio()
        #print(f"screen ratio: {ratio:.2f}")
    
        img_path = "icons/小华.png"
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.small_pixmap = self.original_pixmap.scaled(
                    int(self.small_size * ratio), int(self.small_size * ratio),
                    #self.small_size, self.small_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.small_pixmap.setDevicePixelRatio(ratio)
                self.label.setPixmap(self.small_pixmap)
                self.label.setGeometry(0, 0, self.small_size, self.small_size)
                return
        self.create_default_circle()

    def create_default_circle(self):
        size = max(self.small_size, self.large_size)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 200, 0)))
        painter.setPen(QPen(QColor(0, 255, 0), 1))
        painter.drawEllipse(0, 0, size - 1, size - 1)
        painter.end()
        self.original_pixmap = pixmap
        self.small_pixmap = self.original_pixmap.scaled(
            self.small_size, self.small_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(self.small_pixmap)
        self.label.setGeometry(0, 0, self.small_size, self.small_size)

    def setup_hover_effects(self):
        self.setMouseTracking(True)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutBack)

    def enterEvent(self, event):
        # 当鼠标进入边缘标签时恢复悬浮球
        if self.is_hidden:
            self.restore_from_edge()
        self.leave_check_timer.stop()
        current_screen = self.get_current_screen()
        if self.last_screen_geometry is None or self.last_screen_geometry != current_screen:
            self.last_screen_geometry = current_screen
            if self.input_widget:
                self.input_widget.hide()
            if self.display_widget:
                self.display_widget.hide()
            if self.float_send_button_widget:
                self.float_send_button_widget.hide()
            if self.float_model_combo_widget:
                self.float_model_combo_widget.hide()
            if self.float_pen_draw_widget:
                self.float_pen_draw_widget.hide()
            if self.float_voice_chat_widget:
                self.float_voice_chat_widget.hide()
            if self.float_add_button_widget:
                self.float_add_button_widget.hide()
            if self.float_quote_button_widget:
                self.float_quote_button_widget.hide()
            if self.float_at_button_widget:
                self.float_at_button_widget.hide()
            if self.house_widget:
                self.house_widget.hide()
            if self.float_workbench_widget:
                self.float_workbench_widget.hide()
            
            self.house_widget = FloatHouse(self)
            self.float_workbench_widget = FloatWorkBenchWidget(self)
            self.input_widget = FloatInputWidget(self)
            self.display_widget = FloatDisplayWidget(self, self.saved_display_content)
            
            self.float_send_button_widget = FloatSendButton(self)
            self.float_model_combo_widget = FloatComboBox(self)
            self.float_pen_draw_widget = FloatPenDraw(self)
            self.float_voice_chat_widget = FloatVoiceChat(self)
            self.float_add_button_widget = FloatAddButton(self)
            self.float_quote_button_widget = FloatQuoteButton(self)
            self.float_at_button_widget = FloatAtButton(self)
            
            self.is_input_visible = False
            self.is_display_visible = False
            self.is_float_send_button_visible = False
            self.is_float_model_combo_visible = False
            self.is_float_pen_draw_visible = False
            self.is_float_voice_chat_visible = False
            self.is_float_add_button_visible = False
            self.is_float_quote_button_visible = False
            self.is_float_at_button_visible = False
            self.is_house_visible = False
            self.is_workbench_visible = False
            
            self.is_hovered_on_input = False
            self.is_hovered_on_display = False
            self.is_hovered_on_float_send_button = False
            self.is_hovered_on_float_model_combo = False
            self.is_hovered_on_float_pen_draw = False
            self.is_hovered_on_float_voice_chat = False
            self.is_hovered_on_float_add_button = False
            self.is_hovered_on_float_quote_button = False
            self.is_hovered_on_float_at_button = False
            self.is_hovered_on_house = False
            self.is_hovered_on_workbench = False
        if not self.is_hovered:
            self.is_hovered = True
            self.animate_to_large()
            self.show_workebench()

    def leaveEvent(self, event):
        # 只有在非隐藏状态下才启动离开检查
        if not self.is_hidden:
            self.leave_check_timer.start(50)

    def check_mouse_leave(self):
        # 检查鼠标是否离开所有相关组件
        if not self.underMouse() and \
                not (self.input_widget and self.input_widget.underMouse()) and \
                not (self.display_widget and self.display_widget.underMouse()) and \
                not (self.float_workbench_widget and self.float_workbench_widget.underMouse()):
            
            self.is_hovered = False
            self.animate_to_small()
            
            # 只有当输入框和输入行都没有焦点时才隐藏
            if self.input_widget and not self.input_widget.hasFocus() and not self.input_widget.input_line.hasFocus() and not self.float_workbench_widget.hasFocus():
                # 隐藏前保存显示内容
                if self.display_widget:
                    self.saved_display_content = self.display_widget.display_text
                                
                # 隐藏输入框和显示框
                self.input_widget.hide()
                self.display_widget.hide()
                self.float_send_button_widget.hide()
                self.float_model_combo_widget.hide()
                self.float_pen_draw_widget.hide()
                self.float_voice_chat_widget.hide()
                self.float_add_button_widget.hide()
                self.float_quote_button_widget.hide()
                self.float_at_button_widget.hide()
                self.house_widget.hide()
                self.float_workbench_widget.hide()

                # 更新状态变量
                self.is_input_visible = False
                self.is_display_visible = False
                self.is_float_send_button_visible = False
                self.is_float_model_combo_visible = False
                self.is_float_pen_draw_visible = False
                self.is_float_voice_chat_visible = False
                self.is_float_add_button_visible = False
                self.is_float_quote_button_visible = False
                self.is_float_at_button_visible = False
                self.is_house_visible = False
                self.is_workbench_visible = False
                
                self.is_hovered_on_input = False
                self.is_hovered_on_display = False
                self.is_hovered_on_float_send_button = False
                self.is_hovered_on_float_model_combo = False
                self.is_hovered_on_float_pen_draw = False
                self.is_hovered_on_float_voice_chat = False
                self.is_hovered_on_float_add_button = False
                self.is_hovered_on_float_quote_button = False
                self.is_hovered_on_float_at_button = False
                self.is_hovered_on_house = False
                self.is_hovered_on_workbench = False
                
                # 检查是否需要隐藏到边缘
                self.check_and_hide_to_edge()

    def on_input_hover_enter(self):
        self.leave_check_timer.stop()
        self.is_hovered_on_input = True
        self.is_hovered = True
        
        # 如果处于隐藏状态，恢复正常显示后再处理悬停逻辑
        if self.is_hidden:
            self.restore_from_edge()

    def on_input_hover_leave(self):
        self.leave_check_timer.start(50)

    def update_display_position(self):
        """更新显示框位置，当显示框高度改变时调用"""
        if not self.is_input_visible:
            return
            
        # 获取当前屏幕信息
        current_screen = self.get_current_screen()
        
        # 获取各组件尺寸
        ball_pos = self.pos()
        ball_width = self.width()
        ball_height = self.height()
        scaled_input_width = self.input_widget.width()
        scaled_input_height = self.input_widget.height()
        scaled_display_width = self.display_widget.width()
        scaled_display_height = self.display_widget.height()
        
        # 重新计算位置
        input_x = self.input_widget.x()
        input_y = self.input_widget.y()
        
        # 显示框底部 = 输入框顶部（无空隙）
        display_x = input_x
        display_y = input_y - scaled_display_height
        
        # 边界检查（确保在屏幕内）
        if display_y < current_screen.y():
            offset = current_screen.y() - display_y
            display_y += offset
            input_y += offset
        if input_y + scaled_input_height > current_screen.y() + current_screen.height():
            offset = (input_y + scaled_input_height) - (current_screen.y() + current_screen.height()) + 5
            input_y -= offset
            display_y -= offset
        
        # 更新位置
        self.input_widget.move(input_x, input_y)
        self.display_widget.move(display_x, display_y)
    
    def show_workebench(self):
        if not self.is_input_visible:
            # 获取悬浮球基础信息
            ball_pos = self.pos()
            ball_width = self.width()
            ball_height = self.height()
            current_screen = self.get_current_screen()
            self.last_screen_geometry = current_screen

            # 重新初始化输入框和显示框时传入保存的内容
            if hasattr(self, 'input_widget') and self.input_widget:
                self.input_widget.hide()
            if hasattr(self, 'display_widget') and self.display_widget:
                self.display_widget.hide()
            if hasattr(self, 'float_send_button_widget') and self.float_send_button_widget:
                self.float_send_button_widget.hide()
            if hasattr(self, 'float_model_combo_widget') and self.float_model_combo_widget:
                self.float_model_combo_widget.hide()
            if hasattr(self, 'float_pen_draw_widget') and self.float_pen_draw_widget:
                self.float_pen_draw_widget.hide()
            if hasattr(self, 'float_voice_chat_widget') and self.float_voice_chat_widget:
                self.float_voice_chat_widget.hide()
            if hasattr(self, 'float_add_button_widget') and self.float_add_button_widget:
                self.float_add_button_widget.hide()
            if hasattr(self, 'float_quote_button_widget') and self.float_quote_button_widget:
                self.float_quote_button_widget.hide()
            if hasattr(self, 'float_at_button_widget') and self.float_at_button_widget:
                self.float_at_button_widget.hide()
            if hasattr(self, 'house_widget') and self.house_widget:
                self.house_widget.hide()
            if hasattr(self, 'float_workbench_widget') and self.float_workbench_widget:
                self.float_workbench_widget.hide()
                
            self.input_widget = FloatInputWidget(self)
            self.display_widget = FloatDisplayWidget(self, self.saved_display_content)
            self.float_send_button_widget = FloatSendButton(self)
            self.float_model_combo_widget = FloatComboBox(self)
            self.float_pen_draw_widget = FloatPenDraw(self)
            self.float_voice_chat_widget = FloatVoiceChat(self)
            self.float_add_button_widget = FloatAddButton(self)
            self.float_quote_button_widget = FloatQuoteButton(self)
            self.float_at_button_widget = FloatAtButton(self)
            self.house_widget = FloatHouse(self)
            self.float_workbench_widget = FloatWorkBenchWidget(self)
            #self.docer_widget = FloatDocer(self)
            
            # 应用保存的显示框高度
            if self.saved_display_height and self.saved_display_height >= self.display_widget.min_height:
                self.display_widget.resize(self.display_widget.width(), self.saved_display_height)
                self.display_widget.display_text_edit.setMinimumHeight(self.saved_display_height - 40)

            # 获取缩放后的尺寸
            scaled_input_width = self.input_widget.width()
            scaled_input_height = self.input_widget.height()
            scaled_display_width = self.display_widget.width()
            scaled_display_height = self.display_widget.height()

            # 计算输入框位置
            input_x = ball_pos.x() - scaled_input_width - 5
            input_y = ball_pos.y() + (ball_height - scaled_input_height) // 2
            if input_x < current_screen.x():
                input_x = ball_pos.x() + ball_width + 5

            # 显示框底部 = 输入框顶部（无空隙）
            display_x = input_x
            display_y = input_y - scaled_display_height

            # 边界检查（确保在屏幕内）
            if display_y < current_screen.y():
                offset = current_screen.y() - display_y
                display_y += offset
                input_y += offset
            if input_y + scaled_input_height > current_screen.y() + current_screen.height():
                offset = (input_y + scaled_input_height) - (current_screen.y() + current_screen.height()) + 5
                input_y -= offset
                display_y -= offset

            #print(f"scaled_input_width: {scaled_input_width}")
            #print(f"send button width: {self.float_send_button_widget.width()}")
            self.flower_widget.move(ball_pos.x(), ball_pos.y() + 56)
            #self.docer_widget.move(ball_pos.x(), ball_pos.y() - 56)
                        
            # 显示组件
            #self.house_widget.move(display_x - 110, display_y - 50)
            #self.float_workbench_widget.move(display_x, display_y - self.float_workbench_widget.height())
            #self.float_workbench_widget.move(display_x, display_y - 105)
            
            #self.float_workbench_widget.move(display_x, display_y - 160)
            
            #self.docer_widget.move(display_x, display_y - 105)
            #self.docer_widget.raise_()
            workbench_scaled_width, workbench_scaled_height = self.float_workbench_widget.get_scaled_size(280, 500)
            #workbench_x = input_x - 180
            #workbench_x = 50
            workbench_x = input_x
            workbench_y = 50  # ball_pos.y() - workbench_scaled_height
            self.float_workbench_widget.move(workbench_x, workbench_y)

            self.input_widget.move(input_x, input_y)
            self.display_widget.move(display_x, display_y)
            self.float_send_button_widget.move(input_x + scaled_input_width - 32, input_y + scaled_input_height + 65)
            self.float_pen_draw_widget.move(input_x + scaled_input_width - 64, input_y + scaled_input_height + 65)
            self.float_voice_chat_widget.move(input_x + scaled_input_width - 96, input_y + scaled_input_height + 65)
            self.float_add_button_widget.move(input_x + scaled_input_width - 96, input_y + scaled_input_height + 65)
            self.float_quote_button_widget.move(input_x + scaled_input_width - 128, input_y + scaled_input_height + 65)
            self.float_at_button_widget.move(input_x + scaled_input_width - 160, input_y + scaled_input_height + 65)
            self.float_model_combo_widget.move(input_x + 5, input_y + scaled_input_height + 65)
            
            #self.display_widget.show()
            #self.input_widget.show()

            #self.float_send_button_widget.show()
            #self.float_model_combo_widget.show()
            #self.float_pen_draw_widget.show()
            #self.float_voice_chat_widget.show()
            ##self.float_add_button_widget.show()
            #self.float_quote_button_widget.show()
            #self.float_at_button_widget.show()
            ##self.house_widget.show()
            
            self.float_workbench_widget.show()

            self.is_input_visible = True
            self.is_display_visible = True
            self.is_send_button_visible = True
            self.is_model_combo_visible = True
            self.is_pen_draw_visible = True
            self.is_voice_chat_visible = True
            #self.is_add_button_visible = True
            self.is_quote_button_visible = True
            self.is_at_button_visible = True
            #self.is_house_visible = True
            
    def show_work_widget(self):
        self.show_workebench()

    def animate_to_large(self):
        current_pos = self.pos()
        current_center_x = current_pos.x() + self.small_size // 2
        current_center_y = current_pos.y() + self.small_size // 2
        new_size = self.large_size
        new_x = current_center_x - new_size // 2
        new_y = current_center_y - new_size // 2
        self.animation.setStartValue(QRect(current_pos.x(), current_pos.y(), self.small_size, self.small_size))
        self.animation.setEndValue(QRect(new_x, new_y, new_size, new_size))
        self.animation.start()
        QTimer.singleShot(0, self.update_label_size_large)

    def animate_to_small(self):
        current_pos = self.pos()
        current_center_x = current_pos.x() + self.large_size // 2
        current_center_y = current_pos.y() + self.large_size // 2
        new_size = self.small_size
        new_x = current_center_x - new_size // 2
        new_y = current_center_y - new_size // 2
        self.animation.setStartValue(QRect(current_pos.x(), current_pos.y(), self.large_size, self.large_size))
        self.animation.setEndValue(QRect(new_x, new_y, new_size, new_size))
        if self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        self.animation.start()
        QTimer.singleShot(10, self.update_label_size_small)

    def update_label_size_large(self):
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio()

        self.resize(self.large_size, self.large_size)
        scaled_pixmap = self.original_pixmap.scaled(
            #self.large_size, self.large_size,
            int(self.large_size * ratio), int(self.large_size * ratio),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        scaled_pixmap.setDevicePixelRatio(ratio)
        self.label.setPixmap(scaled_pixmap)
        self.label.setGeometry(0, 0, self.large_size, self.large_size)

    def update_label_size_small(self):
        self.resize(self.small_size, self.small_size)
        self.label.setPixmap(self.small_pixmap)
        self.label.setGeometry(0, 0, self.small_size, self.small_size)

    def move_to_corner(self):
        screen_geometry = self.get_current_screen()
        window_geometry = self.geometry()
        x = screen_geometry.width() - window_geometry.width() - 20
        y = screen_geometry.height() - (screen_geometry.height() // 3) - window_geometry.height() // 2 - 50
        self.move(x, y)
        return x,y

    def get_current_screen(self):
        desktop = QDesktopWidget()
        current_pos = self.pos()
        for i in range(desktop.screenCount()):
            screen_geometry = desktop.screenGeometry(i)
            if screen_geometry.contains(current_pos):
                return screen_geometry
        return desktop.screenGeometry()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 拖动时立即退出隐藏状态
            if self.is_hidden:
                self.restore_from_edge()
                
            self.dragging = True
            self.drag_position = event.globalPos() - self.pos()
            if self.animation.state() == QPropertyAnimation.Running:
                self.animation.stop()
                if self.is_hovered:
                    self.update_label_size_large()
                else:
                    self.update_label_size_small()
            
            self.current_screen = self.get_current_screen()
            
            # 拖动前保存显示内容
            if self.display_widget:
                self.saved_display_content = self.display_widget.display_text

            if self.input_widget:
                self.input_widget.hide()
                self.is_input_visible = False
            if self.display_widget:
                self.display_widget.hide()
                self.is_display_visible = False
            if self.float_send_button_widget:
                self.float_send_button_widget.hide()
                self.is_float_send_button_visible = False
            if self.float_model_combo_widget:
                self.float_model_combo_widget.hide()
                self.is_model_combo_visible = False
            if self.float_pen_draw_widget:
                self.float_pen_draw_widget.hide()
                self.is_pen_draw_visible = False
            if self.float_voice_chat_widget:
                self.float_voice_chat_widget.hide()
                self.is_voice_chat_visible = False
            if self.float_add_button_widget:
                self.float_add_button_widget.hide()
                self.is_add_button_visible = False
            if self.float_quote_button_widget:
                self.float_quote_button_widget.hide()
                self.is_quote_button_visible = False
            if self.float_at_button_widget:
                self.float_at_button_widget.hide()
                self.is_at_button_visible = False
            if self.house_widget:
                self.house_widget.hide()
                self.is_house_visible = False
            if self.float_workbench_widget:
                self.float_workbench_widget.hide()
                self.is_workbench_visible = False
            
            self.is_hovered_on_input = False
            self.is_hovered_on_display = False
            self.is_hovered_on_float_send_button = False
            self.is_hovered_on_pen_draw = False
            self.is_hovered_on_add_button = False
            self.is_hovered_on_quote_button = False
            self.is_hovered_on_at_button = False
            self.is_hovered_on_house = False
            self.is_hovered_on_workbench = False

            self.is_hovered = False
            self.is_waiting = False  # 拖动时重置等待状态
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            center = self.geometry().center()
            self.flower_widget.move((event.globalPos() - self.drag_position).x(), (event.globalPos() - self.drag_position).y() + 56)
            #self.docer_widget.move((event.globalPos() - self.drag_position).x(), (event.globalPos() - self.drag_position).y() - 56)
            
            current_screen = self.get_current_screen()
            if self.last_screen_geometry is None or self.last_screen_geometry != current_screen:
                self.last_screen_geometry = current_screen
                if self.is_input_visible:
                    self.input_widget.hide()
                    self.is_input_visible = False
                if self.is_display_visible:
                    self.display_widget.hide()
                    self.is_display_visible = False
                if self.is_float_send_button_visible:
                    self.float_send_button_widget.hide()
                    self.is_float_send_button_visible = False
                if self.is_model_combo_visible:
                    self.float_model_combo_widget.hide()
                    self.is_model_combo_visible = False
                if self.is_pen_draw_visible:
                    self.float_pen_draw_widget.hide()
                    self.is_pen_draw_visible = False
                if self.is_voice_chat_visible:
                    self.float_voice_chat_widget.hide()
                    self.is_voice_chat_visible = False
                if self.is_add_button_visible:
                    self.float_add_button_widget.hide()
                    self.is_add_button_visible = False
                if self.is_quote_button_visible:
                    self.float_quote_button_widget.hide()
                    self.is_quote_button_visible = False
                if self.is_at_button_visible:
                    self.float_at_button_widget.hide()
                    self.is_at_button_visible = False
                if self.is_house_visible:
                    self.house_widget.hide()
                    self.is_house_visible = False
                if self.is_workbench_visible:
                    self.float_workbench_widget.hide()
                    self.is_workbench_visible = False
                

        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            
            # 如果悬浮球处于隐藏状态，先恢复显示
            if self.is_hidden:
                self.restore_from_edge()
                
            if self.is_hovered:
                current_screen = self.get_current_screen()
                if self.last_screen_geometry is None or self.last_screen_geometry != current_screen:
                    self.last_screen_geometry = current_screen
                    if self.input_widget:
                        self.input_widget.hide()
                    if self.display_widget:
                        self.display_widget.hide()
                    if self.float_send_button_widget:
                        self.float_send_button_widget.hide()
                    
                    # 释放鼠标后重新创建显示框时传入保存的内容
                    self.input_widget = FloatInputWidget(self)
                    self.display_widget = FloatDisplayWidget(self, self.saved_display_content)
                    self.float_send_button_widget = FloatSendButton(self)
                    self.float_model_combo_widget = FloatComboBox(self)
                    self.float_pen_draw_widget = FloatPenDraw(self)
                    self.float_voice_chat_widget = FloatVoiceChat(self)
                    self.float_add_button_widget = FloatAddButton(self)
                    self.float_quote_button_widget = FloatQuoteButton(self)
                    self.float_at_button_widget = FloatAtButton(self)
                    self.house_widget = HouseWidget(self)
                    self.float_workbench_widget = FloatWorkBenchWidget(self)
                QTimer.singleShot(100, self.show_work_widget)
            else:
                # 检查是否需要隐藏到边缘
                self.check_and_hide_to_edge()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.move_to_corner()
        event.accept()

    def set_waiting_state(self, state):
        """设置等待状态"""
        self.is_waiting = state

    def setup_context_menu(self):
        """设置右键菜单"""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建菜单
        self.context_menu = QMenu(self)
        
        # 创建菜单项
        self.enter_setting_action = QAction("设置", self)
        self.red_action = QAction("红色", self)
        self.black_action = QAction("黑色", self)
        self.green_action = QAction("绿色", self)
        self.blue_action = QAction("蓝色", self)
        self.exit_action = QAction("退出", self)

        
        # 连接信号与槽
        self.enter_setting_action.triggered.connect(self.enter_setting_page)
        self.red_action.triggered.connect(self.red_style)
        self.black_action.triggered.connect(self.black_style)
        self.green_action.triggered.connect(self.green_style)
        self.blue_action.triggered.connect(self.blue_style)
        self.exit_action.triggered.connect(self.exit_application)
        
        # 添加菜单项到菜单
        self.context_menu.addAction(self.enter_setting_action)
        self.context_menu.addAction(self.red_action)
        self.context_menu.addAction(self.black_action)
        self.context_menu.addAction(self.green_action)
        self.context_menu.addAction(self.blue_action)
        self.context_menu.addAction(self.exit_action)
        
        self.setStyleSheet()

    def setStyleSheet(self):
        # 设置菜单项样式
        self.context_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {app_background_color};
                border: 1px solid white;
                border-radius: 4px;
                padding: 4px 0;
            }}
            QMenu::item {{
                padding: 6px 24px;
                color: white;
                background-color: transparent;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background-color: #0078d4;
            }}
            QMenu::separator {{
                background-color: #555;
                height: 1px;
                margin: 4px 0;
            }}
        """)

    def show_context_menu(self, position):
        """显示右键菜单"""
        self.context_menu.exec_(self.mapToGlobal(position))
    
    def enter_setting_page(self):
        """进入设置页"""
        print("进入设置页")
        self.setting_window.show() 

    def red_style(self):
        """设置红色样式"""
        global app_background_color
        app_background_color = "#933"
        # 设置菜单项样式
        self.setStyleSheet()

    def black_style(self):
        """设置黑色样式"""
        global app_background_color
        app_background_color = "#111"
        # 设置菜单项样式
        self.setStyleSheet()

    def blue_style(self):
        """设置蓝色样式"""
        global app_background_color
        app_background_color = "#339"
        # 设置菜单项样式
        self.setStyleSheet()
    
    def green_style(self):
        """设置绿色样式"""
        global app_background_color
        app_background_color = "#393"
        # 设置菜单项样式
        self.setStyleSheet()

    def exit_application(self):
        """退出应用程序"""
        print("退出应用程序")
        self.close()
        
    def check_and_hide_to_edge(self):
        """检查是否需要隐藏到屏幕边缘"""
        if not self.is_hidden and not self.is_hovered:
            current_pos = self.pos()
            current_size = self.size()
            screen = self.get_current_screen()
            
            # 检查是否靠近左边缘
            if current_pos.x() <= screen.x() + self.edge_margin:
                self.hide_to_left_edge()
            # 检查是否靠近右边缘
            elif current_pos.x() + current_size.width() >= screen.x() + screen.width() - self.edge_margin:
                self.hide_to_right_edge()
    
    def hide_to_left_edge(self):
        """隐藏到左侧边缘 - 显示红色条时悬浮球完全隐藏"""
        self.is_hidden = True
        current_pos = self.pos()
        screen = self.get_current_screen()
        
        # 隐藏主标签（悬浮球）
        self.label.hide()
        self.flower_widget.hide()
        #self.docer_widget.hide()
        
        # 显示边缘标签（红色条）
        self.edge_label.setGeometry(0, 0, self.hidden_width, self.height())
        self.edge_label.show()
        self.edge_label.raise_()  # 确保红色条在最上层
        
        # 移动窗口到左侧边缘，确保红色条完全可见
        new_x = screen.x()
        self.move(new_x, current_pos.y())
    
    def hide_to_right_edge(self):
        """隐藏到右侧边缘 - 显示红色条时悬浮球完全隐藏"""
        self.is_hidden = True
        current_pos = self.pos()
        screen = self.get_current_screen()
        
        # 隐藏主标签（悬浮球）
        self.label.hide()
        self.flower_widget.hide()
        #self.docer_widget.hide()
        
        # 显示边缘标签（红色条）
        self.edge_label.setGeometry(self.width() - self.hidden_width, 0, self.hidden_width, self.height())
        self.edge_label.show()
        self.edge_label.raise_()  # 确保红色条在最上层
        
        # 移动窗口到右侧边缘，确保红色条完全可见
        new_x = screen.x() + screen.width() - self.width()
        self.move(new_x, current_pos.y())
    
    def restore_from_edge(self):
        """从边缘恢复显示 - 显示悬浮球时红色条完全隐藏"""
        self.is_hidden = False
        current_pos = self.pos()
        screen = self.get_current_screen()
        
        # 隐藏边缘标签（红色条），显示主标签（悬浮球）
        self.edge_label.hide()
        self.label.show()
        self.flower_widget.show()
        #self.docer_widget.show()
        
        # 确保窗口完全在屏幕内且位置合适
        if current_pos.x() <= screen.x() + 10:
            new_x = screen.x() + 10  # 稍微离开边缘一点
            self.move(new_x, current_pos.y())
        elif current_pos.x() + self.width() >= screen.x() + screen.width() - 10:
            new_x = screen.x() + screen.width() - self.width() - 10  # 稍微离开边缘一点
            self.move(new_x, current_pos.y())
    

    def exit_application(self): 
        try:
            sys.exit()
        finally:
            # 清理资源
            comm_manager.stop()

def ai_finished(result):
    # AI执行完成
    print('✅ AI执行完成')
    # 重置退出标志
    #xiaohua_model_do_work.should_exit = False
        
def ai_error(error):
    # AI执行出错
    print('❌ AI执行错误，可能密钥错误或欠费')
        
    # 重置退出标志
    #xiaohua_model_do_work.should_exit = False

def main_float():
    #按钮字体显示不全分辨率
    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    # 高DPI设置已在导入后创建QApplication前设置，这里不再需要
    
    # 清空JSON文件
    try:
        # 确保数据目录存在
        if not os.path.exists("data"):
            os.makedirs("data")
        # 清空输入文件
        with open(INPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False)
        # 清空输出文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False)
        print("JSON文件已清空")
    except Exception as e:
        print(f"清空JSON文件时出错: {e}")

    font = app.font()
    font.setPointSize(9)
    app.setFont(font)
    # 启动通信管理器
    comm_manager.start()
    floating_ball = FloatXiaoHua()
    
    floating_ball.setting_window = XiaohuaSettingWidget()
    #floating_ball.setting_window.show() 

    # 创建并启动AI线程
    ai_thread = xiaohua_work_thread()
    print("xiaohua start work!!!")
    ai_thread.finished.connect(ai_finished)
    ai_thread.error.connect(ai_error)
    ai_thread.start()

    try:
        sys.exit(app.exec_())
    finally:
        # 清理资源
        comm_manager.stop()


if __name__ == "__main__":
    main_float()
    