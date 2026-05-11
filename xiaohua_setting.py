import sys
import time
import ctypes
import os
import json
import platform
import re
import string

# 仅在开发环境中设置Qt平台插件路径，打包时自动处理
if os.path.exists('venv/Lib/site-packages'):
    sys.path.append('venv/Lib/site-packages')

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTextEdit, QPushButton, QLabel, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QFont, QCursor

# Windows API常量
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOOLWINDOW = 0x00000080  # 工具窗口样式，不会在任务栏显示，也不会被Alt+Tab切换到

# 新增：SetWindowDisplayAffinity 常量，用于防止窗口被截图
WDA_EXCLUDEFROMCAPTURE = 0x00000011

# 定义AI坐标监测常量
AI_COORDINATE_THRESHOLD = 500  # AI输出坐标与窗口的安全距离
WINDOW_MOVE_DISTANCE = 600  # 窗口移动距离，超过500像素

# 导入AI控制相关函数
import xiaohua_model_do_work
from xiaohua_model_do_work import xiaohua_control_computer, set_coordinate_callback


# 用于进程间通信的文件路径
INPUT_FILE = "data/input_message.json"
OUTPUT_FILE = "data/output_message.json"

def fresh_display_info(content):
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    old_content = data.get('content', '')
    
    new_content = old_content + "\n" + content
    response_data = {
        'request_id': str(time.time()),
        'content': new_content,
        'timestamp': time.time()
        }
                        
    # 写入输出文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False)

# 创建一个工作线程来运行AI控制逻辑
class xiaohua_work_thread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    ai_coordinate = pyqtSignal(float, float)  # 发送AI输出的坐标信号，使用浮点数类型
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_content = ""
        
    def run(self):
        while True:
            try:
                with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # fresh_display_info(content) 
                    # print(f"[调试] 读取到的原始内容: {content}")
                    if content:
                        try:
                            input_data = json.loads(content)
                            self.user_content = input_data.get('content', '')
                            #print(f"[调试] 成功解析JSON: {self.user_content}")
                            #self.user_content = self.user_content.lstrip("工作任务：")

                            #print(f"去掉前缀: {self.user_content}")
                        except json.JSONDecodeError as e:
                            print(f"[调试] JSON解析错误: {e}")
                            # JSON格式错误时，使用默认错误提示
                            #default_json = '{"request_id": "1761143318.5938723", "content": "￥当前出错了，请重新输入。￥", "timestamp": 1761143318.5938723}'
                            #input_data = json.loads(default_json)
                        if self.user_content:
                            # 清空输出文件
                            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                                json.dump({}, f, ensure_ascii=False)
                            fresh_display_info(self.user_content) 
                            print(f"=============用户输入内容为:{self.user_content}")
                            # 设置坐标回调函数
                            def coordinate_callback(coords):
                                # 将坐标发送给主线程
                                self.ai_coordinate.emit(coords[0], coords[1])
                            
                            set_coordinate_callback(coordinate_callback)
                        
                            self.user_content = self.user_content.lstrip("工作任务：")
                            # 获取时间字符串，年月日时分
                            time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime())
                            # 用户输入内容添加时间
                            user_content2 = "当前时间为:"+time_str + "\n" + "用户任务为:"+self.user_content
                            print(f"=============用户输入内容为:{user_content2}")
                            result = xiaohua_control_computer(user_content2)
                            self.finished.emit(result)
                            with open(INPUT_FILE, 'w', encoding='utf-8') as f:
                                json.dump({}, f, ensure_ascii=False)
                            print("xiaohua work thread finished!")
                            fresh_display_info("小华已完成任务，请验收!")
                            
            except Exception as e:
                print("xiaohua work thread error!")
                fresh_display_info("抱歉，小华出错了!小华需要继续提高工作能力，敬请期待！")
                self.error.emit(str(e))
                with open(INPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False)

class XiaohuaSettingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.ai_thread = None
        self.is_ai_controlling = False  # 标记是否由AI控制鼠标
        self.mouse_monitor_timer = None  # 鼠标监测定时器
        self.initUI()
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('小华')
        self.setGeometry(300, 250, 220, 120)
        
        # 设置窗口标志：
        # - Qt.WindowStaysOnTopHint: 窗口始终在最顶层
        # - Qt.Window: 标准窗口样式
        # - Qt.WindowCloseButtonHint: 显示关闭按钮
        # - Qt.WindowMinimizeButtonHint: 显示最小化按钮
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window | 
                          Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        # 设置窗口透明度，使其更加隐蔽
        self.setWindowOpacity(0.9)
        
        # 显示窗口
        #self.show()
        
        # 获取当前操作系统
        current_os = platform.system()
        
        if current_os == "Windows":
            # 获取窗口句柄
            hwnd = self.winId().__int__()
            
            # 使用Windows API设置窗口为分层窗口
            user32 = ctypes.windll.user32
            
            # 获取当前扩展样式
            current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # 设置新的扩展样式：添加WS_EX_LAYERED
            new_style = current_style | WS_EX_LAYERED
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
            
            # 设置窗口为透明，但允许鼠标事件
            user32.SetLayeredWindowAttributes(hwnd, 0, int(255 * 0.9), 0x00000001)
            
            # 新增：使用SetWindowDisplayAffinity使窗口不被CV2等截图工具捕捉
            # 这是Windows 10版本1803及以上支持的功能
            try:
                # user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                print("窗口已设置为不可被截图")
                print("窗口已设置为可以截图")
            except Exception as e:
                print(f"设置窗口不可被截图时出错: {e}")
        else:
            print(f"{current_os}系统：使用默认窗口设置")
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)  # 设置组件间距
        main_layout.setContentsMargins(15, 10, 15, 10)  # 设置边距
        
        # 创建标题标签 - 酱红色主题
        title_label = QLabel('小华')
        title_font = QFont('Microsoft YaHei', 16, QFont.Bold)  # 使用微软雅黑，稍大但不过大
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                padding: 8px;
                margin-bottom: 8px;
                background-color: #800000;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #bbdefb;
            }
        """)
        main_layout.addWidget(title_label)
        
        # API密钥设置区域
        api_layout = QHBoxLayout()
        api_layout.setSpacing(8)
        
        # API密钥输入框 - 酱红色主题
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)  # 密码形式显示
        self.api_key_input.setPlaceholderText('请输入API密钥...')
        self.api_key_input.textChanged.connect(self.save_api_key)  # 文本变化时自动保存
        api_key_font = QFont('Microsoft YaHei', 11)  # 增大字体
        self.api_key_input.setFont(api_key_font)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #90caf9;
                border-radius: 8px;
                background-color: #f5f9ff;
                color: #1565c0;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border-color: #2196f3;
                background-color: #ffffff;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #90caf9;
            }
        """)
        api_layout.addWidget(self.api_key_input)
        
        # 获取API密钥按钮 - 红色主题
        self.get_api_key_btn = QPushButton('获取密钥')
        self.get_api_key_btn.clicked.connect(self.open_api_key_url)
        button_font = QFont('Microsoft YaHei', 10, QFont.Bold)
        self.get_api_key_btn.setFont(button_font)
        self.get_api_key_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42a5f5, stop:1 #800000);
                color: white;
                border: none;
                padding: 10px 14px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64b5f6, stop:1 #2196f3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976d2, stop:1 #0d47a1);
            }
        """)
        api_layout.addWidget(self.get_api_key_btn)
        
        main_layout.addLayout(api_layout)
       
        # 加载API密钥
        self.load_api_key()
        
        # 设置布局
        self.setLayout(main_layout)
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 设置窗口整体样式 - 酱红色背景
        self.setStyleSheet("""
            QWidget {
                background-color: #800000;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fdff, stop:1 #e6f7ff);
            }
        """)
        
    def open_api_key_url(self):
        """
        打开API密钥获取页面
        """
        import webbrowser
        webbrowser.open('https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey')
    
    def load_api_key(self):
        """
        从config.json加载API密钥
        """
        try:
            # 获取config.json的完整路径
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            print(f"尝试加载配置文件: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('api_config', {}).get('api_key', '')
            self.api_key_input.setText(api_key)
        except Exception as e:
            print(f"加载API密钥失败: {e}")
            print(f"错误路径: {config_path if 'config_path' in locals() else '未知'}")
    
    def save_api_key(self, text):
        """
        保存API密钥到config.json
        """
        try:
            # 获取config.json的完整路径
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            print(f"尝试保存配置文件: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新API密钥
            if 'api_config' not in config:
                config['api_config'] = {}
            config['api_config']['api_key'] = text
            
            # 保存到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            print(f"保存API密钥失败: {e}")
            print(f"错误路径: {config_path if 'config_path' in locals() else '未知'}")

    def closeEvent(self, event):
        # 关闭窗口时停止AI
        event.ignore()
        self.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 创建并显示AI主窗口
    window = XiaohuaSettingWidget()

    sys.exit(app.exec_())

    # 打包命令： pyinstaller xiaohua_main.spec