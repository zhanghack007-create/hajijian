"""哈基简：手动回收 ComfyUI 管理的模型和空闲内存。"""
import gc
import logging
import psutil
import torch
from aiohttp import web
from server import PromptServer
from comfy import model_management

NODE_CLASS_MAPPINGS = {}
WEB_DIRECTORY = './web'

def memory_snapshot():
    result = {'ram': psutil.Process().memory_info().rss, 'reserved': None, 'device_used': None}
    if torch.cuda.is_available():
        device = model_management.get_torch_device()
        torch.cuda.synchronize(device)
        free, total = torch.cuda.mem_get_info(device)
        result.update(reserved=torch.cuda.memory_reserved(device), device_used=total-free)
    return result

@PromptServer.instance.routes.post('/hajijian/clean')
async def clean(request):
    queue = PromptServer.instance.prompt_queue
    # Hold the worker's queue lock through the operation so no prompt starts midway.
    with queue.mutex:
        if queue.queue or queue.currently_running:
            return web.json_response({'error': '还有任务正在运行或排队，请待任务结束后再清理。'}, status=409)
        try:
            before = memory_snapshot()
            model_management.unload_all_models()
            gc.collect()
            model_management.soft_empty_cache()
            after = memory_snapshot()
            return web.json_response({'before': before, 'after': after})
        except Exception:
            logging.exception('[哈基简] 清理失败')
            return web.json_response({'error': '清理未完成，请查看 ComfyUI 日志。'}, status=500)
