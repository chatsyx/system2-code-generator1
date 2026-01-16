# 完整导入：覆盖所有Qt组件+内置模块+第三方模块，无Pylance报错
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QMessageBox,
    QProgressBar,
    QFileDialog,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QCheckBox
)
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, QProcess
from PyQt6.QtGui import QFont, QColor  # 显式导入字体类+颜色类，解决相关警告

# 导入历史记录工具函数（新增update_history更新函数）
from utils import save_history, load_history, clear_history, update_history

# Python内置标准模块
import sys
import os
import tempfile
import subprocess
import time
import json
import ast
import re
import warnings
import codecs  # 用于强制无BOM编码

# 第三方模块
import dotenv
import requests
from github import Github
from github.GithubException import GithubException, BadCredentialsException, UnknownObjectException

# 忽略sip相关废弃警告 + PyQt6字体无关警告
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict() is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="QFont::setPointSize")

# 加载.env配置文件（强制无BOM）
dotenv.load_dotenv(encoding='utf-8')

# ===================== 全局配置 =====================
DEFAULT_OLLAMA_MODEL = "deepseek-coder"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
# 全局有效字体配置（避免QFont报错，字体大小为正整数）
DEFAULT_FONT = QFont("Microsoft YaHei", 12)  # 字体名称+正整数大小，消除setPointSize警告
DEFAULT_SMALL_FONT = QFont("Consolas", 11)  # 代码/日志/执行输出区域字体

# ===================== 代码格式化 =====================
def format_python_code(code):
    try:
        from black import format_str, FileMode
        formatted_code = format_str(
            code,
            mode=FileMode(line_length=88, target_versions={("py38",)})
        )
        return formatted_code.strip()
    except ImportError:
        return code.strip()
    except Exception:
        return code.strip()

# ===================== 核心AI生成逻辑 =====================
def call_ai_with_thought(prompt):
    thought = f"用户需求：{prompt}\n分析：生成符合需求、可直接运行的Python代码，包含输入/输出逻辑，无语法错误。"
    
    if "判断一个数是否为偶数" in prompt:
        code = '''# 判断整数是否为偶数
def check_even_number():
    """判断整数是否为偶数的函数"""
    num = 0  # 显式初始化变量

    try:
        # 获取用户输入
        num = int(input("请输入一个整数："))
        # 判断奇偶
        if num % 2 == 0:
            print(str(num) + " 是偶数")
        else:
            print(str(num) + " 不是偶数")
    except ValueError:
        print("输入错误！请输入有效的整数")
    # 暂停窗口，避免执行完立即关闭
    input("\\n测试完成，按回车键关闭窗口...")

# 执行函数
check_even_number()'''
    elif "两数之和" in prompt:
        code = '''# 计算两数之和
def calculate_sum():
    """计算两数之和的函数"""
    num1 = 0.0  # 显式初始化变量
    num2 = 0.0  # 显式初始化变量

    try:
        num1 = float(input("请输入第一个数："))
        num2 = float(input("请输入第二个数："))
        sum_result = num1 + num2
        print("两数之和：" + str(num1) + " + " + str(num2) + " = " + str(sum_result))
    except ValueError:
        print("输入错误！请输入有效的数字")
    # 暂停窗口，避免执行完立即关闭
    input("\\n测试完成，按回车键关闭窗口...")

# 执行函数
calculate_sum()'''
    elif "冒泡排序" in prompt:
        code = '''# 冒泡排序实现
def bubble_sort():
    """冒泡排序函数"""
    nums = [5, 2, 9, 1, 5, 6]
    print("排序前：", nums)
    n = len(nums)
    # 冒泡排序核心逻辑
    for i in range(n):
        for j in range(0, n-i-1):
            if nums[j] > nums[j+1]:
                nums[j], nums[j+1] = nums[j+1], nums[j]
    print("排序后：", nums)
    # 暂停窗口，避免执行完立即关闭
    input("\\n测试完成，按回车键关闭窗口...")

# 执行函数
bubble_sort()'''
    else:
        code = f'''# 响应指令：{prompt}
def custom_code():
    """通用交互代码函数"""
    user_input = ""  # 显式初始化变量，覆盖所有分支

    try:
        print("指令已接收，以下是定制化代码：")
        # 获取用户输入
        user_input = input("请输入内容：")
        print("你输入的内容是：" + user_input)
    except Exception as err:
        print("输入处理异常：" + str(err))
    # 暂停窗口，避免执行完立即关闭
    input("\\n测试完成，按回车键关闭窗口...")

# 执行函数
custom_code()'''
    return thought, code

def get_fallback_code(prompt, error_msg):
    fallback_thought = f"原代码报错：{error_msg}\\n修正方案：修复语法/逻辑错误，确保代码可运行。"
    fallback_code = f'''# 修正后的代码（指令：{prompt}）
def corrected_code():
    """纠错后的代码函数"""
    num = 0  # 显式初始化变量，覆盖所有分支
    err = Exception("默认异常")  # 显式初始化异常变量

    try:
        # 基础容错框架
        print("纠错后代码运行中...")
        num = int(input("请输入一个整数："))
        print("输入的整数是：" + str(num))
    except ValueError as err:
        print("运行成功（容错），错误信息：" + str(err))
    except Exception as err:
        print("未知错误：" + str(err))
    # 暂停窗口，避免执行完立即关闭
    input("\\n测试完成，按回车键关闭窗口...")

# 执行函数
corrected_code()'''
    return fallback_thought, fallback_code

