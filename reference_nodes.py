"""Append reference conditions to an unchanged Qwen head-swap prompt; never modify pixels."""
import json
from pathlib import Path
import numpy as np
import folder_paths


def landmark_model(name):
    candidates = [Path(folder_paths.models_dir) / 'mediapipe' / name]
    if name == 'face_landmarker.task':
        candidates.append(Path(folder_paths.base_path) / 'custom_nodes/ComfyUI_LayerStyle_Advance/face_landmarker' / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f'缺少 {name}，请放入 ComfyUI/models/mediapipe/。安装说明见 hajijian 仓库 README。')


def body_points(image):
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
    path=landmark_model('pose_landmarker_lite.task')
    options=vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(path)),num_poses=1)
    rgb=np.ascontiguousarray((image[0,:,:,:3].cpu().numpy().clip(0,1)*255).astype(np.uint8))
    with vision.PoseLandmarker.create_from_options(options) as detector:
        result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
    return result.pose_landmarks[0] if result.pose_landmarks else None


def reference_features(image):
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
    model=landmark_model('face_landmarker.task')
    rgb=np.ascontiguousarray((image[0,:,:,:3].cpu().numpy().clip(0,1)*255).astype(np.uint8))
    options=vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(model)),num_faces=2,output_face_blendshapes=True)
    with vision.FaceLandmarker.create_from_options(options) as detector:
        result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
    if len(result.face_landmarks)!=1:raise ValueError('无法可靠判断单人表情，请手动指定眼睛/嘴部状态；原图仍完整传入换头。')
    h,w=rgb.shape[:2]
    p=np.array([(x.x*w,x.y*h) for x in result.face_landmarks[0]])
    gap=float(np.linalg.norm(p[13]-p[14])/max(np.linalg.norm(p[61]-p[291]),1))
    return {x.category_name:float(x.score) for x in result.face_blendshapes[0]},gap


class ReferenceConstraints:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'base':('IMAGE',),'original_prompt':('STRING',{'multiline':True}),
                'eyes':(['自动','闭眼','睁眼'],),'mouth':(['自动','闭嘴','张嘴'],)}}
    RETURN_TYPES=('STRING','STRING')
    RETURN_NAMES=('原提示词加参考约束','参考状态说明')
    FUNCTION='run'
    CATEGORY='哈基简/原版换头参考约束'
    def run(self,base,original_prompt,eyes,mouth):
        try:
            b,gap=reference_features(base)
            blink=max(b.get('eyeBlinkLeft',0),b.get('eyeBlinkRight',0))
            down=max(b.get('eyeLookDownLeft',0),b.get('eyeLookDownRight',0))
            closed=blink>.65 or (blink>.4 and down>.55)
            eye_text='Both eyes fully CLOSED, eyelids touching, no visible pupils, iris or eye whites.' if closed else 'Precisely retain image1 eyelid opening and gaze.'
            mouth_text='Lips closed with no visible teeth.' if gap<.01 else 'Keep exactly image1 mouth opening, visible teeth and lip tension.'
            report={'eye_blink_estimate':blink,'look_down_estimate':down,'mouth_gap_estimate':gap}
        except ValueError as e:
            eye_text='Copy exactly image1 eyelid opening and gaze.'
            mouth_text='Copy exactly image1 mouth opening and lip tension.'
            report={'detection_warning':str(e)}
        if eyes=='闭眼':eye_text='Both eyes fully CLOSED, eyelids touching, no visible pupils, iris or eye whites.'
        if eyes=='睁眼':eye_text='Eyes open, preserving the gaze direction of image1.'
        if mouth=='闭嘴':mouth_text='Lips closed with no visible teeth.'
        if mouth=='张嘴':mouth_text='Mouth open as in image1, preserving its visible teeth and lip shape.'
        extra=('\n\nMandatory reference constraints: '+eye_text+' '+mouth_text+
               ' Image2 supplies head identity and hairstyle ONLY, not its facial expression or head pose. '
               'Precisely match image1 head yaw, pitch, roll, gaze and head position relative to the neck. '
               'Keep image1 body silhouette, shoulder angle, elbow and wrist positions, hands, fingers, body lean and all limb poses unchanged. '
               'Keep image1 clothing, background and all printed text unchanged. Match the new head skin tone and lighting to image1 neck and body. '
               'Do not straighten a tilted head or open closed eyes. '+eye_text+' '+mouth_text)
        report.update(eyes=eyes,mouth=mouth,eye_instruction=eye_text,mouth_instruction=mouth_text,
                      limitation='仅增强参考条件，不是ControlNet硬约束；不裁图、不生成蒙版、不回贴，仍须检查输出。')
        return original_prompt+extra,json.dumps(report,ensure_ascii=False,indent=2)

