import json
import time
import os
import codecs  # 强制无BOM编码

# 历史记录文件路径
HISTORY_FILE = "history.json"

def save_history(record):
    """
    保存单条历史记录到history.json
    record格式：{"time": 时间戳, "prompt": 生成指令, "model": 选择的模型, "code": 生成的代码}
    """
    # 保证文件存在（强制无BOM写入）
    if not os.path.exists(HISTORY_FILE):
        with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    try:
        # 读取已有记录（强制无BOM读取，去除可能的BOM残留）
        with codecs.open(HISTORY_FILE, "r", encoding="utf-8") as f:
            file_content = f.read().strip()  # 去除首尾空白字符
            if not file_content:  # 文件为空，直接初始化为空列表
                histories = []
            else:
                if file_content.startswith('\ufeff'):
                    file_content = file_content[1:]
                histories = json.loads(file_content)
    except json.JSONDecodeError:
        # JSON解析失败，重置文件为空白列表
        histories = []
        with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(histories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 其他读取错误，同样重置文件
        histories = []
        with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(histories, f, ensure_ascii=False, indent=2)
    
    # 添加新记录（带时间戳）
    record["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    histories.append(record)
    
    # 写入文件（强制无BOM，避免生成BOM标记）
    with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(histories, f, ensure_ascii=False, indent=2)

def load_history():
    """读取所有历史记录，返回列表（添加JSON解析容错，文件损坏时自动重置）"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        # 读取时去BOM，确保无残留
        with codecs.open(HISTORY_FILE, "r", encoding="utf-8") as f:
            file_content = f.read().strip()  # 去除首尾空白字符
            if not file_content:  # 文件为空
                return []
            if file_content.startswith('\ufeff'):
                file_content = file_content[1:]
            return json.loads(file_content)
    except json.JSONDecodeError:
        # JSON解析失败，重置文件为空白列表
        with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    except Exception as e:
        # 其他读取错误，同样返回空列表
        return []

def clear_history():
    """清空所有历史记录（保留空的history.json文件）"""
    # 写入空列表，保留文件避免后续报错
    with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

def update_history(record_idx, updated_record):
    """
    更新指定索引的历史记录
    :param record_idx: 历史记录索引
    :param updated_record: 更新后的记录（包含prompt/model/code）
    """
    if not os.path.exists(HISTORY_FILE):
        return False
    
    try:
        # 读取原有历史记录
        with codecs.open(HISTORY_FILE, "r", encoding="utf-8") as f:
            file_content = f.read().strip()
            if not file_content:
                return False
            if file_content.startswith('\ufeff'):
                file_content = file_content[1:]
            histories = json.loads(file_content)
        
        # 验证索引有效性
        if record_idx < 0 or record_idx >= len(histories):
            return False
        
        # 更新记录（保留原时间戳，添加更新标记）
        original_record = histories[record_idx]
        updated_record["time"] = original_record.get("time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        updated_record["updated"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        histories[record_idx] = updated_record
        
        # 重新写入文件
        with codecs.open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(histories, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"更新历史记录失败：{str(e)}")
        return False