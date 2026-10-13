"""Track spatial padding separately from generated canvas expansion; single Qwen pass."""
import json
import torch.nn.functional as F
import comfy.utils


def resize(image, w, h):
    if image.shape[1:3] == (h, w):
        return image
    return comfy.utils.common_upscale(image.movedim(-1, 1), w, h, 'lanczos', 'disabled').movedim(1, -1)


def geometry(w, h, longest, headroom):
    scale = longest / max(w, h) if longest else 1.0
    cw, ch = max(1, round(w*scale)), max(1, round(h*scale))
    ih = max(1, round(ch / (1 + headroom/100)))
    iw = max(1, round(cw * ih / ch))
    pw, ph = ((cw+31)//32)*32, ((ch+31)//32)*32
    return dict(original_width=w, original_height=h, canvas_width=cw, canvas_height=ch,
                inner_width=iw, inner_height=ih, inner_left=(cw-iw)//2, inner_top=ch-ih,
                padded_width=pw, padded_height=ph, left=(pw-cw)//2, top=(ph-ch)//2,
                headroom=headroom)


class PrepareCanvas:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'prompt': ('STRING', {'forceInput': True}),
                'generation_long_edge': ('INT', {'default':1440, 'min':0, 'max':4096, 'step':32,
                    'tooltip':'0 为原始像素尺寸；1440 与原工作流长边接近。'}),
                'headroom_percent': ('FLOAT', {'default':0, 'min':0, 'max':30, 'step':1,
                    'tooltip':'0 保持构图；10 在头顶留空间，人物略缩小，由同一次Qwen生成补全。'})}}
    RETURN_TYPES=('IMAGE','HAJI_CANVAS_MAP','STRING','STRING')
    RETURN_NAMES=('Qwen底图','尺寸还原记录','一采提示词','尺寸说明')
    FUNCTION='run'
    CATEGORY='哈基简/尺寸与扩图'
    def run(self,image,prompt,generation_long_edge,headroom_percent):
        if image.shape[0] != 1:
            raise ValueError('本工作流一次处理一张底图，避免Qwen只读取批次首帧。')
        h,w=image.shape[1:3]
        m=geometry(w,h,generation_long_edge,headroom_percent)
        img=resize(image[:,:,:,:3],m['inner_width'],m['inner_height']).movedim(-1,1)
        l,t=m['inner_left'],m['inner_top']
        img=F.pad(img,(l,m['canvas_width']-m['inner_width']-l,t,0),mode='replicate')
        l,t=m['left'],m['top']
        img=F.pad(img,(l,m['padded_width']-m['canvas_width']-l,t,m['padded_height']-m['canvas_height']-t),mode='replicate')
        if headroom_percent:
            prompt += ('\nCanvas completion: image1 has temporary stretched edge pixels in its upper '
                       'and side margins. Replace these placeholders with coherent generated background. '
                       'Complete the transferred hairstyle and crown naturally inside the available headroom. '
                       'Preserve the smaller subject placement and pose inside image1. Do not crop the top '
                       'of the head, duplicate faces, or preserve stretched edge artifacts.')
        report=f'原图 {w}×{h} → 生成 {m["padded_width"]}×{m["padded_height"]} → 输出 {w}×{h}。头顶留白 {headroom_percent}%。尺寸修复不等于语义位置锁定。'
        return img.movedim(1,-1),m,prompt,report


class RestoreCanvas:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'generated':('IMAGE',),'reference':('IMAGE',),'canvas_map':('HAJI_CANVAS_MAP',)}}
    RETURN_TYPES=('IMAGE','STRING')
    RETURN_NAMES=('原图尺寸结果','还原说明')
    FUNCTION='run'
    CATEGORY='哈基简/尺寸与扩图'
    def run(self,generated,reference,canvas_map):
        m=canvas_map
        if reference.shape[1:3] != (m['original_height'],m['original_width']):
            raise ValueError('尺寸记录和原始参考图不匹配。请连接同一张底图。')
        if generated.shape[1:3] != (m['padded_height'],m['padded_width']):
            raise ValueError('生成尺寸与记录不匹配。请保持Qwen resolution=0，采样latent接编码器输出。')
        l,t=m['left'],m['top']
        crop=generated[:,t:t+m['canvas_height'],l:l+m['canvas_width'],:]
        result=resize(crop,m['original_width'],m['original_height'])
        return result, json.dumps({'输出宽':result.shape[2],'输出高':result.shape[1],
            '处理':'仅去除32倍数对齐补边，并按记录恢复原图尺寸；保留生成的头顶扩图。',
            '局限':'不会识别或修复模型造成的局部头部错位；未使用原图头部覆盖生成结果。'},ensure_ascii=False)

NODE_CLASS_MAPPINGS={'HajiPrepareCanvas':PrepareCanvas,'HajiRestoreCanvas':RestoreCanvas}
NODE_DISPLAY_NAME_MAPPINGS={'HajiPrepareCanvas':'哈基简 · 一采画布 / 头顶扩图', 'HajiRestoreCanvas':'哈基简 · 精确还原原图尺寸'}
