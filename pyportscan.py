import socket
import threading
from queue import Queue
import time
from datetime import datetime
import os
import tempfile
import shutil
import zipfile
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
import io

# 资源管理类
class ResourceManager:
    def __init__(self):
        self.temp_dir = None
        self.font_path = None
        self.bg_image_path = None
        self.zip_file = "DATA.dat"
        self.zip_password = "114514"
        self.resource_extracted = False
        
    def extract_resources(self):
        """从加密ZIP文件中提取资源到临时文件夹"""
        try:
            # 检查ZIP文件是否存在
            if not os.path.exists(self.zip_file):
                raise FileNotFoundError(f"资源文件 {self.zip_file} 不存在")
            
            # 创建唯一的临时文件夹
            self.temp_dir = tempfile.mkdtemp(prefix="PyPortScan_")
            
            # 打开并解压ZIP文件
            with zipfile.ZipFile(self.zip_file, 'r') as zf:
                # 检查ZIP文件是否需要密码
                for info in zf.infolist():
                    if info.flag_bits & 0x1:  # 如果文件被加密
                        # 尝试使用密码解压
                        try:
                            zf.extract(info, self.temp_dir, pwd=self.zip_password.encode('utf-8'))
                        except RuntimeError:
                            raise ValueError("ZIP文件密码错误")
                    else:
                        # 直接解压未加密文件
                        zf.extract(info, self.temp_dir)
            
            # 获取资源路径
            self.font_path = os.path.join(self.temp_dir, "MapleMono-NF-CN-Light.ttf")
            self.bg_image_path = os.path.join(self.temp_dir, "bgp.png")
            
            # 检查必要资源是否存在
            if not os.path.exists(self.font_path):
                raise FileNotFoundError(f"字体文件 MapleMono-NF-CN-Light.ttf 未在 {self.zip_file} 中找到")
            if not os.path.exists(self.bg_image_path):
                raise FileNotFoundError(f"背景图片 bgp.png 未在 {self.zip_file} 中找到")
            
            self.resource_extracted = True
            return True
            
        except Exception as e:
            print(f"资源提取失败: {e}")
            self.cleanup()
            raise
    
    def cleanup(self):
        """清理临时文件夹"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                self.font_path = None
                self.bg_image_path = None
                self.resource_extracted = False
            except Exception as e:
                print(f"清理临时文件失败: {e}")

# 启动时清理残留的临时文件夹
def cleanup_old_temp_folders():
    """清理之前可能残留的临时文件夹"""
    try:
        import tempfile
        import shutil
        import glob
        
        # 获取临时文件夹路径
        temp_dir = tempfile.gettempdir()
        # 查找所有PyPortScan_开头的临时文件夹
        temp_folders = glob.glob(os.path.join(temp_dir, "PyPortScan_*"))
        
        for folder in temp_folders:
            try:
                shutil.rmtree(folder)
                print(f"已清理残留的临时文件夹: {folder}")
            except Exception as e:
                print(f"清理残留临时文件夹 {folder} 失败: {e}")
    except Exception as e:
        print(f"检查残留临时文件夹时发生错误: {e}")

# 全局样式将在LoadingApp中设置

class PortScannerGUI(App):
    def __init__(self, **kwargs):
        super(PortScannerGUI, self).__init__(**kwargs)
        self._is_dragging = False
        self._mouse_pos_x = 0
        self._mouse_pos_y = 0
        self._window_pos_x = 0
        self._window_pos_y = 0
        
        # 设置主程序窗口默认尺寸
        self.default_window_width = 900
        self.default_window_height = 700
    
    def on_start(self):
        """应用启动时设置窗口属性，确保在Window完全初始化后进行"""
        # 使用Clock.schedule_once延迟设置窗口属性，确保Window已经完全创建
        Clock.schedule_once(self.set_window_properties, 0.1)
    
    def set_window_properties(self, dt):
        """设置窗口属性"""
        # 导入Windows API模块
        try:
            from win32api import GetSystemMetrics
            from win32gui import GetForegroundWindow, MoveWindow, SetWindowPos, GetWindowRect, GetWindowLong, SetWindowLong
            from win32con import HWND_TOP, SWP_NOSIZE, SWP_NOZORDER, SWP_SHOWWINDOW, GWL_STYLE, WS_POPUP, WS_VISIBLE, WS_SYSMENU
        except ImportError:
            print("Windows API模块导入失败，使用Kivy默认方式设置窗口属性")
            # 强制设置窗口大小
            Window.size = (self.default_window_width, self.default_window_height)
            Window.borderless = True
            Window.topmost = False
            
            # 获取屏幕尺寸
            screen_width = Window.system_size[0]
            screen_height = Window.system_size[1]
            
            # 计算居中位置
            left = int((screen_width - self.default_window_width) / 2)
            top = int((screen_height - self.default_window_height) / 2)
            
            # 强制设置窗口位置
            Window.left = left
            Window.top = top
            
            # 验证设置是否生效
            print(f"主程序窗口设置: 尺寸={Window.size}, 位置=({Window.left}, {Window.top})")
            return
        
        # 使用Windows API设置窗口属性
        print("使用Windows API设置窗口属性")
        
        # 获取当前窗口句柄
        hwnd = GetForegroundWindow()
        
        # 设置窗口为无边框样式
        # 移除标题栏和边框
        current_style = GetWindowLong(hwnd, GWL_STYLE)
        new_style = WS_POPUP | WS_VISIBLE
        SetWindowLong(hwnd, GWL_STYLE, new_style)
        print(f"已设置窗口为无边框样式")
        
        # 获取屏幕尺寸
        screen_width = GetSystemMetrics(0)  # SM_CXSCREEN
        screen_height = GetSystemMetrics(1)  # SM_CYSCREEN
        
        # 计算居中位置
        left = int((screen_width - self.default_window_width) / 2)
        top = int((screen_height - self.default_window_height) / 2)
        
        # 使用Windows API直接设置窗口位置和大小
        result = MoveWindow(hwnd, left, top, self.default_window_width, self.default_window_height, True)
        
        # 验证设置是否生效
        rect = GetWindowRect(hwnd)
        actual_width = rect[2] - rect[0]
        actual_height = rect[3] - rect[1]
        actual_left = rect[0]
        actual_top = rect[1]
        print(f"Windows API设置主程序窗口: 预期尺寸=({self.default_window_width}, {self.default_window_height}), 实际尺寸=({actual_width}, {actual_height})")
        print(f"Windows API设置主程序窗口: 预期位置=({left}, {top}), 实际位置=({actual_left}, {actual_top})")
        
    def build(self):
        # 添加全局触摸事件处理，确保拖动结束时能正确重置状态
        Window.bind(on_touch_up=self.on_touch_up_global)
        
        # 主布局改为BoxLayout，更适合垂直排列的窗口
        from kivy.graphics import Color, Rectangle, Line
        main_layout = BoxLayout(orientation='vertical', padding=0, spacing=0)
        
        # 自定义标题栏
        title_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=0)
        title_bar.background_color = (0.1, 0.1, 0.15, 1)
        
        # 标题栏拖动区域
        drag_area = BoxLayout(orientation='horizontal', spacing=5, padding=(10, 0), size_hint_x=1)
        drag_area.bind(on_touch_down=self.start_window_drag)
        drag_area.bind(on_touch_move=self.do_window_drag)
        
        # 应用标题
        app_title = Label(
            text="PyPortScan - 端口扫描工具",
            font_size=14,
            color=(0.3, 0.8, 1, 1),
            halign='left',
            valign='middle',
            font_name='CustomFont'
        )
        drag_area.add_widget(app_title)
        
        title_bar.add_widget(drag_area)
        
        # 窗口控制按钮区域
        controls_layout = BoxLayout(orientation='horizontal', spacing=0, size_hint_x=None, width=80)
        
        # 最小化按钮
        self.minimize_btn = Button(
            text="_",
            size_hint=(None, 1),
            width=40,
            background_color=(0.2, 0.2, 0.25, 1),
            color=(1, 1, 1, 1),
            font_size=18,
            font_name='CustomFont'
        )
        self.minimize_btn.bind(on_press=self.minimize_window)
        controls_layout.add_widget(self.minimize_btn)
        
        # 关闭按钮
        self.close_btn = Button(
            text="×",
            size_hint=(None, 1),
            width=40,
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            font_name='CustomFont'
        )
        self.close_btn.bind(on_press=self.close_window)
        controls_layout.add_widget(self.close_btn)
        
        title_bar.add_widget(controls_layout)
        
        # 添加标题栏到主布局
        main_layout.add_widget(title_bar)
        
        # 内容区域
        content_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # 标题
        title = Label(
            text="端口扫描工具",
            font_size=28,
            color=(0.3, 0.8, 1, 1),
            halign='center',
            size_hint_y=None,
            height=60,
            font_name='CustomFont'
        )
        content_layout.add_widget(title)
        
        # 输入区域
        input_layout = GridLayout(cols=2, spacing=10, size_hint_y=None)
        input_layout.bind(minimum_height=input_layout.setter('height'))
        
        # 目标IP/域名
        label = Label(text="目标IP/域名:", color=(0.8, 0.8, 0.8, 1), font_size=16, font_name='CustomFont', size_hint_y=None, height=50, valign='center')
        input_layout.add_widget(label)
        self.target_input = TextInput(
            text="127.0.0.1",
            multiline=False,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=16,
            padding_y=[10, 10],
            font_name='CustomFont',
            size_hint_y=None,
            height=50
        )
        input_layout.add_widget(self.target_input)
        
        # 端口范围
        label = Label(text="端口范围:", color=(0.8, 0.8, 0.8, 1), font_size=16, font_name='CustomFont', size_hint_y=None, height=50, valign='center')
        input_layout.add_widget(label)
        self.ports_input = TextInput(
            text="1-1024",
            multiline=False,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=16,
            padding_y=[10, 10],
            font_name='CustomFont',
            size_hint_y=None,
            height=50
        )
        input_layout.add_widget(self.ports_input)
        
        # 线程数
        label = Label(text="线程数:", color=(0.8, 0.8, 0.8, 1), font_size=16, font_name='CustomFont', size_hint_y=None, height=50, valign='center')
        input_layout.add_widget(label)
        self.threads_input = TextInput(
            text="100",
            multiline=False,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=16,
            padding_y=[10, 10],
            font_name='CustomFont',
            size_hint_y=None,
            height=50
        )
        input_layout.add_widget(self.threads_input)
        
        # 超时时间
        label = Label(text="超时时间(秒):", color=(0.8, 0.8, 0.8, 1), font_size=16, font_name='CustomFont', size_hint_y=None, height=50, valign='center')
        input_layout.add_widget(label)
        self.timeout_input = TextInput(
            text="1.0",
            multiline=False,
            background_color=(0.25, 0.25, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=16,
            padding_y=[10, 10],
            font_name='CustomFont',
            size_hint_y=None,
            height=50
        )
        input_layout.add_widget(self.timeout_input)
        content_layout.add_widget(input_layout)
        
        # 按钮区域
        button_layout = BoxLayout(spacing=10, size_hint_y=None, height=60)
        
        self.scan_button = Button(
            text="开始扫描",
            background_color=(0.3, 0.6, 0.9, 1),
            color=(1, 1, 1, 1),
            font_size=18,
            bold=True,
            size_hint_y=None,
            height=50,
            font_name='CustomFont'
        )
        self.scan_button.bind(on_press=self.start_scan)
        button_layout.add_widget(self.scan_button)
        
        self.clear_button = Button(
            text="清空结果",
            background_color=(0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1),
            font_size=18,
            bold=True,
            size_hint_y=None,
            height=50,
            font_name='CustomFont'
        )
        self.clear_button.bind(on_press=self.clear_results)
        button_layout.add_widget(self.clear_button)
        content_layout.add_widget(button_layout)
        
        # 进度条
        self.progress_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=80, spacing=5)
        self.progress_label = Label(
            text="准备就绪",
            color=(0.8, 0.8, 0.8, 1),
            font_size=14,
            halign='center',
            font_name='CustomFont'
        )
        self.progress_layout.add_widget(self.progress_label)
        
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=20
        )
        self.progress_layout.add_widget(self.progress_bar)
        content_layout.add_widget(self.progress_layout)
        
        # 结果显示区域 - 使用RelativeLayout实现图片背景效果
        result_area = RelativeLayout(size_hint=(1, 1))
        
        # 添加背景图片 - 正片叠底模式，保持1:1比例，贴住左下角
        bg_image = Image(
            source=resource_manager.bg_image_path,
            allow_stretch=False,
            keep_ratio=True,
            size_hint=(None, None),
            pos_hint={'x': 0, 'y': 0},  # 贴住左下角
            opacity=0.3  # 设置透明度，实现正片叠底效果
        )
        # 绑定容器大小变化，更新图片大小
        def update_image_size(instance, value):
            # 计算最大可能的1:1尺寸，不超过容器大小
            max_size = min(instance.width, instance.height)
            bg_image.size = (max_size, max_size)
        
        result_area.bind(size=update_image_size)
        result_area.add_widget(bg_image)
        
        # 结果滚动视图
        self.result_scroll = ScrollView(size_hint=(1, 1))
        self.result_label = Label(
            text="扫描结果将显示在这里...",
            color=(0.8, 0.8, 0.8, 1),
            font_size=14,
            halign='left',
            valign='top',
            text_size=(None, None),
            size_hint_y=None,
            font_name='CustomFont'
        )
        # 绑定滚动视图的宽度变化，更新标签的text_size
        def update_text_size(instance, value):
            self.result_label.text_size = (self.result_scroll.width - 40, None)
            self.result_label.texture_update()
            self.result_label.height = self.result_label.texture_size[1] + 20
        
        self.result_scroll.bind(width=update_text_size)
        self.result_scroll.add_widget(self.result_label)
        
        result_area.add_widget(self.result_scroll)
        content_layout.add_widget(result_area)
        
        # 创建一个RelativeLayout来容纳内容区域和调整大小控件
        # 这样可以确保调整大小控件显示在右下角
        content_container = RelativeLayout(size_hint=(1, 1))
        
        # 将内容布局添加到容器中
        content_container.add_widget(content_layout)
        
        # 添加调整大小控件到容器中
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, Rectangle, Line
        
        class ResizeWidget(Widget):
            def __init__(self, **kwargs):
                super(ResizeWidget, self).__init__(**kwargs)
                self.size_hint = (None, None)
                self.size = (20, 20)
                self.pos_hint = {'right': 1, 'y': 0}  # 右下角位置
                self.is_resizing = False
                self.is_hovered = False
                
                # 绘制控件外观
                with self.canvas:
                    Color(0.3, 0.8, 1, 0.7)  # 半透明蓝色
                    Rectangle(pos=self.pos, size=self.size)
                    Color(1, 1, 1, 1)  # 白色
                    Line(points=[self.x + 5, self.y + 15, self.x + 15, self.y + 5], width=2)
                    Line(points=[self.x + 15, self.y + 5, self.x + 15, self.y + 15], width=2)
                    Line(points=[self.x + 15, self.y + 15, self.x + 5, self.y + 15], width=2)
                
                # 绑定鼠标位置事件
                from kivy.core.window import Window
                Window.bind(mouse_pos=self.on_mouse_pos)
            
            def on_pos(self, *args):
                # 更新绘制
                self.canvas.clear()
                with self.canvas:
                    Color(0.3, 0.8, 1, 0.7)
                    Rectangle(pos=self.pos, size=self.size)
                    Color(1, 1, 1, 1)
                    Line(points=[self.x + 5, self.y + 15, self.x + 15, self.y + 5], width=2)
                    Line(points=[self.x + 15, self.y + 5, self.x + 15, self.y + 15], width=2)
                    Line(points=[self.x + 15, self.y + 15, self.x + 5, self.y + 15], width=2)
            
            def on_mouse_pos(self, window, pos):
                # 检测鼠标是否悬停在控件上
                if self.collide_point(*pos):
                    if not self.is_hovered:
                        self.is_hovered = True
                        # 显示调整大小指针
                        from kivy.core.window import Window
                        Window.set_system_cursor('se-resize')
                        # 添加悬停效果
                        self.canvas.clear()
                        with self.canvas:
                            Color(0.4, 0.9, 1, 0.9)  # 更亮的蓝色
                            Rectangle(pos=self.pos, size=self.size)
                            Color(1, 1, 1, 1)
                            Line(points=[self.x + 5, self.y + 15, self.x + 15, self.y + 5], width=2)
                            Line(points=[self.x + 15, self.y + 5, self.x + 15, self.y + 15], width=2)
                            Line(points=[self.x + 15, self.y + 15, self.x + 5, self.y + 15], width=2)
                else:
                    if self.is_hovered:
                        self.is_hovered = False
                        # 恢复默认指针
                        from kivy.core.window import Window
                        Window.set_system_cursor('arrow')
                        # 恢复正常外观
                        self.canvas.clear()
                        with self.canvas:
                            Color(0.3, 0.8, 1, 0.7)
                            Rectangle(pos=self.pos, size=self.size)
                            Color(1, 1, 1, 1)
                            Line(points=[self.x + 5, self.y + 15, self.x + 15, self.y + 5], width=2)
                            Line(points=[self.x + 15, self.y + 5, self.x + 15, self.y + 15], width=2)
                            Line(points=[self.x + 15, self.y + 15, self.x + 5, self.y + 15], width=2)
        
        # 添加调整大小控件到内容容器
        self.resize_widget = ResizeWidget()
        content_container.add_widget(self.resize_widget)
        
        # 将内容容器添加到主布局
        main_layout.add_widget(content_container)
        
        # 初始化扫描变量
        self.is_scanning = False
        self.open_ports = []
        self.total_ports = 0
        self.scanned_ports = 0
        self.result_text = ""
        
        # 初始化调整大小相关变量
        self.is_resizing = False
        self._start_resize_x = 0
        self._start_resize_y = 0
        self._start_window_width = 0
        self._start_window_height = 0
        # 视觉反馈相关
        self.resize_feedback = None
        
        # 绑定调整大小事件
        self.resize_widget.bind(on_touch_down=self.start_resize)
        self.resize_widget.bind(on_touch_move=self.do_resize)
        self.resize_widget.bind(on_touch_up=self.stop_resize)
        
        return main_layout
    
    def start_window_drag(self, instance, touch):
        """开始拖动窗口"""
        if touch.x < instance.width:
            self._is_dragging = True
            # 使用Windows API直接拖动窗口，完全绕过Kivy的坐标系统
            from win32api import GetCursorPos
            from win32gui import GetWindowRect, GetForegroundWindow
            
            # 获取当前窗口句柄
            self._window_handle = GetForegroundWindow()
            # 获取初始鼠标位置
            self._start_mouse_x, self._start_mouse_y = GetCursorPos()
            # 获取窗口初始位置
            window_rect = GetWindowRect(self._window_handle)
            self._start_window_left = window_rect[0]
            self._start_window_top = window_rect[1]
    
    def do_window_drag(self, instance, touch):
        """执行窗口拖动"""
        if self._is_dragging:
            # 使用Windows API直接移动窗口
            from win32api import GetCursorPos
            from win32gui import MoveWindow
            
            # 获取当前鼠标位置
            current_mouse_x, current_mouse_y = GetCursorPos()
            
            # 计算鼠标移动距离
            delta_x = current_mouse_x - self._start_mouse_x
            delta_y = current_mouse_y - self._start_mouse_y
            
            # 计算窗口新位置
            new_left = self._start_window_left + delta_x
            new_top = self._start_window_top + delta_y
            
            # 获取窗口大小
            from win32gui import GetWindowRect
            window_rect = GetWindowRect(self._window_handle)
            window_width = window_rect[2] - window_rect[0]
            window_height = window_rect[3] - window_rect[1]
            
            # 使用Windows API直接移动窗口，完全绕过Kivy的坐标系统
            # 这样可以确保精确的1:1比例
            MoveWindow(self._window_handle, new_left, new_top, window_width, window_height, True)
    
    def on_touch_up_global(self, window, touch):
        """全局触摸释放事件，确保拖动状态被正确重置"""
        self._is_dragging = False
        self.is_resizing = False
    
    def start_resize(self, instance, touch):
        """开始调整窗口大小"""
        if instance.collide_point(*touch.pos):
            self.is_resizing = True
            # 使用Windows API记录初始状态
            from win32api import GetCursorPos
            self._start_resize_x, self._start_resize_y = GetCursorPos()
            
            # 获取当前窗口句柄和大小
            from win32gui import GetForegroundWindow, GetWindowRect
            self._resize_window_handle = GetForegroundWindow()
            window_rect = GetWindowRect(self._resize_window_handle)
            self._start_window_width = window_rect[2] - window_rect[0]
            self._start_window_height = window_rect[3] - window_rect[1]
            return True
        return False
    
    def do_resize(self, instance, touch):
        """执行窗口大小调整"""
        if self.is_resizing:
            # 使用Windows API获取当前鼠标位置
            from win32api import GetCursorPos
            current_mouse_x, current_mouse_y = GetCursorPos()
            
            # 计算鼠标移动距离
            delta_x = current_mouse_x - self._start_resize_x
            delta_y = current_mouse_y - self._start_resize_y  # 修正y轴方向，与x轴保持一致
            
            # 计算新窗口大小
            new_width = self._start_window_width + delta_x
            # y轴方向需要调整，因为Windows坐标系y轴向下为正
            new_height = self._start_window_height + delta_y
            
            # 添加边界限制
            min_width = 300
            min_height = 200
            new_width = max(new_width, min_width)
            new_height = max(new_height, min_height)
            
            # 使用Windows API调整窗口大小
            from win32gui import GetWindowRect, MoveWindow
            window_rect = GetWindowRect(self._resize_window_handle)
            # 保持窗口左上角位置不变，只调整大小
            MoveWindow(self._resize_window_handle, window_rect[0], window_rect[1], new_width, new_height, True)
            return True
        return False
    
    def stop_resize(self, instance, touch):
        """停止调整窗口大小"""
        self.is_resizing = False
        return True
    
    def minimize_window(self, instance):
        """最小化窗口"""
        Window.minimize()
    
    def close_window(self, instance):
        """关闭窗口"""
        self.stop()
    
    def get_ip(self, hostname):
        """将域名转换为IP地址"""
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except socket.gaierror:
            self.show_error(f"无法解析域名: {hostname}")
            return None
    
    def parse_port_range(self, port_range_str):
        """解析端口范围字符串"""
        ports = set()
        parts = port_range_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    if start > end:
                        start, end = end, start
                    ports.update(range(start, end + 1))
                except ValueError:
                    self.show_error(f"无效的端口范围: {part}")
                    return None
            else:
                try:
                    port = int(part)
                    ports.add(port)
                except ValueError:
                    self.show_error(f"无效的端口: {part}")
                    return None
        
        return sorted(ports)
    
    def scan_port(self, target, port, timeout):
        """扫描单个端口"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((target, port))
                if result == 0:
                    try:
                        service = socket.getservbyport(port, 'tcp')
                    except:
                        service = "未知服务"
                    self.open_ports.append((port, service))
        except Exception as e:
            pass
        finally:
            self.scanned_ports += 1
            # 更新进度，避免除以零
            if self.total_ports > 0:
                progress = (self.scanned_ports / self.total_ports) * 100
                Clock.schedule_once(lambda dt: self.update_progress(progress), 0)
    
    def worker(self, queue, target, timeout):
        """线程工作函数"""
        while not queue.empty() and self.is_scanning:
            port = queue.get()
            self.scan_port(target, port, timeout)
            queue.task_done()
    
    def start_scan(self, instance):
        """开始扫描"""
        if self.is_scanning:
            return
        
        # 获取输入值
        target = self.target_input.text.strip()
        port_range = self.ports_input.text.strip()
        
        try:
            threads = int(self.threads_input.text.strip())
            if threads <= 0:
                raise ValueError("线程数必须大于0")
        except ValueError as e:
            self.show_error(f"无效的线程数: {e}")
            return
        
        try:
            timeout = float(self.timeout_input.text.strip())
            if timeout <= 0:
                raise ValueError("超时时间必须大于0")
        except ValueError as e:
            self.show_error(f"无效的超时时间: {e}")
            return
        
        if not target:
            self.show_error("请输入目标IP或域名")
            return
        
        if not port_range:
            self.show_error("请输入端口范围")
            return
        
        # 清空之前的结果
        self.clear_results(None)
        
        # 将域名转换为IP
        if target.replace('.', '').isdigit():
            target_ip = target
        else:
            target_ip = self.get_ip(target)
            if not target_ip:
                return
        
        # 解析端口范围
        ports = self.parse_port_range(port_range)
        if not ports:
            return
        
        self.total_ports = len(ports)
        self.scanned_ports = 0
        self.open_ports = []
        self.is_scanning = True
        
        # 禁用扫描按钮
        self.scan_button.disabled = True
        self.scan_button.background_color = (0.2, 0.2, 0.2, 1)
        
        # 设置进度条
        self.progress_bar.max = 100
        self.progress_bar.value = 0
        self.progress_label.text = f"开始扫描 {target} ({target_ip})..."
        
        # 记录开始时间
        start_time = time.time()
        
        # 创建队列
        port_queue = Queue()
        for port in ports:
            port_queue.put(port)
        
        # 创建线程
        for _ in range(min(threads, len(ports))):
            t = threading.Thread(
                target=self.worker,
                args=(port_queue, target_ip, timeout)
            )
            t.daemon = True
            t.start()
        
        # 等待队列完成
        def check_queue(dt):
            if not port_queue.empty() or self.scanned_ports < self.total_ports:
                Clock.schedule_once(check_queue, 0.1)
            else:
                # 扫描完成
                self.is_scanning = False
                end_time = time.time()
                scan_time = end_time - start_time
                
                # 恢复按钮
                self.scan_button.disabled = False
                self.scan_button.background_color = (0.3, 0.6, 0.9, 1)
                
                # 显示结果
                self.display_results(target, target_ip, scan_time)
        
        Clock.schedule_once(check_queue, 0.1)
    
    def update_progress(self, progress):
        """更新进度条"""
        self.progress_bar.value = progress
        self.progress_label.text = f"扫描中... {self.scanned_ports}/{self.total_ports} 个端口 ({int(progress)}%)"
    
    def display_results(self, target, target_ip, scan_time):
        """显示扫描结果"""
        self.result_text = "=" * 60 + "\n"
        self.result_text += f"扫描目标: {target} ({target_ip})\n"
        self.result_text += f"扫描端口: {self.ports_input.text.strip()}\n"
        self.result_text += f"线程数: {self.threads_input.text.strip()}\n"
        self.result_text += f"超时时间: {self.timeout_input.text.strip()}秒\n"
        self.result_text += f"扫描开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        self.result_text += f"扫描结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        self.result_text += f"扫描耗时: {scan_time:.2f} 秒\n"
        self.result_text += "=" * 60 + "\n\n"
        
        if self.open_ports:
            self.result_text += f"在 {target} 上发现 {len(self.open_ports)} 个开放端口:\n\n"
            self.result_text += f"{'端口':<10} {'服务':<20}\n"
            self.result_text += f"{'-'*30}\n"
            
            for port, service in sorted(self.open_ports):
                self.result_text += f"{port:<10} {service:<20}\n"
        else:
            self.result_text += f"在 {target} 上未发现开放端口\n"
        
        self.result_text += "\n" + "=" * 60
        
        self.result_label.text = self.result_text
        # 确保text_size已设置，以便文本正确换行
        if self.result_label.text_size[0] is None:
            self.result_label.text_size = (self.result_scroll.width - 40, None)
        self.result_label.texture_update()
        self.result_label.height = self.result_label.texture_size[1] + 20
        
        self.progress_label.text = "扫描完成"
        self.progress_bar.value = 100
        
        # 扫描完成后询问是否保存结果
        self.show_save_confirmation()
    
    def show_save_confirmation(self):
        """显示是否保存结果的确认对话框"""
        # 创建确认对话框布局
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        label = Label(
            text="是否将扫描结果保存为TXT文件？",
            color=(0.8, 0.8, 0.8, 1),
            font_size=18,
            font_name='CustomFont',
            halign='center'
        )
        layout.add_widget(label)
        
        # 按钮布局
        button_layout = BoxLayout(spacing=10, size_hint_y=None, height=50)
        
        # 是按钮
        yes_button = Button(
            text="是",
            background_color=(0.3, 0.6, 0.9, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            font_name='CustomFont',
            bold=True
        )
        button_layout.add_widget(yes_button)
        
        # 否按钮
        no_button = Button(
            text="否",
            background_color=(0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            font_name='CustomFont',
            bold=True
        )
        button_layout.add_widget(no_button)
        
        layout.add_widget(button_layout)
        
        # 创建弹出窗口
        self.save_confirm_popup = Popup(
            title="保存结果",
            content=layout,
            size_hint=(0.6, 0.4),
            background_color=(0.2, 0.2, 0.25, 1)
        )
        # 设置弹窗标题的字体
        self.save_confirm_popup.title_font = 'CustomFont'
        
        # 绑定按钮事件
        yes_button.bind(on_press=self.show_file_chooser)
        no_button.bind(on_press=self.save_confirm_popup.dismiss)
        
        # 显示确认窗口
        self.save_confirm_popup.open()
    
    def show_file_chooser(self, instance):
        """显示文件选择器，让用户选择保存路径"""
        # 关闭确认对话框
        self.save_confirm_popup.dismiss()
        
        # 创建文件选择器布局
        layout = BoxLayout(orientation='vertical', spacing=10)
        
        # 创建文件选择器
        self.filechooser = FileChooserListView(
            path=os.getcwd(),
            filters=['*.txt'],
            dirselect=True
        )
        layout.add_widget(self.filechooser)
        
        # 按钮布局
        button_layout = BoxLayout(spacing=10, size_hint_y=None, height=50)
        
        # 保存按钮
        save_button = Button(
            text="保存",
            background_color=(0.3, 0.6, 0.9, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            font_name='CustomFont',
            bold=True
        )
        button_layout.add_widget(save_button)
        
        # 取消按钮
        cancel_button = Button(
            text="取消",
            background_color=(0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1),
            font_size=16,
            font_name='CustomFont',
            bold=True
        )
        button_layout.add_widget(cancel_button)
        
        layout.add_widget(button_layout)
        
        # 创建文件选择弹出窗口
        self.filechooser_popup = Popup(
            title="选择保存路径",
            content=layout,
            size_hint=(0.8, 0.8),
            background_color=(0.2, 0.2, 0.25, 1)
        )
        # 设置弹窗标题的字体
        self.filechooser_popup.title_font = 'CustomFont'
        
        # 绑定按钮事件
        save_button.bind(on_press=self.save_results)
        cancel_button.bind(on_press=self.filechooser_popup.dismiss)
        
        # 显示文件选择窗口
        self.filechooser_popup.open()
    
    def save_results(self, instance):
        """保存扫描结果到TXT文件"""
        try:
            # 获取选择的路径
            selected = self.filechooser.selection
            if not selected:
                # 如果没有选择文件，使用当前目录和默认文件名
                save_path = os.path.join(os.getcwd(), f"port_scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            else:
                # 如果选择了目录，创建默认文件名
                if os.path.isdir(selected[0]):
                    save_path = os.path.join(selected[0], f"port_scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                else:
                    # 如果选择了文件，直接使用该路径
                    save_path = selected[0]
                    # 确保文件扩展名为.txt
                    if not save_path.endswith('.txt'):
                        save_path += '.txt'
            
            # 保存文件
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.result_text)
            
            # 关闭文件选择窗口
            self.filechooser_popup.dismiss()
            
            # 显示保存成功提示
            self.show_save_success(save_path)
        
        except Exception as e:
            # 关闭文件选择窗口
            self.filechooser_popup.dismiss()
            
            # 显示错误提示
            error_popup = Popup(
                title="保存失败",
                content=Label(
                    text=f"保存文件时发生错误:\n{str(e)}",
                    color=(1, 0, 0, 1),
                    font_name='CustomFont'
                ),
                size_hint=(0.6, 0.4),
                background_color=(0.2, 0.2, 0.25, 1)
            )
            # 设置弹窗标题的字体
            error_popup.title_font = 'CustomFont'
            error_popup.open()
    
    def show_save_success(self, save_path):
        """显示保存成功提示，2秒后自动关闭"""
        # 创建成功提示布局
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        label = Label(
            text=f"扫描结果已成功保存到:\n{save_path}",
            color=(0.3, 0.8, 0.3, 1),
            font_size=16,
            font_name='CustomFont',
            halign='center',
            valign='middle'
        )
        layout.add_widget(label)
        
        # 创建成功提示窗口
        self.success_popup = Popup(
            title="保存成功",
            content=layout,
            size_hint=(0.6, 0.4),
            background_color=(0.2, 0.2, 0.25, 1),
            auto_dismiss=False
        )
        # 设置弹窗标题的字体
        self.success_popup.title_font = 'CustomFont'
        
        # 显示提示窗口
        self.success_popup.open()
        
        # 2秒后自动关闭
        Clock.schedule_once(lambda dt: self.success_popup.dismiss(), 2)
    
    def clear_results(self, instance):
        """清空结果"""
        self.result_label.text = "扫描结果将显示在这里..."
        self.result_label.height = 50
        self.progress_label.text = "准备就绪"
        self.progress_bar.value = 0
        self.is_scanning = False
        self.open_ports = []
        self.total_ports = 0
        self.scanned_ports = 0
    
    def show_error(self, message):
        """显示错误信息"""
        popup = Popup(
            title='错误',
            content=Label(text=message, color=(1, 0, 0, 1), font_name='CustomFont'),
            size_hint=(0.7, 0.3),
            background_color=(0.2, 0.2, 0.25, 1)
        )
        popup.open()
    
    def on_stop(self):
        """应用停止时的清理"""
        self.is_scanning = False

# 加载完成标志
app_loaded = False
main_app = None

# 主程序资源
resource_manager = None

class LoadingApp(App):
    """加载窗口应用"""
    def __init__(self, **kwargs):
        super(LoadingApp, self).__init__(**kwargs)
        self.loading_thread = None
        self.main_app = None
        
    def on_start(self):
        """应用启动时设置窗口属性，确保在Window完全初始化后进行"""
        # 使用Clock.schedule_once延迟设置窗口属性，确保Window已经完全创建
        Clock.schedule_once(self.set_window_properties, 0.1)
    
    def set_window_properties(self, dt):
        """设置窗口属性"""
        # 导入Windows API模块
        try:
            from win32api import GetSystemMetrics
            from win32gui import GetForegroundWindow, MoveWindow, SetWindowPos, GetWindowRect, GetWindowLong, SetWindowLong
            from win32con import HWND_TOP, SWP_NOSIZE, SWP_NOZORDER, SWP_SHOWWINDOW, HWND_TOPMOST, GWL_STYLE, WS_POPUP, WS_VISIBLE
        except ImportError:
            print("Windows API模块导入失败，使用Kivy默认方式设置窗口属性")
            # 强制设置窗口大小
            Window.size = (700, 500)
            Window.borderless = True
            Window.topmost = True
            
            # 获取屏幕尺寸
            screen_width = Window.system_size[0]
            screen_height = Window.system_size[1]
            
            # 计算居中位置
            left = int((screen_width - 700) / 2)
            top = int((screen_height - 500) / 2)
            
            # 强制设置窗口位置
            Window.left = left
            Window.top = top
            
            # 验证设置是否生效
            print(f"加载窗口设置: 尺寸={Window.size}, 位置=({Window.left}, {Window.top})")
            return
        
        # 使用Windows API设置窗口属性
        print("使用Windows API设置加载窗口属性")
        
        # 获取当前窗口句柄
        hwnd = GetForegroundWindow()
        
        # 设置窗口为无边框样式
        # 移除标题栏和边框
        current_style = GetWindowLong(hwnd, GWL_STYLE)
        new_style = WS_POPUP | WS_VISIBLE
        SetWindowLong(hwnd, GWL_STYLE, new_style)
        print(f"已设置加载窗口为无边框样式")
        
        # 获取屏幕尺寸
        screen_width = GetSystemMetrics(0)  # SM_CXSCREEN
        screen_height = GetSystemMetrics(1)  # SM_CYSCREEN
        
        # 计算居中位置
        left = int((screen_width - 700) / 2)
        top = int((screen_height - 500) / 2)
        
        # 使用Windows API直接设置窗口位置和大小
        result = MoveWindow(hwnd, left, top, 700, 500, True)
        
        # 设置窗口为置顶
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)
        
        # 验证设置是否生效
        rect = GetWindowRect(hwnd)
        actual_width = rect[2] - rect[0]
        actual_height = rect[3] - rect[1]
        actual_left = rect[0]
        actual_top = rect[1]
        print(f"Windows API设置加载窗口: 预期尺寸=(700, 500), 实际尺寸=({actual_width}, {actual_height})")
        print(f"Windows API设置加载窗口: 预期位置=({left}, {top}), 实际位置=({actual_left}, {actual_top})")
        
    def build(self):
        # 创建布局
        layout = RelativeLayout()
        
        try:
            # 加载loading.dat图片
            loading_file = "loading.dat"
            if not os.path.exists(loading_file):
                raise FileNotFoundError(f"加载图片 {loading_file} 不存在")
            
            # 读取图片文件
            with open(loading_file, 'rb') as f:
                img_data = f.read()
            
            # 创建Image组件并显示
            self.loading_image = Image(
                source=loading_file,
                size_hint=(None, None),
                size=(700, 500),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                allow_stretch=False,
                keep_ratio=True
            )
            layout.add_widget(self.loading_image)
            
        except Exception as e:
            print(f"加载图片失败: {e}")
            # 显示错误信息
            error_label = Label(
                text=f"加载图片失败: {str(e)}",
                color=(1, 0, 0, 1),
                font_size=20,
                halign='center',
                valign='middle'
            )
            layout.add_widget(error_label)
        
        # 启动主程序加载线程
        self.loading_thread = threading.Thread(target=self.load_main_app)
        self.loading_thread.daemon = True
        self.loading_thread.start()
        
        # 启动加载完成检测
        Clock.schedule_interval(self.check_loading_complete, 0.1)
        
        return layout
    
    def load_main_app(self):
        """在后台加载主程序"""
        global app_loaded, main_app, resource_manager
        
        try:
            # 清理旧的临时文件夹
            cleanup_old_temp_folders()
            
            # 创建资源管理器实例
            resource_manager = ResourceManager()
            
            # 提取资源
            resource_manager.extract_resources()
            
            # 注册中文字体
            LabelBase.register(name='CustomFont', fn_regular=resource_manager.font_path)
            
            # 设置全局样式
            Window.clearcolor = (0.15, 0.15, 0.2, 1)
            
            # 创建主应用实例
            main_app = PortScannerGUI()
            
            # 标记加载完成
            app_loaded = True
            
        except Exception as e:
            print(f"加载主程序失败: {e}")
            app_loaded = True  # 即使失败也要退出加载窗口
    
    def check_loading_complete(self, dt):
        """检查主程序是否加载完成"""
        global app_loaded, main_app
        
        if app_loaded:
            # 取消检测
            Clock.unschedule(self.check_loading_complete)
            
            # 平滑关闭加载窗口，切换到主程序
            self.switch_to_main_app()
    
    def switch_to_main_app(self):
        """切换到主程序"""
        global main_app
        
        try:
            # 关闭加载窗口
            self.stop()
            
            # 短暂延迟，确保加载窗口完全关闭
            time.sleep(0.1)
            
            # 运行主程序
            if main_app:
                main_app.run()
        except Exception as e:
            print(f"切换到主程序失败: {e}")

# 程序退出时清理资源
import atexit
import traceback

def cleanup_resources():
    """注册为程序退出时的清理函数"""
    global resource_manager
    try:
        if resource_manager:
            resource_manager.cleanup()
            print("资源已成功清理")
    except Exception as e:
        print(f"清理资源时发生错误: {e}")
        traceback.print_exc()

# 注册清理函数
atexit.register(cleanup_resources)

if __name__ == "__main__":
    try:
        # 运行加载窗口应用
        loading_app = LoadingApp()
        loading_app.run()
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        traceback.print_exc()
    finally:
        # 确保无论程序如何退出，资源都会被清理
        print("执行最后的资源清理...")
        cleanup_resources()