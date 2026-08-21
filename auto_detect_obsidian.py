#!/usr/bin/env python3
"""
Auto-detect Obsidian active file and populate Markdown path field.
"""
import re
import sys
import os
import subprocess
import tkinter as tk


def get_active_window_title():
    """获取当前活动窗口的标题"""
    # 方法1: 使用 pywin32 查找 Obsidian 窗口
    try:
        import win32gui
        import win32process

        obsidian_windows = []

        def enum_windows_callback(hwnd, results):
            """枚举所有窗口并收集 Obsidian 窗口"""
            title = win32gui.GetWindowText(hwnd)
            if 'Obsidian' in title or 'obsidian' in title.lower():
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    # 检查窗口是否可见
                    if win32gui.IsWindowVisible(hwnd):
                        results.append((hwnd, title, pid))
                except:
                    pass

        results = []
        win32gui.EnumWindows(enum_windows_callback, results)

        if results:
            # 返回第一个可见的 Obsidian 窗口标题
            return results[0][1]

    except ImportError:
        pass
    except Exception:
        pass

    # 方法2: 使用 pygetwindow（备用）
    try:
        import pygetwindow as pgw
        obsidian_windows = pgw.getWindowsWithTitle('Obsidian')
        if obsidian_windows:
            # 优先返回活动窗口，其次返回最前面的窗口
            for win in obsidian_windows:
                if win.isActive:
                    return win.title
            # 返回最前面的窗口
            return obsidian_windows[0].title
    except Exception:
        pass

    # 方法3: 使用 PowerShell（最后备用）
    try:
        ps_code = '''
Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
        [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
    }
"@
$hwnd = [Win32]::GetForegroundWindow()
$pid = 0
[Win32]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
$title = New-Object System.Text.StringBuilder 256
[Win32]::GetWindowText($hwnd, $title, $title.Capacity) | Out-Null
$title.ToString()
'''
        result = subprocess.run(
            ['powershell', '-Command', ps_code],
            capture_output=True, text=True, timeout=5, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass

    return ""


def is_obsidian_window(title):
    """检查是否为 Obsidian 窗口"""
    if not title:
        return False
    return 'Obsidian' in title or 'obsidian' in title.lower()


def extract_filename_from_title(title):
    """从窗口标题中提取文件名"""
    if not title:
        return None

    # Obsidian 标题格式示例:
    # - "文件名 - Obsidian"
    # - "文件名.md - Obsidian"
    # - "文件名 - Vault名称 - Obsidian"
    # - "文件名 - Vault名称 - Obsidian 1.12.4"
    # - "对话框 -- Obsidian #数字 ..."

    # 策略1: 移除版本号和 Obsidian 后缀
    # 先移除版本号 "1.12.4" 等
    title_clean = re.sub(r'\s*-\s*Obsidian\s+\d+\.\d+\.\d+$', ' - Obsidian', title)

    # 策略2: 匹配 "文件名 - Vault名称 - Obsidian" 格式
    match = re.match(r'^(.+?)\s*-\s*[^-]+?\s*-\s*Obsidian$', title_clean, re.IGNORECASE)
    if match:
        filename = match.group(1).strip()
        if filename.endswith('.md'):
            return filename
        return filename + '.md'

    # 策略3: 直接移除 " - Obsidian" 后缀
    for suffix in [' - Obsidian', ' -- Obsidian', ' - obsidian', ' -- obsidian']:
        if title_clean.endswith(suffix):
            filename = title_clean[:-len(suffix)].strip()
            if filename and filename.endswith('.md'):
                return filename
            elif filename:
                return filename + '.md'

    # 策略4: 匹配 "文件名 -- Obsidian #数字 ..." 格式
    match = re.match(r'^(.+?)\s*--\s*Obsidian\s+#\d+', title, re.IGNORECASE)
    if match:
        filename = match.group(1).strip()
        if filename.endswith('.md'):
            return filename
        return filename + '.md'

    # 策略5: 匹配 "文件名 - Obsidian" 格式（带可选的 .md）
    match = re.match(r'^(.+?)\s*- Obsidian', title, re.IGNORECASE)
    if match:
        filename = match.group(1).strip()
        if filename.endswith('.md'):
            return filename
        return filename + '.md'

    # 策略6: 如果标题以 .md 结尾，直接返回
    if title.strip().lower().endswith('.md'):
        return title.strip()

    # 策略7: 尝试从标题中提取 .md 文件名
    match = re.search(r'([\w\s\-\.]+\.md)', title, re.IGNORECASE)
    if match:
        return match.group(1)

    # 策略8: 如果标题不包含 "编辑动作" 等 UI 元素，尝试使用整个标题
    if '编辑动作' not in title and '对话框' not in title:
        filename = title.strip()
        if not filename.endswith('.md'):
            filename += '.md'
        return filename

    return None


def find_file_in_vault(filename, vault_paths=None):
    """在 Obsidian vault 中查找文件"""
    if vault_paths is None:
        vault_paths = get_default_vault_paths()

    # 只匹配文件名（不含路径）
    base_name = os.path.basename(filename)

    for vault_path in vault_paths:
        if not os.path.exists(vault_path):
            continue

        # 使用 faster 搜索：os.listdir 只搜索当前目录
        try:
            for item in os.listdir(vault_path):
                full_path = os.path.join(vault_path, item)
                if os.path.isfile(full_path) and item.lower() == base_name.lower():
                    return full_path

            # 如果没找到，递归搜索子目录
            for root, dirs, files in os.walk(vault_path):
                for f in files:
                    if f.lower() == base_name.lower():
                        return os.path.join(root, f)
        except Exception:
            continue

    return None


def get_default_vault_paths():
    """获取默认的 Obsidian vault 路径"""
    paths = []

    # 从环境变量获取
    vault_env = os.environ.get('OBSIDIAN_VAULT')
    if vault_env:
        paths.append(vault_env)

    # 从注册表获取（Windows）
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Obsidian\Obsidian')
        vault_path, _ = winreg.QueryValueEx(key, 'VaultPath')
        paths.append(vault_path)
        winreg.CloseKey(key)
    except Exception:
        pass

    # 常见位置
    home = os.path.expanduser('~')
    common_paths = [
        os.path.join(home, 'Obsidian'),
        os.path.join(home, 'Documents', 'Obsidian'),
        os.path.join(home, 'Obsidian Vault'),
        'D:/Obsidian/MyIOTO',  # 用户已知的 vault 路径
    ]

    for p in common_paths:
        if os.path.exists(p):
            paths.append(p)

    # 去重并保持顺序
    seen = set()
    unique_paths = []
    for p in paths:
        p_normalized = p.replace('\\', '/').lower()
        if p_normalized not in seen:
            seen.add(p_normalized)
            unique_paths.append(p)

    return unique_paths


def auto_detect_obsidian_file():
    """自动检测 Obsidian 当前打开的文件"""
    try:
        # 获取活动窗口标题
        title = get_active_window_title()
        print(f"Active window title: '{title}'", file=sys.stderr)

        if not title:
            print("No active window found", file=sys.stderr)
            return None

        if not is_obsidian_window(title):
            print(f"Window '{title}' is not Obsidian", file=sys.stderr)
            return None

        # 提取文件名
        filename = extract_filename_from_title(title)
        if not filename:
            print(f"Could not extract filename from title: '{title}'", file=sys.stderr)
            return None

        print(f"Extracted filename: '{filename}'", file=sys.stderr)

        # 在 vault 中查找
        vault_paths = get_default_vault_paths()
        print(f"Vault paths: {vault_paths}", file=sys.stderr)

        full_path = find_file_in_vault(filename, vault_paths)
        if full_path:
            print(f"Found file: '{full_path}'", file=sys.stderr)
            return full_path
        else:
            print(f"File '{filename}' not found in any vault", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error auto-detecting file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


if __name__ == '__main__':
    result = auto_detect_obsidian_file()
    if result:
        print(result)
    else:
        print("NOT_FOUND")
        sys.exit(1)
