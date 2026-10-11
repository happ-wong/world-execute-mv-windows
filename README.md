# world.execute(me); —ascii（Windows 版）

![world.execute(me);](docs/images/mv-cover.png)

Mili《world.execute(me);》的终端字符动画，从 macOS 单文件播放包移植到 Windows。中英字幕、原曲同步播放、频谱与分镜动画全部沿用原项目，画面代码逐帧一致。

## 单文件运行（需要 Python 3.9+）

音乐、动画、字幕、频谱数据和 Windows 音频引擎都已内嵌在 `world-execute-mv-win.pyz` 里，不用再准备 MP3。

需要 **Windows 10 或更新版本、Python 3.9 或更新版本**。播放器本身只用 Python 标准库，声音由系统自带的 Media Foundation 播放。

直接 **双击 `全屏播放.cmd`**（推荐）：用 Windows Terminal 真全屏打开，没有标题栏和任务栏。也可以双击 `运行单文件.cmd` 在当前终端窗口里播放，或手动执行：

```bat
py -3 world-execute-mv-win.pyz
```

按空格开始。终端至少 64 列 × 24 行，120 列 × 40 行以上效果更好。

```bat
:: 从 2:38.7 直接开始播
py -3 world-execute-mv-win.pyz --start 158.7 --autoplay
```

内嵌音乐是随程序封装的资源，不是加密或 DRM。运行时解包到当前用户的临时目录，退出后清理（`%TEMP%\world-execute-mv-*`），全程不联网。

## 操作

| 按键 | 功能 |
| --- | --- |
| 空格 / 回车 | 开始／暂停 |
| 左／右 | 后退／前进 5 秒 |
| 1–5 | 跳转章节 |
| , / . | 上一句 / 下一句 |
| [ / ] | 字幕提前 / 延后 0.1 秒 |
| + / - | 音量 |
| R | 从头播放 |
| H | 帮助 |
| Q / ESC | 退出 |

## 与 macOS 版的差异

音频引擎换了实现，其余（渲染、字幕、频谱、分镜、按键、协议）完全相同。

macOS 版把音频时钟做成一个 AVFoundation 子进程 `audio-clock`，通过 JSON 行协议驱动画面。Windows 上对应的位置是 winmm/MCI 的 `MPEGVideo` 设备，但它注册的是 `mciqtz32.dll`——依赖早已从 Windows 中移除的 QuickTime，实测 `open` 直接返回错误 277，放不了 MP3。

所以 Windows 版换成 **PowerShell + WPF MediaPlayer（Media Foundation）** 作为子进程音频引擎 `audio-clock.ps1`，说的是同一套协议：`play` / `pause` / `seek <秒>` / `volume <0..1>` / `quit`，回 `{"time","duration","playing"}`。Python 侧只有 `make_audio()` 按平台拼启动命令，播放逻辑一行没改。

实测精度：时钟速率 1.00x，暂停/恢复/跳转后与真实播放进度偏差在 ±60ms 内，起播瞬间约 50ms 的启动延迟（听感上画面几乎与声音同时）。

其他 Windows 适配：

- 输入用 `msvcrt`（`kbhit` + `getwch`），方向键的 `\xe0` 扩展码翻译成 `\x1b[C/D`，解析分支与 macOS 共用。
- 输出走 `sys.stdout.reconfigure(encoding='utf-8')` 并给 conhost 打开 VT 处理模式；同时关掉 QuickEdit，避免鼠标误点把渲染循环卡住。
- 资源读取固定 UTF-8（Windows 默认 GBK，中文字幕会直接解码失败）。
- `/dev/tty`、`SIGHUP`、`chmod 0o755` 这些 POSIX 专属调用都做了平台分支。

## 音画不同步怎么调

- `[` / `]`：只挪字幕，每次 0.1 秒。
- `--audio-latency 0.05`：整体把画面往后压，补偿输出设备延迟（蓝牙耳机、HDMI 音响建议试 0.05～0.15）。
- `--fps 30`：高刷屏可以更顺；性能不够就 `--fps 15`。

## 常见问题

**提示找不到 Python**：`winget install -e --id Python.Python.3.12`，重新打开启动器。

**双击后窗口一闪而过**：用 `运行单文件.cmd`（出错会停住等你按键），或在终端里手动执行看报错。

**没有声音 / 报 media failed**：Windows N 版缺少媒体功能包，装 “Media Feature Pack”；或换 `--audio` 指定一个本地 MP3 试试。

**被组策略禁用 PowerShell 脚本**：`audio-clock.ps1` 通过 `powershell -ExecutionPolicy Bypass -File` 启动，机器级 `Restricted` 策略可能拦截；在终端里手动运行可以看到具体错误。

**画面错位、有重影**：换 Windows Terminal 或 Windows 11 终端；传统 conhost 的字号缩放会破坏 2 格宽汉字的对齐。

## 从源码运行与重新打包

源码在上一级目录的 `source/`：

```bat
cd source
py -3 src\player.py                        :: 直接跑源码
py -3 tools\build_bundle.py                :: 重新打包 dist\world-execute-mv-win.pyz
py -3 tests\test_bundle.py                 :: 校验包内容与 SHA-256
py -3 tests\test_audio_clock.py            :: 音频时钟：速率、跳转、暂停、句柄释放
py -3 tests\test_playback_loop.py          :: 完整播放循环（脚本化按键，无声渲染）
py -3 tools\render_frames.py               :: 把若干帧渲染成 PNG，方便肉眼核对
```

`bundle-manifest.json` 记录每个资源的 SHA-256，启动时逐个校验；`audio-clock.ps1` 与 `.cmd` 启动器保持纯 ASCII，因为 PowerShell 5.1 和 cmd.exe 对无 BOM 的多字节脚本会读错位。

## 收录范围与版权

动画、字幕、频谱数据与打包协议来自原 macOS 项目 `world-execute-mv`，本仓库只做 Windows 移植：新增 `audio-clock.ps1`、跨平台输入/输出层、Windows 打包脚本，渲染与分镜代码未改动。移植部分的实现与脚本以同样方式开放。

原曲与歌词：Mili《world.execute(me);》。音频仅内嵌于本机播放包，不构成对原曲、歌词或任何第三方素材的授权。