class BodyAudit:
    @classmethod
    def INPUT_TYPES(cls):return {'required':{'reference':('IMAGE',),'result':('IMAGE',)}}
    RETURN_TYPES=('STRING',)
    FUNCTION='run'
    CATEGORY='哈基简/原版换头参考约束'
    def run(self,reference,result):
        a,b=body_points(reference),body_points(result)
        shifts=[]
        if a and b:
            for i in (11,12,13,14,15,16,23,24,25,26,27,28):
                if min(a[i].visibility,b[i].visibility)>.6:
                    shifts.append({'joint':i,'normalized_shift':float(np.hypot(a[i].x-b[i].x,a[i].y-b[i].y))})
        text='检测到的可见关节不足，请人工核对' if len(shifts)<3 else ('关节检测提示可能偏移，请看对照图；遮挡时也可能误检' if max(x['normalized_shift'] for x in shifts)>.04 else '检测到的可见关节偏移在4%画幅阈值内，仍需人工核对')
        return (json.dumps({'joints':shifts,'result':text,'note':'这是姿态检测估计，不是像素一致性或头部表情合格保证。'},ensure_ascii=False,indent=2),)

NODE_CLASS_MAPPINGS={'HajiBodyAudit':BodyAudit}
NODE_DISPLAY_NAME_MAPPINGS={'HajiBodyAudit':'哈基简 · 身体动作核对'}



class GenerativeReferenceConstraints(ReferenceConstraints):
    @classmethod
    def INPUT_TYPES(cls):
        spec = super().INPUT_TYPES()
        spec['required']['occlusion'] = (['普通换头', '移除口罩并生成面部'],)
        return spec

    def run(self, base, original_prompt, eyes, mouth, occlusion):
        if occlusion == '普通换头':
            return super().run(base, original_prompt, eyes, mouth)
        # A covered mouth has no observable expression. Do not treat inferred
        # face landmarks through a mask as a measured mouth opening.
        eye = 'Preserve the visible eyelid opening and gaze from image1.'
        if eyes == '闭眼': eye = 'Keep both eyes closed, no visible pupils.'
        if eyes == '睁眼': eye = 'Keep eyes open and preserve image1 gaze direction.'
        mouth_instruction = 'Generate relaxed, naturally closed lips, consistent with image2 identity.'
        if mouth == '张嘴': mouth_instruction = 'Generate a naturally slightly open mouth consistent with image2 identity.'
        instruction = (
            'Edit image1 using image2 as the full head identity and hairstyle reference. '
            'Replace the entire head identity, including facial structure, ears and hairstyle. '
            'Remove the face mask and its straps completely. Generate the missing nose, cheeks, '
            'mouth and chin according to image2 identity, with coherent facial anatomy. '
            'The hidden mouth expression in image1 is unknown; do not copy the mask shape or '
            'invent expression measurements through the mask. '
            + eye + ' ' + mouth_instruction +
            ' Preserve image1 head yaw, pitch, roll and neck alignment, visible expression cues, '
            'body pose, hands, clothing, background and text. Match facial skin color and '
            'illumination to image1 neck and body. Generate a complete uncovered face.'
        )
        report = {'mode': occlusion, 'mouth': mouth, 'eyes': eyes,
                  'note': '遮挡模式不使用口罩下的嘴部检测；按身份参考生成，自动嘴型为自然闭嘴。此模式使用专用生成提示词。'}
        return instruction, json.dumps(report, ensure_ascii=False, indent=2)

NODE_CLASS_MAPPINGS['HajiGenerativeReferenceConstraints'] = GenerativeReferenceConstraints
NODE_DISPLAY_NAME_MAPPINGS['HajiGenerativeReferenceConstraints'] = '哈基简 · 整头生成约束 / 口罩处理'
