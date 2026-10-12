# 哈基简 · ComfyUI-Hajijian

<img src="web/hajijian.svg" width="48" height="56" alt="哈基简像素女仆" />

ComfyUI 的像素女仆清理助手。右键小人，一键卸载模型并回收可释放的内存与显存。

## 功能

- 原创双马尾女仆像素角色，48 × 56 像素显示。
- 拖动移动，自动记住浏览器中的位置。
- 右键或单击打开菜单，仅提供内存与显存清理功能。
- 显示清理中状态，以及进程内存、PyTorch 显存缓存池、整卡显存的前后用量（GiB）。
- 成功后 3 秒自动关闭结果；失败提示保留。重新打开或再次清理会取消旧计时。
- 有任务运行或排队时拒绝清理，避免干扰生成。

## 安装

下载本仓库的 ZIP，解压为 `ComfyUI-Hajijian`，放入 ComfyUI 的 `custom_nodes` 文件夹。目录结构应为：

```text
ComfyUI/
└── custom_nodes/
    └── ComfyUI-Hajijian/
        ├── __init__.py
        └── web/
            ├── hajijian.js
            └── hajijian.svg
```

也可以在 `custom_nodes` 中使用本仓库页面 Code 按钮提供的 HTTPS 地址执行 `git clone`。

重启 ComfyUI，并按 Ctrl+F5 刷新页面。此插件是悬浮界面扩展，无需向工作流添加节点。

依赖 ComfyUI 环境已有的 `torch`、`aiohttp`、`psutil`，不下载额外模型。

## 使用与限制

右键（或单击）哈基简 → **清理内存与显存**。下次生成可能需要重新加载模型。

清理调用 ComfyUI 模型卸载接口、Python 垃圾回收和空闲显存缓存释放接口。不会强制结束其他程序，也不能释放仍被节点引用的对象、第三方自行管理的模型或所有执行结果缓存。没有可释放资源时数值可能不变；进程 RSS 也不一定立即下降。整卡显存包含其他程序，可能随其活动变化。

已在 Windows、NVIDIA CUDA 的 ComfyUI v0.39.0 环境验证。CPU 模式不显示 CUDA 显存数值，其他平台尚未实测。

更新后请强制刷新浏览器。卸载时关闭 ComfyUI，再移除本插件目录。

## License / 致谢

GPL-3.0，见 [LICENSE](LICENSE)。清理交互与功能参考 [kk8bit/KayTool](https://github.com/kk8bit/kaytool) 的 GuLuLu / Clean VRAM；保留来源致谢。像素女孩 SVG 和本插件界面重新设计，未使用原角色图片，未引入其他 KayTool 功能。

## English

A tiny pixel-maid companion for ComfyUI. Right-click or click the character to unload ComfyUI-managed models and reclaim unused RAM / VRAM. Drag to reposition. Successful results close after three seconds; errors remain visible. Cleanup is refused while prompts are running or queued.

Extract this repository into `ComfyUI/custom_nodes/ComfyUI-Hajijian`, restart ComfyUI, and hard-refresh the browser. No workflow node is required. Memory still referenced by nodes and externally managed models may remain allocated.
