# system2-code-generator1: AI智能代码生成工具

## 项目简介
一款基于PyQt6+Ollama开发的可视化AI代码生成工具，支持代码生成、本地编辑、内置执行、历史记录管理与GitHub一键上传，无需复杂命令行操作，开箱即用。

## 功能特点
- ✅ 可视化界面操作，无需专业编程基础
- ✅ 集成Ollama模型，快速生成高质量Python代码
- ✅ 代码本地编辑、保存与实时预览
- ✅ 历史生成记录管理，方便回溯与复用
- ✅ 支持将项目一键上传到GitHub仓库
- ✅ 轻量简洁，无多余冗余功能

## 安装指南
### 前置条件
- Python 3.10+
- Ollama环境已部署并启动（推荐安装Llama 2或Qwen模型）

### 安装步骤
1.  克隆本项目
    ```bash
    git clone https://github.com/chatsyx/system2-code-generator1.git
    ```
2.  进入项目目录
    ```bash
    cd system2-code-generator1
    ```
3.  安装依赖包
    ```bash
    pip install -r requirements.txt
    ```

## 使用方法
1.  启动Ollama本地服务（终端执行）
    ```bash
    ollama serve
    ```
2.  运行项目主程序
    ```bash
    python main.py
    ```
3.  进入可视化界面，输入代码生成指令，点击对应按钮完成操作
4.  生成的代码可直接编辑、保存，或一键上传到个人GitHub仓库

## 许可证
本项目采用 [MIT License](LICENSE) 开源协议，自由使用、修改与分发。
