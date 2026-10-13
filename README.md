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

重启 ComfyUI，并按 Ctrl+F5 刷新页面。像素助手无需添加节点；下方四个工作流节点可按需使用。

像素助手使用 ComfyUI 环境的 `torch`、`aiohttp`、`psutil`，不需要额外模型。新增节点的依赖和检测模型见下文。

## 使用与限制

右键（或单击）哈基简 → **清理内存与显存**。下次生成可能需要重新加载模型。

清理调用 ComfyUI 模型卸载接口、Python 垃圾回收和空闲显存缓存释放接口。不会强制结束其他程序，也不能释放仍被节点引用的对象、第三方自行管理的模型或所有执行结果缓存。没有可释放资源时数值可能不变；进程 RSS 也不一定立即下降。整卡显存包含其他程序，可能随其活动变化。

已在 Windows、NVIDIA CUDA 的 ComfyUI v0.39.0 环境验证。CPU 模式不显示 CUDA 显存数值，其他平台尚未实测。

更新后请强制刷新浏览器。卸载时关闭 ComfyUI，再移除本插件目录。


## v1.1.0：四个工作流节点

保留像素助手；以下节点用于 Qwen 等工作流的提示约束、检查和尺寸处理，不包含图像生成模型。

| 节点 ID | 界面名称 | 功能 |
|---|---|---|
| `HajiGenerativeReferenceConstraints` | 哈基简 · 整头生成约束 / 口罩处理 | 检测底图表情并追加参考约束，支持手动眼嘴状态和口罩移除生成提示 |
| `HajiBodyAudit` | 哈基简 · 身体动作核对 | 比较可见身体关节，仅输出检查文字，不修改图片 |
| `HajiPrepareCanvas` | 哈基简 · 一采画布 / 头顶扩图 | 等比缩放、补边到32倍数，记录变换；可选头顶留白 |
| `HajiRestoreCanvas` | 哈基简 · 精确还原原图尺寸 | 去除对齐补边并输出参考图的精确宽高 |

### 依赖与模型

在运行 ComfyUI 的 Python 环境安装 `requirements.txt`。Windows 便携版可在便携版根目录执行（按实际插件目录名称调整）：

```powershell
.\python_embeded\python.exe -m pip install -r .\ComfyUI\custom_nodes\ComfyUI-Hajijian\requirements.txt
```

使用现有 ComfyUI 的 PyTorch，不需要为本插件重装 CUDA 或 PyTorch。MediaPipe 用于表情检测和身体核对。画布节点不使用 MediaPipe 模型。

将以下 MediaPipe Tasks 模型放入 `ComfyUI/models/mediapipe/`：

- `face_landmarker.task`：普通模式的表情检测。
- `pose_landmarker_lite.task`：身体动作核对。

模型需自行从 Google MediaPipe 官方模型页面取得，本仓库不打包或自动下载模型。也兼容已有 `ComfyUI_LayerStyle_Advance/face_landmarker/face_landmarker.task`。安装依赖、模型后重启 ComfyUI。

### 接线

1. 原始底图 → 生成约束节点；其提示词和同一张原始底图 → 画布准备。
2. 画布图片接 `TextEncodeQwenImage21` 的 image1，身份参考接 image2，准备后的提示词接 prompt；resolution 设为 **0**。
3. 编码器的正面、负面、latent 输出接同一个采样器，采样后 VAE 解码。
4. 解码结果、原始底图和画布准备的尺寸记录 → 尺寸还原 → 保存图片。
5. 原始底图与最终结果可接身体动作核对。文字输出可接任意 STRING 显示节点。

画布准备默认长边1440、头顶留白0。长边0表示保留原始像素尺寸（大图可能占用更多显存）。留白10会适当缩小人物占比，让同一次生成尝试补全头顶及背景。留白是生成前的边缘占位，必须经过生成模型，不能将占位图片直接作为扩图成品。

### 使用边界与兼容

- 约束是提示词，不是身份、姿态或跨帧一致性的硬保证。口罩模式使用专用提示词，遮住的真实嘴部表情未知，自动选项生成自然闭嘴。
- 尺寸还原修正缩放/补边坐标，不修复模型自己改变的头部位置，也不重新绘制图片。
- 头顶补全由外部生成模型执行，可能仍出现伪影；本插件没有额外二采。
- 画布准备一次只接收一张底图，避免 Qwen 只读取图像批次第一帧。
- 若已经安装早期 `ComfyUI-Hajijian-Retarget` / `ComfyUI-Hajijian-Canvas`，它们与本包包含同名节点。迁移当前四节点工作流时应避免重复启用；若仍使用旧的 `HajiReferenceConstraints` 工作流，请先保留旧包并另行迁移该旧节点，本版本不注册那个旧 ID。
- 仓库不包含人物素材、用户工作流或模型权重。已检查节点接口和画布还原行为，未对本次发布重新执行 Qwen 生成测试。

## License / 致谢

GPL-3.0，见 [LICENSE](LICENSE)。清理交互与功能参考 [kk8bit/KayTool](https://github.com/kk8bit/kaytool) 的 GuLuLu / Clean VRAM；保留来源致谢。像素女孩 SVG 和本插件界面重新设计，未使用原角色图片，未引入其他 KayTool 功能。

## English

A tiny pixel-maid companion for ComfyUI. Right-click or click the character to unload ComfyUI-managed models and reclaim unused RAM / VRAM. Drag to reposition. Successful results close after three seconds; errors remain visible. Cleanup is refused while prompts are running or queued.

Extract this repository into `ComfyUI/custom_nodes/ComfyUI-Hajijian`, restart ComfyUI, and hard-refresh the browser. No workflow node is required. Memory still referenced by nodes and externally managed models may remain allocated.
