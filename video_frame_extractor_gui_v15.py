#!/usr/bin/env python3
"""
视频笔记关键帧提取工具 - GUI 版本
使用批处理文件调用 ffmpeg 以避免路径问题
支持自动检测 Obsidian 当前打开的 Markdown 文档
"""

import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


def find_ffmpeg():
    """查找 ffmpeg 可执行文件"""
    try:
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            paths = result.stdout.strip().split('\n')
            for p in paths:
                if Path(p).exists():
                    return p
    except:
        pass
    
    default_paths = [
        r"C:\Users\MDSNALW\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    
    for path in default_paths:
        if Path(path).exists():
            return path
    
    return None


def resource_path(relative_path):
    """获取资源文件的真实路径，兼容 PyInstaller onefile 打包"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


class VideoFrameExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 视频笔记关键帧提取工具")
        self.root.geometry("750x520")
        
        self.default_obsidian_root = r"D:\Obsidian\MyIOTO"
        self.ffmpeg_exe = find_ffmpeg()
        self.auto_detect_success = False
        
        if not self.ffmpeg_exe:
            messagebox.showerror("错误", "未找到 ffmpeg，请确保已安装 ffmpeg")
            root.quit()
            return
        
        print(f"使用 ffmpeg: {self.ffmpeg_exe}")
        self.create_widgets()
        
        # 启动时自动计算图片文件夹编号
        self._update_folder_number()
        
        # 延迟启动自动检测，避免与UI初始化冲突
        self.root.after(500, self.auto_detect_obsidian_file)
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        ttk.Label(main_frame, text="🎬 视频笔记关键帧提取工具", 
                  font=("Microsoft YaHei UI", 16, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 视频文件
        ttk.Label(main_frame, text="视频文件路径:", font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky=tk.W, pady=10)
        self.video_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.video_path_var, width=65).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=10, padx=(10, 0))
        ttk.Button(main_frame, text="浏览...", command=self.browse_video).grid(row=1, column=2, padx=(10, 0))
        
        # 笔记文件
        ttk.Label(main_frame, text="笔记文件路径:", font=("Microsoft YaHei UI", 10)).grid(row=2, column=0, sticky=tk.W, pady=10)
        self.note_path_var = tk.StringVar()
        note_frame = ttk.Frame(main_frame)
        note_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=10, padx=(10, 0))
        note_frame.columnconfigure(0, weight=1)
        ttk.Entry(note_frame, textvariable=self.note_path_var, width=55).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(note_frame, text="自动检测", command=self.auto_detect_obsidian_file).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(main_frame, text="浏览...", command=self.browse_note).grid(row=2, column=2, padx=(10, 0))
        
        # 状态提示标签
        self.status_label = ttk.Label(main_frame, text="", font=("Microsoft YaHei UI", 9))
        self.status_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        # Obsidian 根目录
        ttk.Label(main_frame, text="Obsidian 根目录:", font=("Microsoft YaHei UI", 10)).grid(row=3, column=0, sticky=tk.W, pady=10)
        self.obsidian_root_var = tk.StringVar(value=self.default_obsidian_root)
        ttk.Entry(main_frame, textvariable=self.obsidian_root_var, width=65).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=10, padx=(10, 0))
        ttk.Button(main_frame, text="浏览...", command=self.browse_obsidian).grid(row=3, column=2, padx=(10, 0))
        
        # 图片文件夹名称（自动计算）
        ttk.Label(main_frame, text="图片文件夹:", font=("Microsoft YaHei UI", 10)).grid(row=4, column=0, sticky=tk.W, pady=10)
        self.folder_name_var = tk.StringVar(value="video1")
        ttk.Entry(main_frame, textvariable=self.folder_name_var, width=65, state='readonly').grid(row=4, column=1, sticky=(tk.W, tk.E), pady=10, padx=(10, 0))
        
        # 说明
        info = """💡 使用说明：
1. 选择视频文件和笔记文件（或点击"自动检测"从 Obsidian 获取当前文档）
2. 设置 Obsidian 根目录
3. 图片将保存到: {Obsidian根}/images/{videoN}/
4. 点击"开始提取"
        """
        ttk.Label(main_frame, text=info, font=("Microsoft YaHei UI", 9), foreground="gray").grid(row=5, column=0, columnspan=3, pady=20)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=500, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=3, pady=10)
        
        # 状态
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=3, pady=10)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=20)
        ttk.Button(btn_frame, text="🚀 开始提取", command=self.start_extraction, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ 取消", command=self.root.quit, width=15).pack(side=tk.LEFT, padx=10)
        
        main_frame.columnconfigure(1, weight=1)
        
    def browse_video(self):
        filename = filedialog.askopenfilename(title="选择视频文件", filetypes=[("MP4", "*.mp4"), ("所有", "*.*")])
        if filename:
            self.video_path_var.set(filename)
    
    def browse_note(self):
        filename = filedialog.askopenfilename(title="选择笔记文件", filetypes=[("Markdown", "*.md"), ("所有", "*.*")])
        if filename:
            self.note_path_var.set(filename)
    
    def browse_obsidian(self):
        dirname = filedialog.askdirectory(title="选择 Obsidian 根目录")
        if dirname:
            self.obsidian_root_var.set(dirname)
            # 自动递增视频文件夹编号
            self._update_folder_number()
    
    def _update_folder_number(self):
        """根据已存在的 video 文件夹自动递增编号"""
        if not Path(self.obsidian_root_var.get()).exists():
            return
        images_dir = Path(self.obsidian_root_var.get()) / "images"
        if not images_dir.exists():
            self.folder_name_var.set("video1")
            return

        # 查找所有 videoN 格式的文件夹（无空格）
        max_num = 0
        for item in images_dir.iterdir():
            if item.is_dir() and re.match(r'^video(\d+)$', item.name, re.IGNORECASE):
                match = re.match(r'^video(\d+)$', item.name, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

        self.folder_name_var.set(f"video{max_num + 1}")
    
    def auto_detect_obsidian_file(self):
        """自动检测 Obsidian 当前打开的 Markdown 文件并填充路径"""
        try:
            # 导入自动检测模块
            from auto_detect_obsidian import auto_detect_obsidian_file
            
            # 先尝试直接检测
            detected_path = auto_detect_obsidian_file()
            if detected_path:
                self.root.after(100, lambda: self._insert_detected_path(detected_path))
                return

            # 如果直接检测失败，尝试使用快捷键复制路径
            self.root.after(200, self._try_copy_path_via_keyboard_shortcut)
        except Exception as e:
            # 显示错误提示
            self.root.after(100, lambda: self._show_auto_detect_status(f"自动检测失败: {str(e)}", "red"))
            pass
    
    def _try_copy_path_via_keyboard_shortcut(self):
        """使用快捷键复制 Obsidian 文档路径"""
        try:
            import pyautogui
            import pygetwindow as pgw
            import time

            # 查找 Obsidian 窗口
            obsidian_windows = pgw.getWindowsWithTitle('Obsidian')
            if not obsidian_windows:
                self.root.after(50, lambda: self._show_auto_detect_status("未找到 Obsidian 窗口", "orange"))
                return

            # 获取最前端的 Obsidian 窗口
            active_window = None
            for win in obsidian_windows:
                if win.isActive:
                    active_window = win
                    break

            if not active_window:
                self.root.after(50, lambda: self._show_auto_detect_status("未找到活动的 Obsidian 窗口", "orange"))
                return

            # 确保 Obsidian 窗口在前台（不窃取焦点）
            # 模拟快捷键 Alt+Ctrl+K 复制路径
            pyautogui.PAUSE = 0.1
            pyautogui.hotkey('alt', 'ctrl', 'k')

            # 等待剪贴板更新
            time.sleep(0.5)

            # 从剪贴板获取路径
            try:
                clipboard_content = self.root.clipboard_get()
                if clipboard_content and clipboard_content.endswith('.md'):
                    self.root.after(100, lambda: self._insert_detected_path(clipboard_content.strip()))
                    return
            except:
                pass

            # 剪贴板为空或无效，尝试其他方法
            self.root.after(50, lambda: self._show_auto_detect_status("快捷键检测失败", "orange"))

        except ImportError:
            # pyautogui 不可用，尝试其他方式
            self.root.after(50, lambda: self._show_auto_detect_status("缺少 pyautogui 模块", "orange"))
        except Exception as e:
            self.root.after(50, lambda: self._show_auto_detect_status(f"快捷键检测失败: {str(e)}", "red"))
            pass
    
    def _insert_detected_path(self, path):
        """插入检测到的路径并显示成功提示"""
        try:
            # 清空当前内容并插入检测到的路径
            self.note_path_var.set(path)
            self._show_auto_detect_status(f"✓ 已自动识别: {os.path.basename(path)}", "green")
            self.auto_detect_success = True
        except Exception as e:
            self._show_auto_detect_status(f"插入路径失败: {str(e)}", "red")
    
    def _show_auto_detect_status(self, message, color):
        """显示自动检测状态"""
        try:
            self.status_label.config(text=message, foreground=color)
            # 3秒后清除提示
            self.root.after(3000, lambda: self.status_label.config(text=""))
        except Exception:
            pass
    
    def extract_time_ranges(self, note_path):
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 允许时间戳范围内有空白字符，如 "00:00 - 00:28"
        pattern = r'(\d{1,2}:\d{2})\s*-\s*\d{1,2}:\d{2}'
        matches = re.findall(pattern, content)
        seen = set()
        timestamps = []
        for ts in matches:
            if ts not in seen:
                seen.add(ts)
                timestamps.append(ts)
        return timestamps
    
    def extract_frame(self, video_path, timestamp_str, output_path):
        """提取帧 - 使用 shell=True 确保兼容性"""
        parts = timestamp_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        # 转换为秒数，避免 HH:MM:SS 格式在某些视频上的问题
        total_seconds = hours * 60 + minutes

        try:
            # 使用 shell=True 确保跨平台兼容性，特别是处理中文路径和特殊字符
            # 使用秒数而不是 HH:MM:SS 格式，避免某些视频的 seek 问题
            # 使用 -pix_fmt yuvj420p 解决 HEVC 非全范围 YUV 视频编码为 MJPEG 的问题
            cmd = (
                f'"{self.ffmpeg_exe}" -ss "{total_seconds}" '
                f'-i "{video_path}" -t 00:00:01 -vframes 1 '
                f'-pix_fmt yuvj420p -qscale:v 2 -y "{output_path}"'
            )

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and output_path.exists():
                size = output_path.stat().st_size
                if size > 1000:
                    print(f"  成功: {output_path} ({size} bytes)")
                    return True

            if result.returncode != 0:
                print(f"  FFmpeg 错误 (code {result.returncode})")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:200]}")

            return False
        except Exception as e:
            print(f"  异常: {e}")
            return False
    
    def start_extraction(self):
        video_path = self.video_path_var.get().strip()
        note_path = self.note_path_var.get().strip()
        obsidian_root = self.obsidian_root_var.get().strip()
        folder_name = self.folder_name_var.get()
        
        if not video_path or not note_path or not obsidian_root:
            messagebox.showerror("错误", "请填写所有路径")
            return
        
        if not Path(video_path).exists():
            messagebox.showerror("错误", f"视频文件不存在:\n{video_path}")
            return
        if not Path(note_path).exists():
            messagebox.showerror("错误", f"笔记文件不存在:\n{note_path}")
            return
        if not Path(obsidian_root).exists():
            messagebox.showerror("错误", f"Obsidian 根目录不存在:\n{obsidian_root}")
            return
        
        timestamps = self.extract_time_ranges(note_path)
        print(f"找到时间戳: {timestamps}")
        
        if not timestamps:
            messagebox.showwarning("警告", "未找到时间戳，请确认笔记格式")
            return
        
        images_dir = Path(obsidian_root) / "images" / folder_name
        images_dir.mkdir(parents=True, exist_ok=True)

        note_parent = Path(note_path).parent
        # 使用 pathlib 计算相对路径，正确处理空格和特殊字符
        try:
            rel_path = images_dir.relative_to(note_parent)
        except ValueError:
            # 如果不在同一驱动器，使用绝对路径
            rel_path = images_dir
        image_base_path = str(rel_path).replace('\\', '/')
        
        print(f"图片目录: {images_dir}")
        print(f"相对路径: {image_base_path}")
        
        frames = []
        for i, ts in enumerate(timestamps, 1):
            filename = f"f{i:03d}.jpg"
            output_path = images_dir / filename
            
            self.status_var.set(f"正在提取 {ts}... ({i}/{len(timestamps)})")
            self.progress['value'] = (i / len(timestamps)) * 100
            self.root.update()
            
            print(f"正在提取 {ts} -> {output_path}")
            
            if self.extract_frame(video_path, ts, output_path):
                frames.append({'timestamp': ts, 'filename': filename})
            else:
                print(f"  失败")
        
        print(f"成功提取 {len(frames)}/{len(timestamps)} 个帧")
        
        if not frames:
            messagebox.showwarning("警告", "未成功提取任何帧")
            return
        
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        video_path_escaped = video_path.replace('\\', '/').replace(':', '%3A').replace(' ', '%20')
        
        lines = content.split('\n')
        new_lines = []
        last_section = None
        inserted = set()
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if line.startswith('## '):
                last_section = line.strip()
                inserted.clear()
            
            if '|' in line and re.search(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', line):
                ts_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*\d{1,2}:\d{2}', line)
                if ts_match:
                    ts = ts_match.group(1)
                    frame = next((f for f in frames if f['timestamp'] == ts), None)
                    
                    if frame and last_section:
                        key = (last_section, ts)
                        if key not in inserted:
                            inserted.add(key)
                            
                            insert_idx = len(new_lines) - 1
                            while insert_idx >= 0 and new_lines[insert_idx].strip() == '':
                                insert_idx -= 1
                            
                            new_lines.insert(insert_idx + 1, '')
                            new_lines.insert(insert_idx + 2, f'- [{ts}](jv://open?path={video_path_escaped}&time={ts}.000)')
                            new_lines.insert(insert_idx + 3, f'  ![时间戳 {ts}]({image_base_path}/{frame["filename"]})')
                            new_lines.insert(insert_idx + 4, '')
        
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        messagebox.showinfo("成功", f"完成！成功提取 {len(frames)}/{len(timestamps)} 个帧\n\n图片保存在: {images_dir}")
        self.status_var.set("就绪")
        self.progress['value'] = 0


def main():
    root = tk.Tk()
    # 设置窗口图标，使程序运行时任务栏显示新 logo
    try:
        root.iconbitmap(resource_path('logo.ico'))
    except Exception as e:
        print(f"设置窗口图标失败: {e}")
    app = VideoFrameExtractorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