def _extract_and_validate_code(content):
    code_lines = []
    for line in content.splitlines():
        line_strip = line.strip()
        if (line_strip and not line_strip.startswith(("#", "*", "```", "分析", "说明", "用户需求")) 
            and not re.match(r"^[a-zA-Z0-9_]+：", line_strip)):
            code_lines.append(line_strip)
    
    fixed_lines = []
    indent_level = 0
    indent = "    "
    for line in code_lines:
        line_strip = line.strip()
        if re.match(r"^(def|class|if|for|while).*:$", line_strip):
            fixed_lines.append(line_strip)
            indent_level += 1
        elif (re.match(r"^return|^break|^continue", line_strip) and indent_level > 0):
            indent_level = max(0, indent_level - 1)
            fixed_lines.append(indent * indent_level + line_strip)
        else:
            fixed_lines.append(indent * indent_level + line_strip)
    
    raw_code = "\n".join(fixed_lines).strip()
    try:
        ast.parse(raw_code)
        raw_code = re.sub(r"f\"(.*?)\{(.*?)\}(.*?)\"", r'"\1" + str(\2) + "\3"', raw_code)
        raw_code = re.sub(r"f\'(.*?)\{(.*?)\}(.*?)\'", r'"\1" + str(\2) + "\3"', raw_code)
        return raw_code
    except SyntaxError:
        return ""

# ===================== Ollama异步生成线程 =====================
class OllamaGenerateThread(QThread):
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(bool, str, str)
    log_signal = pyqtSignal(str)

    def __init__(self, prompt, selected_model):
        super().__init__()
        self.prompt = prompt
        self.selected_model = selected_model

    def run(self):
        try:
            self.progress_signal.emit(10)
            self.log_signal.emit(f"正在连接Ollama模型（{self.selected_model}）...")
            
            ollama_prompt = f"""
            仅输出可运行的Python代码，无任何注释、说明、空行、代码块标记：
            1. 函数/if/for/while等代码块必须用4个空格缩进；
            2. 包含完整输入→处理→输出逻辑，运行后暂停窗口；
            3. 禁止生成自然语言，仅保留Python代码。
            生成需求：{self.prompt}
            """
            payload = {
                "model": self.selected_model,
                "prompt": ollama_prompt,
                "stream": False,
                "temperature": 0.1
            }

            self.progress_signal.emit(30)
            self.log_signal.emit("发送代码生成请求...")
            
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )

            self.progress_signal.emit(60)
            if response.status_code != 200:
                raise Exception(f"Ollama响应失败（状态码：{response.status_code}）")
            
            result_data = response.json()
            ollama_content = result_data.get("response", "").strip()
            if not ollama_content:
                raise Exception("Ollama返回空内容")
            
            self.log_signal.emit("提取并验证生成的代码...")
            generated_code = _extract_and_validate_code(ollama_content)
            if not generated_code:
                self.log_signal.emit("Ollama生成的代码无效，切换为本地兜底逻辑...")
                thought, code = call_ai_with_thought(self.prompt)
                self.progress_signal.emit(100)
                self.result_signal.emit(False, thought, code)
                return
            
            thought = f"用户需求：{self.prompt}\\n分析：通过Ollama模型（{self.selected_model}）生成纯Python代码，已通过语法验证。"
            self.progress_signal.emit(100)
            self.log_signal.emit(f"Ollama模型（{self.selected_model}）代码生成成功！")
            self.result_signal.emit(True, thought, generated_code)

        except requests.exceptions.ConnectionError:
            self.log_signal.emit(f"无法连接Ollama服务！请先运行：ollama run {self.selected_model}，切换为本地兜底逻辑...")
            thought, code = call_ai_with_thought(self.prompt)
            self.progress_signal.emit(100)
            self.result_signal.emit(False, thought, code)
        except Exception as e:
            self.log_signal.emit(f"Ollama生成失败：{str(e)}，切换为本地兜底逻辑...")
            thought, code = call_ai_with_thought(self.prompt)
            self.progress_signal.emit(100)
            self.result_signal.emit(False, thought, code)

# ===================== 内置代码执行线程（替代外部终端） =====================
class InternalExecuteThread(QObject):
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(bool)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_finished)

    def start_execution(self):
        """启动代码执行"""
        try:
            # 配置Python执行环境，编码为UTF-8
            self.process.setProgram(sys.executable)
            self.process.setArguments([self.file_path])
            self.process.setWorkingDirectory(os.path.dirname(self.file_path))
            # 设置编码，避免中文乱码
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.process.start()
            if not self.process.waitForStarted(5000):
                self.error_signal.emit("无法启动Python进程，请检查Python环境是否配置正确")
                self.finish_signal.emit(False)
        except Exception as e:
            self.error_signal.emit(f"启动执行失败：{str(e)}")
            self.finish_signal.emit(False)

    def stop_execution(self):
        """终止代码执行"""
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(3000)
            self.output_signal.emit("\\n⚠️ 代码执行已被手动终止")
            self.finish_signal.emit(False)

    def _read_stdout(self):
        """读取标准输出"""
        try:
            output = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
            if output:
                self.output_signal.emit(output)
        except Exception as e:
            self.error_signal.emit(f"读取输出失败：{str(e)}")

    def _read_stderr(self):
        """读取标准错误"""
        try:
            error = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
            if error:
                self.error_signal.emit(f"❌ 执行错误：{error}")
        except Exception as e:
            self.error_signal.emit(f"读取错误信息失败：{str(e)}")

    def _on_finished(self):
        """执行完成回调"""
        exit_code = self.process.exitCode()
        if exit_code == 0:
            self.output_signal.emit("\\n✅ 代码执行完成，无异常退出")
            self.finish_signal.emit(True)
        else:
            self.error_signal.emit(f"\\n❌ 代码执行异常退出，退出码：{exit_code}")
            self.finish_signal.emit(False)

