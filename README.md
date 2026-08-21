# 视频笔记关键帧提取工具

一个用于从视频中提取关键帧并自动添加到 Obsidian 笔记的 GUI 工具。适用于 B 站视频学习笔记整理，可快速将视频关键帧与时间戳链接关联。

## 功能特点

- **一键提取关键帧**：根据笔记中的时间戳范围自动提取视频帧
- **Obsidian 集成**：自动保存图片并生成带时间戳的链接
- **PotPlayer 跳转**：生成的链接支持 `jv://` 协议，点击可跳转到指定时间点
- **智能文件夹管理**：自动递增命名（video1、video2、video3...）
- **中文路径支持**：正确处理含空格和特殊字符的路径
- **进度显示**：实时显示提取进度和状态

## 环境要求

- Python 3.7+
- ffmpeg（需安装并加入系统 PATH）
- Windows 系统

## 安装

1. 克隆或下载本项目
2. 确保已安装 ffmpeg：
   ```bash
   # Winget 安装
   winget install Gyan.FFmpeg
   
   # 或手动下载安装后添加到系统 PATH
   ```
3. 运行脚本：
   ```bash
   python video_frame_extractor_gui_v14.py
   ```

## 使用方法

### 1. 准备笔记文件

在 Obsidian 笔记中使用表格记录时间戳，格式如下：

```markdown
## 章节标题

| 时间范围 | 内容说明 |
|----------|----------|
| 00:21-00:45 | 这是第一段内容 |
| 01:30-02:15 | 这是第二段内容 |
```

### 2. 运行工具

1. 选择视频文件（MP4 等格式）
2. 选择笔记文件（.md）
3. 设置 Obsidian 根目录（默认：`D:\Obsidian\MyIOTO`）
4. 点击"开始提取"

### 3. 查看结果

- 图片保存位置：`{Obsidian根}/images/{videoN}/`
- 笔记中自动添加时间戳链接和图片：

```markdown
- [00:21](jv://open?path=C:/视频/xxx.mp4&time=00:21.000)
  ![时间戳 00:21](images/video1/f001.jpg)
```

## 技术细节

### 时间戳提取逻辑

- 支持 `MM:SS` 格式（如 `00:21`）
- 自动去重，保持原有顺序
- 识别表格中的时间范围格式

### 帧提取参数

```bash
ffmpeg -ss {秒数} -i "视频路径" -t 00:00:01 -vframes 1 \
       -pix_fmt yuvj420p -qscale:v 2 -y "输出路径"
```

- `-pix_fmt yuvj420p`：解决 HEVC 视频编码问题
- `-qscale:v 2`：高质量输出
- 使用 `shell=True` 确保跨平台兼容性

### jv:// 协议

生成的链接使用 PotPlayer 的自定义协议，可在 Obsidian 中直接点击跳转到视频指定时间点。

## 常见问题

**Q: 提示未找到 ffmpeg？**
A: 确保 ffmpeg 已安装并加入系统 PATH，或手动指定路径。

**Q: 提取失败或图片损坏？**
A: 检查视频文件是否损坏，或尝试更新 ffmpeg 版本。

**Q: 时间戳未识别？**
A: 确认笔记格式为表格，且时间戳格式为 `MM:SS-MM:SS`。

## 许可证

MIT License

## 更新日志

### v1.4
- 修复路径空格问题
- 优化 HEVC 视频支持
- 改进文件夹自动命名逻辑

---

**作者**：Agnes  
**项目仓库**：[GitHub](https://github.com/your-username/TimeStampFormatter)