# ===================== 主窗口类（进阶优化：可编辑+搜索+内置执行） =====================
class System2MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System2 智能代码生成工具（进阶优化版：可编辑+历史搜索+内置执行）")
        self.setFixedSize(1400, 950)  # 加宽加高窗口，容纳新增功能面板
        self.temp_code_file = None
        self.current_progress = 0
        self.ollama_thread = None
        self.history_records = []  # 存储历史记录数据
        self.current_selected_history_idx = None  # 记录当前选中的历史记录索引
        self.execute_thread = None  # 内置执行线程实例

        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
        self.GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
        self.GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "system2-code-repo")

        # 全局设置字体（消除QFont警告，所有组件继承有效字体）
        self.setFont(DEFAULT_FONT)
        self._init_ui()
        self._load_history_to_list()  # 启动时加载历史记录

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # 水平布局：历史记录+主内容
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ===== 左侧：历史记录面板（新增搜索功能） =====
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setSpacing(10)

        # 历史记录标题
        history_title = QLabel("📋 历史记录（按时间倒序）")
        history_title.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        history_title.setStyleSheet("color: #2c3e50;")
        history_layout.addWidget(history_title)

        # 历史记录搜索框（新增）
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜索：")
        search_label.setFont(DEFAULT_FONT)
        self.history_search_edit = QLineEdit()
        self.history_search_edit.setPlaceholderText("输入关键词筛选历史指令...")
        self.history_search_edit.setFont(DEFAULT_FONT)
        self.history_search_edit.setStyleSheet("padding: 6px;")
        self.history_search_edit.textChanged.connect(self._filter_history_list)  # 实时筛选
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.history_search_edit)
        history_layout.addLayout(search_layout)

        # 历史记录列表
        self.history_list = QListWidget()
        self.history_list.setFont(DEFAULT_SMALL_FONT)
        self.history_list.setStyleSheet("padding: 6px;")
        self.history_list.itemDoubleClicked.connect(self._on_history_item_click)  # 双击加载
        history_layout.addWidget(self.history_list)

        # 历史记录操作按钮（新增更新历史按钮）
        history_btn_layout = QHBoxLayout()
        self.load_history_btn = QPushButton("加载选中记录")
        self.update_history_btn = QPushButton("更新当前记录")  # 新增：更新修改后的代码到历史
        self.clear_history_btn = QPushButton("清空所有记录")
        history_btn_style = """
            QPushButton {
                padding: 8px;
                font-size: 10px;
                font-weight: bold;
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton#update_btn {
                background-color: #f39c12;
            }
            QPushButton#update_btn:hover {
                background-color: #e67e22;
            }
            QPushButton#clear_btn {
                background-color: #e74c3c;
            }
            QPushButton#clear_btn:hover {
                background-color: #c0392b;
            }
        """
        self.load_history_btn.setStyleSheet(history_btn_style)
        self.update_history_btn.setStyleSheet(history_btn_style)
        self.clear_history_btn.setStyleSheet(history_btn_style)
        self.update_history_btn.setObjectName("update_btn")
        self.clear_history_btn.setObjectName("clear_btn")

        self.load_history_btn.clicked.connect(self._on_history_item_click)
        self.update_history_btn.clicked.connect(self._on_update_history_click)
        self.clear_history_btn.clicked.connect(self._on_clear_history_click)

        history_btn_layout.addWidget(self.load_history_btn)
        history_btn_layout.addWidget(self.update_history_btn)
        history_btn_layout.addWidget(self.clear_history_btn)
        history_layout.addLayout(history_btn_layout)

        # ===== 右侧：主功能面板（新增可编辑代码+内置执行面板） =====
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setSpacing(12)

        # 标题标签
        title_label = QLabel("System2 代码生成工具 - 生成→编辑→内置执行→保存→上传GitHub（进阶优化版）")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        main_content_layout.addWidget(title_label)

        # 输入布局
        input_layout = QHBoxLayout()
        input_label = QLabel("生成指令：")
        input_label.setFont(DEFAULT_FONT)
        input_label.setStyleSheet("font-weight: bold;")
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("例如：生成判断一个数是否为质数的Python代码、生成1-100偶数和代码")
        self.input_edit.setFont(DEFAULT_FONT)
        self.input_edit.setStyleSheet("padding: 6px;")
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_edit)
        main_content_layout.addLayout(input_layout)

        # 模型选择布局
        model_layout = QHBoxLayout()
        model_label = QLabel("Ollama模型：")
        model_label.setFont(DEFAULT_FONT)
        model_label.setStyleSheet("font-weight: bold;")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-coder", "llama3:8b"])
        self.model_combo.setCurrentText(DEFAULT_OLLAMA_MODEL)
        self.model_combo.setFont(DEFAULT_FONT)
        self.model_combo.setStyleSheet("padding: 6px; min-width: 150px;")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        main_content_layout.addLayout(model_layout)

        # AI思考过程
        thought_label = QLabel("📝 AI思考过程：")
        thought_label.setFont(DEFAULT_FONT)
        thought_label.setStyleSheet("font-weight: bold;")
        self.thought_edit = QTextEdit()
        self.thought_edit.setReadOnly(True)
        self.thought_edit.setFixedHeight(80)
        self.thought_edit.setFont(DEFAULT_SMALL_FONT)
        self.thought_edit.setStyleSheet("padding: 6px;")
        main_content_layout.addWidget(thought_label)
        main_content_layout.addWidget(self.thought_edit)

        # 生成的代码（改为可编辑，新增）
        code_label = QLabel("💻 生成的Python代码（可编辑，修改后可更新历史/测试）：")
        code_label.setFont(DEFAULT_FONT)
        code_label.setStyleSheet("font-weight: bold;")
        self.code_edit = QTextEdit()  # 取消只读，支持编辑
        self.code_edit.setFixedHeight(200)
        self.code_edit.setFont(DEFAULT_SMALL_FONT)
        self.code_edit.setStyleSheet("padding: 6px; border: 1px solid #ddd;")
        # 可选：开启行号（简化版，保持轻量）
        main_content_layout.addWidget(code_label)
        main_content_layout.addWidget(self.code_edit)

        # 内置代码执行面板（新增，替代外部终端）
        execute_label = QLabel("▶️ 内置执行结果（无需弹出终端，直接查看输出）：")
        execute_label.setFont(DEFAULT_FONT)
        execute_label.setStyleSheet("font-weight: bold;")
        self.execute_edit = QTextEdit()
        self.execute_edit.setReadOnly(True)
        self.execute_edit.setFixedHeight(150)
        self.execute_edit.setFont(DEFAULT_SMALL_FONT)
        self.execute_edit.setStyleSheet("padding: 6px; background-color: #f8f9fa; color: #2c3e50;")
        main_content_layout.addWidget(execute_label)
        main_content_layout.addWidget(self.execute_edit)

        # 执行控制按钮（新增）
        execute_btn_layout = QHBoxLayout()
        self.run_code_btn = QPushButton("内置运行代码")
        self.stop_code_btn = QPushButton("终止运行")
        self.format_code_btn = QPushButton("格式化代码")  # 新增：格式化编辑后的代码
        execute_btn_style = """
            QPushButton {
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton#stop_btn {
                background-color: #e74c3c;
            }
            QPushButton#stop_btn:hover {
                background-color: #c0392b;
            }
            QPushButton#format_btn {
                background-color: #3498db;
            }
            QPushButton#format_btn:hover {
                background-color: #2980b9;
            }
        """
        self.run_code_btn.setStyleSheet(execute_btn_style)
        self.stop_code_btn.setStyleSheet(execute_btn_style)
        self.format_code_btn.setStyleSheet(execute_btn_style)
        self.stop_code_btn.setObjectName("stop_btn")
        self.format_code_btn.setObjectName("format_btn")

        self.run_code_btn.clicked.connect(self._run_code_internal)
        self.stop_code_btn.clicked.connect(self._stop_code_internal)
        self.format_code_btn.clicked.connect(self._format_edited_code)

        execute_btn_layout.addWidget(self.run_code_btn)
        execute_btn_layout.addWidget(self.stop_code_btn)
        execute_btn_layout.addWidget(self.format_code_btn)
        main_content_layout.addLayout(execute_btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("height: 20px;")
        main_content_layout.addWidget(self.progress_bar)

        # 实时日志
        log_label = QLabel("📜 实时日志：")
        log_label.setFont(DEFAULT_FONT)
        log_label.setStyleSheet("font-weight: bold;")
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(100)
        self.log_edit.setFont(DEFAULT_SMALL_FONT)
        self.log_edit.setStyleSheet("padding: 6px;")
        main_content_layout.addWidget(log_label)
        main_content_layout.addWidget(self.log_edit)

        # 按钮布局（保留原有功能按钮）
        btn_layout = QHBoxLayout()
        self.gen_code_btn = QPushButton("1. 生成代码")
        self.save_local_btn = QPushButton("2. 保存到本地")
        self.upload_github_btn = QPushButton("3. 上传GitHub")
        
        btn_style = """
            QPushButton {
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """
        for btn in [self.gen_code_btn, self.save_local_btn, self.upload_github_btn]:
            btn.setFont(DEFAULT_FONT)
            btn.setStyleSheet(btn_style)
        
        self.gen_code_btn.clicked.connect(self.generate_code)
        self.save_local_btn.clicked.connect(self.save_code_to_local)
        self.upload_github_btn.clicked.connect(self.upload_to_github)
        
        btn_layout.addWidget(self.gen_code_btn)
        btn_layout.addWidget(self.save_local_btn)
        btn_layout.addWidget(self.upload_github_btn)
        main_content_layout.addLayout(btn_layout)

        # 状态标签
        self.status_label = QLabel(f"状态：就绪 - 请输入指令生成代码 | 当前模型：{DEFAULT_OLLAMA_MODEL} | 保存默认路径：桌面 | 支持编辑代码+内置执行")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 11))
        self.status_label.setStyleSheet("color: #7f8c8d; margin-top: 8px;")
        main_content_layout.addWidget(self.status_label)

        # ===== 组装水平布局（历史记录+主内容） =====
        main_layout.addWidget(history_widget, stretch=1)  # 历史记录占1份宽度
        main_layout.addWidget(main_content_widget, stretch=4)  # 主内容占4份宽度

    def _filter_history_list(self):
        """实时筛选历史记录（按关键词匹配指令）"""
        search_keyword = self.history_search_edit.text().strip().lower()
        self.history_list.clear()

        if not self.history_records:
            self.history_list.addItem("暂无历史记录（生成代码后自动保存）")
            return

        # 筛选符合关键词的记录
        filtered_records = []
        for record in self.history_records:
            prompt = record.get("prompt", "").lower()
            if search_keyword in prompt or not search_keyword:
                filtered_records.append(record)

        if not filtered_records:
            self.history_list.addItem(f"无匹配关键词「{search_keyword}」的历史记录")
            return

        # 按时间倒序显示筛选结果
        filtered_records.sort(key=lambda x: x.get("time", ""), reverse=True)
        for idx, record in enumerate(filtered_records):
            time_str = record.get("time", "未知时间")
            prompt = record.get("prompt", "无指令")[:30]
            model = record.get("model", "未知模型")
            updated_mark = "（已更新）" if "updated" in record else ""
            list_item_text = f"[{time_str}] {updated_mark} | 模型：{model} | 指令：{prompt}..."
            list_item = QListWidgetItem(list_item_text)
            # 关联原始记录索引
            original_idx = self.history_records.index(record)
            list_item.setData(Qt.ItemDataRole.UserRole, original_idx)
            self.history_list.addItem(list_item)

    def _load_history_to_list(self):
        """加载历史记录到列表控件，按时间倒序排列（兼容容错逻辑）"""
        self.history_list.clear()
        self.history_records = load_history()  # 调用修复后的load_history
        # 按时间倒序排序（最新记录在顶部）
        self.history_records.sort(key=lambda x: x.get("time", ""), reverse=True)

        if not self.history_records:
            self.history_list.addItem("暂无历史记录（生成代码后自动保存）")
            return

        for idx, record in enumerate(self.history_records):
            time_str = record.get("time", "未知时间")
            prompt = record.get("prompt", "无指令")[:30]
            model = record.get("model", "未知模型")
            updated_mark = "（已更新）" if "updated" in record else ""
            list_item_text = f"[{time_str}] {updated_mark} | 模型：{model} | 指令：{prompt}..."
            list_item = QListWidgetItem(list_item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, idx)  # 存储记录索引，用于后续加载
            self.history_list.addItem(list_item)

    def _on_history_item_click(self):
        """加载选中的历史记录到当前UI"""
        selected_item = self.history_list.currentItem()
        if not selected_item or not self.history_records:
            QMessageBox.warning(self, "提示", "请选择有效的历史记录！")
            return

        try:
            record_idx = selected_item.data(Qt.ItemDataRole.UserRole)
            if record_idx is None:
                return

            self.current_selected_history_idx = record_idx  # 记录当前选中索引，用于后续更新
            record = self.history_records[record_idx]
            prompt = record.get("prompt", "")
            model = record.get("model", DEFAULT_OLLAMA_MODEL)
            code = record.get("code", "")
            thought = f"用户需求：{prompt}\\n分析：历史记录（模型：{model}）{('（已更新）' if 'updated' in record else '')}，已加载保存的代码。"

            # 填充到UI
            self.input_edit.setText(prompt)
            self.model_combo.setCurrentText(model)
            self.thought_edit.setText(thought)
            self.code_edit.setText(code)

            # 生成临时文件（用于测试/上传）
            formatted_code = format_python_code(code)
            self.temp_code_file = tempfile.mktemp(suffix=".py", prefix="system2_history_")
            with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
                f.write(formatted_code)

            self._update_log(f"✅ 已加载历史记录（{record.get('time', '未知时间')}）")
            self.status_label.setText(f"✅ 历史记录加载成功 | 当前模型：{model} | 保存默认路径：桌面 | 可编辑/测试/保存该代码")
        except Exception as e:
            self._update_log(f"❌ 加载历史记录失败：{str(e)}")
            QMessageBox.critical(self, "错误", f"加载历史记录出错：{str(e)}")

    def _on_update_history_click(self):
        """更新当前选中的历史记录（保存编辑后的代码）"""
        if self.current_selected_history_idx is None or not self.history_records:
            QMessageBox.warning(self, "提示", "请先加载一条历史记录再进行更新！")
            return

        code_content = self.code_edit.toPlainText().strip()
        if not code_content:
            QMessageBox.warning(self, "提示", "无有效代码可更新到历史记录！")
            return

        try:
            # 格式化编辑后的代码
            formatted_code = format_python_code(code_content)
            prompt = self.input_edit.text().strip()
            model = self.model_combo.currentText()

            # 构建更新后的记录
            updated_record = {
                "prompt": prompt,
                "model": model,
                "code": formatted_code
            }

            # 调用update_history更新历史记录
            update_success = update_history(self.current_selected_history_idx, updated_record)
            if update_success:
                # 刷新历史记录列表和当前数据
                self.history_records = load_history()
                self._filter_history_list()  # 刷新筛选后的列表
                self._update_log(f"✅ 已成功更新历史记录（索引：{self.current_selected_history_idx}）")
                # 更新临时文件
                with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
                    f.write(formatted_code)
                self.status_label.setText(f"✅ 历史记录更新成功 | 当前模型：{model} | 编辑后的代码已保存到history.json")
                QMessageBox.information(self, "成功", "历史记录已更新！编辑后的代码已保存。")
            else:
                self._update_log(f"❌ 历史记录更新失败（索引无效或文件损坏）")
                QMessageBox.critical(self, "错误", "历史记录更新失败，请重试！")
        except Exception as e:
            self._update_log(f"❌ 更新历史记录出错：{str(e)}")
            QMessageBox.critical(self, "错误", f"更新历史记录时发生异常：{str(e)}")

    def _on_clear_history_click(self):
        """清空所有历史记录（带确认提示）"""
        if not self.history_records:
            QMessageBox.information(self, "提示", "暂无历史记录可清空！")
            return

        confirm = QMessageBox.question(
            self,
            "确认清空",
            "是否确定清空所有历史记录？该操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            self._update_log("ℹ️ 用户取消了清空历史记录操作")
            return

        try:
            clear_history()
            self.current_selected_history_idx = None  # 重置选中索引
            self._update_log("✅ 所有历史记录已清空")
            self._load_history_to_list()  # 刷新列表
            self.status_label.setText(f"✅ 历史记录已清空 | 当前模型：{self.model_combo.currentText()} | 保存默认路径：桌面 | 重新生成代码将创建新记录")
            QMessageBox.information(self, "成功", "所有历史记录已清空！")
        except Exception as e:
            self._update_log(f"❌ 清空历史记录失败：{str(e)}")
            QMessageBox.critical(self, "错误", f"清空历史记录出错：{str(e)}")

    def _format_edited_code(self):
        """格式化编辑后的代码"""
        code_content = self.code_edit.toPlainText().strip()
        if not code_content:
            QMessageBox.warning(self, "提示", "无有效代码可格式化！")
            return

        try:
            formatted_code = format_python_code(code_content)
            self.code_edit.setText(formatted_code)
            self._update_log("✅ 代码格式化完成（使用black规范）")
            # 更新临时文件
            if self.temp_code_file and os.path.exists(self.temp_code_file):
                with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
                    f.write(formatted_code)
            self.status_label.setText(f"✅ 代码格式化成功 | 当前模型：{self.model_combo.currentText()} | 可直接运行/保存格式化后的代码")
        except Exception as e:
            self._update_log(f"❌ 代码格式化失败：{str(e)}（可能缺少black库，已跳过格式化）")
            QMessageBox.warning(self, "格式化提示", f"格式化失败：{str(e)}\n\\n请安装black库：pip install black")

    def _run_code_internal(self):
        """内置运行代码（无需弹出终端）"""
        code_content = self.code_edit.toPlainText().strip()
        if not code_content:
            QMessageBox.warning(self, "提示", "无有效代码可运行！")
            return

        # 生成临时文件
        formatted_code = format_python_code(code_content)
        self.temp_code_file = tempfile.mktemp(suffix=".py", prefix="system2_internal_")
        with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
            f.write(formatted_code)

        # 清空之前的执行结果
        self.execute_edit.clear()
        self.execute_edit.append("▶️ 开始执行代码...\n" + "="*50 + "\n")
        self._update_log("✅ 启动内置代码执行，结果将显示在执行面板中")
        self.status_label.setText(f"状态：代码执行中... | 当前模型：{self.model_combo.currentText()} | 请勿重复运行，可点击「终止运行」停止")

        # 初始化执行线程
        self.execute_thread = InternalExecuteThread(self.temp_code_file)
        self.execute_thread.output_signal.connect(self._append_execute_output)
        self.execute_thread.error_signal.connect(self._append_execute_output)
        self.execute_thread.finish_signal.connect(self._on_execute_finish)

        # 启动执行
        self.execute_thread.start_execution()
        self.run_code_btn.setDisabled(True)

    def _stop_code_internal(self):
        """终止内置代码执行"""
        if self.execute_thread and self.run_code_btn.isDisabled():
            self.execute_thread.stop_execution()
            self.run_code_btn.setEnabled(True)
            self._update_log("✅ 已终止内置代码执行")
            self.status_label.setText(f"状态：代码执行已终止 | 当前模型：{self.model_combo.currentText()} | 可重新编辑并运行代码")

    def _append_execute_output(self, output):
        """追加执行结果到面板"""
        self.execute_edit.append(output)
        self.execute_edit.verticalScrollBar().setValue(self.execute_edit.verticalScrollBar().maximum())

    def _on_execute_finish(self, success):
        """代码执行完成回调"""
        self.run_code_btn.setEnabled(True)
        self.execute_edit.append("\n" + "="*50 + "\n▶️ 执行结束")
        if success:
            self._update_log("✅ 内置代码执行完成，无异常")
            self.status_label.setText(f"✅ 代码执行成功 | 当前模型：{self.model_combo.currentText()} | 可编辑代码后重新运行或保存")
        else:
            self._update_log("⚠️ 内置代码执行完成，存在异常（查看执行面板详情）")
            self.status_label.setText(f"⚠️ 代码执行存在异常 | 当前模型：{self.model_combo.currentText()} | 请查看执行结果面板排查错误")

    def _update_progress(self, value):
        self.current_progress = max(0, min(100, value))
        self.progress_bar.setValue(self.current_progress)

    def _update_log(self, msg):
        try:
            timestamp = time.strftime("[%H:%M:%S]")
            log_msg = f"{timestamp} {msg}"
            self.log_edit.append(log_msg)
            self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())
            # 日志文件强制无BOM
            with codecs.open("system2_log.txt", "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except Exception as e:
            error_msg = f"[日志更新失败] {str(e)}"
            self.log_edit.append(error_msg)

    def generate_code(self):
        prompt = self.input_edit.text().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入生成指令！")
            return

        selected_model = self.model_combo.currentText()

        self._update_progress(0)
        self._update_log(f"开始生成代码（优先使用Ollama模型：{selected_model}，失败自动切换本地兜底）...")
        self.status_label.setText(f"状态：生成代码中... | 当前模型：{selected_model} | 保存默认路径：桌面 | 支持编辑代码+内置执行")
        self.gen_code_btn.setDisabled(True)
        QApplication.processEvents()

        self.ollama_thread = OllamaGenerateThread(prompt, selected_model)
        self.ollama_thread.progress_signal.connect(self._update_progress)
        self.ollama_thread.log_signal.connect(self._update_log)
        self.ollama_thread.result_signal.connect(self.on_ollama_generate_finish)
        self.ollama_thread.start()

    def on_ollama_generate_finish(self, is_ollama_success, thought, code):
        try:
            formatted_code = format_python_code(code)

            # 临时文件强制无BOM
            self.temp_code_file = tempfile.mktemp(suffix=".py", prefix="system2_")
            with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
                f.write(formatted_code)

            # 检测并去除代码中的BOM
            if formatted_code.startswith('\ufeff'):
                formatted_code = formatted_code[1:]
                with codecs.open(self.temp_code_file, "w", encoding="utf-8") as f:
                    f.write(formatted_code)

            prompt = self.input_edit.text().strip()
            selected_model = self.model_combo.currentText()
            record = {
                "prompt": prompt,
                "model": selected_model,
                "code": formatted_code
            }
            save_history(record)  # 调用修复后的save_history
            self._update_log("✅ 历史记录已自动保存到history.json")
            self.current_selected_history_idx = None  # 重置选中索引
            self._load_history_to_list()  # 刷新历史记录列表

            self.thought_edit.setText(thought)
            self.code_edit.setText(formatted_code)  # 填充到可编辑面板

            if is_ollama_success:
                self._update_log("✅ 代码生成完成（Ollama模型生成）！已格式化并保存到临时文件")
                self.status_label.setText(f"✅ 代码生成成功（Ollama模型）！可编辑/内置运行/保存该代码 | 当前模型：{selected_model} | 历史记录已保存")
            else:
                self._update_log("✅ 代码生成完成（本地兜底逻辑）！已格式化并保存到临时文件")
                self.status_label.setText(f"✅ 代码生成成功（本地兜底）！可编辑/内置运行/保存该代码 | 当前模型：{selected_model} | 历史记录已保存")
        except Exception as e:
            self._update_log(f"❌ 代码保存失败：{str(e)}")
            self.status_label.setText(f"❌ 生成失败！查看日志 | 当前模型：{self.model_combo.currentText()} | 保存默认路径：桌面 | 历史记录保存失败")
            QMessageBox.critical(self, "错误", f"保存代码出错：{str(e)}")
        finally:
            self.gen_code_btn.setDisabled(False)
            self._update_progress(100)

    def save_code_to_local(self):
        code_content = self.code_edit.toPlainText().strip()
        if not code_content:
            QMessageBox.warning(self, "提示", "无生成的代码可保存！")
            return

        # 检测并去除代码中的BOM
        if code_content.startswith('\ufeff'):
            code_content = code_content[1:]
            self._update_log("ℹ️ 已自动去除代码中的UTF-8 BOM标记")

        desktop_path = os.path.expanduser("~/Desktop")
        default_file_name = f"system2_code_{time.strftime('%Y%m%d_%H%M%S')}.py"
        default_save_path = os.path.join(desktop_path, default_file_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存Python代码到本地（默认路径：桌面）",
            default_save_path,
            "Python Files (*.py);;All Files (*.*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        
        if not file_path:
            self._update_log("ℹ️ 用户取消了保存操作")
            return

        try:
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir, exist_ok=True)
                self._update_log(f"ℹ️ 已创建保存目录：{file_dir}")

            # 强制无BOM保存
            with codecs.open(file_path, "w", encoding="utf-8") as f:
                f.write(code_content)

            self._update_log(f"✅ 代码已成功保存到：{file_path}")
            QMessageBox.information(
                self,
                "保存成功！",
                f"代码已格式化并保存到：\\n\\n{file_path}\\n\\n可直接打开该文件运行～",
                QMessageBox.StandardButton.Ok
            )
            self.status_label.setText(f"✅ 代码保存成功！路径：{os.path.basename(file_path)} | 当前模型：{self.model_combo.currentText()} | 历史记录自动保存到history.json")

        except PermissionError:
            self._update_log(f"❌ 保存失败：无权限写入路径 {file_path}")
            QMessageBox.critical(self, "保存失败", f"无权限写入该路径！\\n请选择其他文件夹或关闭正在占用该文件的程序。")
        except OSError as e:
            self._update_log(f"❌ 保存失败：路径非法或包含特殊字符 - {str(e)}")
            QMessageBox.critical(self, "保存失败", f"路径非法或包含特殊字符！\\n请选择无特殊字符的路径（如桌面）。")
        except Exception as e:
            self._update_log(f"❌ 保存失败：{str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存代码出错：{str(e)}")

    def upload_to_github(self):
        if not self.temp_code_file or not os.path.exists(self.temp_code_file):
            QMessageBox.warning(self, "提示", "请先生成并测试代码！")
            return
        if not self.GITHUB_TOKEN or not self.GITHUB_USERNAME:
            QMessageBox.critical(self, "配置错误", 
                                ".env文件中未配置以下必填项：\\n1. GITHUB_TOKEN（GitHub个人访问令牌）\\n2. GITHUB_USERNAME（GitHub用户名）\\n\\n请配置后重试！")
            return

        selected_model = self.model_combo.currentText()
        self._update_progress(0)
        self._update_log("开始上传GitHub...")
        self.status_label.setText(f"状态：连接GitHub中... | 当前模型：{selected_model} | 保存默认路径：桌面 | 支持编辑代码+内置执行")
        QApplication.processEvents()

        try:
            self._update_progress(20)
            try:
                github_client = Github(self.GITHUB_TOKEN)
                github_user = github_client.get_user(self.GITHUB_USERNAME)
                github_user.login
                self._update_log(f"✅ 已成功连接到GitHub用户：{self.GITHUB_USERNAME}")
            except BadCredentialsException:
                raise Exception("GitHub Token无效！请检查Token是否正确，或重新生成（需勾选repo权限）")
            except UnknownObjectException:
                raise Exception("GitHub用户名错误！请检查GITHUB_USERNAME是否与Token所属用户一致")

            self._update_progress(40)
            target_repo = None
            try:
                target_repo = github_user.get_repo(self.GITHUB_REPO_NAME)
                self._update_log(f"✅ 找到已有仓库：{self.GITHUB_REPO_NAME}")
            except GithubException:
                self._update_log(f"⚠️ 仓库 {self.GITHUB_REPO_NAME} 不存在，创建新仓库...")
                headers = {
                    "Authorization": f"token {self.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                }
                repo_data = {
                    "name": self.GITHUB_REPO_NAME,
                    "description": "System2工具自动创建的仓库（进阶优化版：可编辑+历史搜索+内置执行）",
                    "auto_init": True,
                    "private": False
                }
                create_response = requests.post(
                    url="https://api.github.com/user/repos",
                    json=repo_data,
                    headers=headers,
                    timeout=30
                )
                if create_response.status_code == 201:
                    self._update_log(f"✅ 新建仓库成功：{self.GITHUB_REPO_NAME}")
                    target_repo = github_user.get_repo(self.GITHUB_REPO_NAME)
                else:
                    err_data = create_response.json()
                    raise Exception(f"创建仓库失败！返回：{err_data.get('message', '未知错误')}")

            self._update_progress(60)
            # 读取临时文件并去BOM（读取编辑后的最新代码）
            code_content = self.code_edit.toPlainText().strip()
            if code_content.startswith('\ufeff'):
                code_content = code_content[1:]
                self._update_log("ℹ️ 已自动去除代码中的UTF-8 BOM标记")
            self._update_log("✅ 已读取编辑后的最新代码内容")

            self._update_progress(80)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_name = f"system2_code_{timestamp}.py"
            target_repo.create_file(
                path=file_name,
                message=f"System2自动上传（{self.model_combo.currentText()}模型）：{self.input_edit.text()[:20]}",
                content=code_content
            )

            self._update_progress(100)
            repo_url = f"https://github.com/{self.GITHUB_USERNAME}/{self.GITHUB_REPO_NAME}/blob/main/{file_name}"
            self._update_log(f"✅ 上传成功！代码地址：{repo_url}")
            self.status_label.setText(f"✅ 上传GitHub成功！| 当前模型：{selected_model} | 保存默认路径：桌面 | 支持编辑代码+内置执行")
            QMessageBox.information(self, "上传成功", 
                                  f"代码已上传到GitHub！\\n仓库地址：https://github.com/{self.GITHUB_USERNAME}/{self.GITHUB_REPO_NAME}\\n文件地址：{repo_url}")

        except Exception as e:
            self._update_progress(100)
            self._update_log(f"❌ 上传失败：{str(e)}")
            self.status_label.setText(f"❌ 上传GitHub失败！| 当前模型：{selected_model} | 保存默认路径：桌面 | 支持编辑代码+内置执行")
            QMessageBox.critical(self, "错误", f"上传出错：{str(e)}")

# ===================== 程序入口 =====================
if __name__ == "__main__":
    # 强制系统编码为无BOM的UTF-8，消除环境编码干扰
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["QT_FONT_DPI"] = "96"  # 固定字体DPI，避免QFont尺寸异常

    app = QApplication(sys.argv)
    # 应用全局字体，确保所有组件无QFont报错
    app.setFont(DEFAULT_FONT)
    window = System2MainWindow()
    window.show()
    sys.exit(app.exec())