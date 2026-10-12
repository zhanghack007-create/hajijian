import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';

app.registerExtension({
  name: 'Hajijian.Clean',
  setup() {
    if (document.getElementById('hajijian')) return;
    const style = document.createElement('style');
    style.textContent = `
      #hajijian{position:fixed;z-index:1001;left:90px;bottom:100px;font:14px/1.6 "Microsoft YaHei",sans-serif;color:#173e39}
      #hajijian .pet{display:block;width:48px;height:56px;padding:0;border:0;background:transparent;cursor:grab;touch-action:none}
      #hajijian .pet img{width:48px;height:56px;image-rendering:pixelated;pointer-events:none;animation:haji-breathe 2.5s steps(2) infinite}
      #hajijian .panel{position:absolute;bottom:60px;left:0;width:min(310px,calc(100vw - 24px));box-sizing:border-box;background:#effbf2;border:3px solid #173e39;border-radius:12px;padding:16px;box-shadow:4px 4px 0 #173e3960}
      #hajijian .panel[hidden]{display:none}
      #hajijian .clean{width:100%;background:#173e39;color:#fff;border:0;border-radius:6px;padding:10px;cursor:pointer;font:inherit}
      #hajijian .close{float:right;border:0;background:none;color:#173e39;cursor:pointer;font-size:20px}
      #hajijian .message{white-space:pre-line;margin:8px 0 0;font-variant-numeric:tabular-nums}
      #hajijian .note{font-size:12px;opacity:.75;margin-top:8px}
      #hajijian.busy img{animation:haji-sweep .3s steps(2) infinite}
      @keyframes haji-breathe{50%{transform:translateY(-2px)}}
      @keyframes haji-sweep{50%{transform:translateX(2px)}}
      @media(prefers-reduced-motion:reduce){#hajijian .pet img{animation:none}}
    `;
    document.head.append(style);
    const root = document.createElement('div'); root.id = 'hajijian';
    root.innerHTML = `<button class="pet" aria-label="哈基简，右键清理内存与显存" title="哈基简 · 拖动移动，右键清理"><img alt="哈基简" src="${new URL('./hajijian.svg?v=2', import.meta.url)}"></button><section class="panel" hidden aria-label="哈基简清理工具"><button class="close" aria-label="关闭哈基简菜单">×</button><strong>哈基简 · 清扫一下</strong><button class="clean">🧹 清理内存与显存</button><div class="message" role="status" aria-live="polite"></div><div class="note">卸载模型并回收空闲缓存，下次运行会重新加载模型。</div></section>`;
    document.body.append(root);
    const pet = root.querySelector('.pet'), panel = root.querySelector('.panel');
    const clean = root.querySelector('.clean'), message = root.querySelector('.message');
    let busy = false, drag = null, moved = false, closeTimer = null;
    function fit() {
      const r = root.getBoundingClientRect();
      root.style.left = `${Math.max(12, Math.min(r.left, innerWidth - 60))}px`;
      root.style.top = `${Math.max(12, Math.min(r.top, innerHeight - 68))}px`;
      root.style.bottom = 'auto';
      const x = parseFloat(root.style.left), y = parseFloat(root.style.top);
      panel.style.left = `${Math.min(0, innerWidth - x - 334)}px`;
      panel.style.bottom = y < 300 ? 'auto' : '60px';
      panel.style.top = y < 300 ? '60px' : 'auto';
    }
    try { const p = JSON.parse(localStorage.getItem('hajijian.position')); if(p && Number.isFinite(p.x) && Number.isFinite(p.y)){root.style.left=p.x+'px';root.style.top=p.y+'px';root.style.bottom='auto';} } catch {}
    fit(); window.addEventListener('resize', fit);
    pet.addEventListener('pointerdown', e => {if(e.button!==0)return; moved=false; const r=root.getBoundingClientRect();drag={x:e.clientX,y:e.clientY,left:r.left,top:r.top};pet.setPointerCapture(e.pointerId);});
    pet.addEventListener('pointermove', e => {if(!drag)return; const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;root.style.left=drag.left+dx+'px';root.style.top=drag.top+dy+'px';fit();});
    pet.addEventListener('pointerup', () => {drag=null;try{localStorage.setItem('hajijian.position',JSON.stringify({x:parseFloat(root.style.left),y:parseFloat(root.style.top)}));}catch{}});
    pet.addEventListener('pointercancel',()=>{drag=null;});
    function open(e){clearTimeout(closeTimer);e.preventDefault();e.stopPropagation();panel.hidden=false;fit();}
    pet.addEventListener('contextmenu',open);
    pet.addEventListener('click',e=>{if(!moved)open(e);});
    root.querySelector('.close').onclick=()=>{panel.hidden=true;};
    document.addEventListener('pointerdown',e=>{if(!root.contains(e.target)&&!busy)panel.hidden=true;});
    root.addEventListener('keydown',e=>{if(e.key==='Escape')panel.hidden=true;});
    const gib = n => n == null ? '不适用' : (n / 1073741824).toFixed(2)+' GiB';
    clean.onclick = async () => {
      if(busy)return;clearTimeout(closeTimer);busy=true;clean.disabled=true;root.classList.add('busy');message.textContent='哈基简正在打扫，请稍候…';
      try {
        const response = await api.fetchApi('/hajijian/clean',{method:'POST'});
        const data = await response.json();if(!response.ok)throw new Error(data.error || `请求失败 (${response.status})`);
        const b=data.before,a=data.after;
        message.textContent=`打扫完成！\n进程内存：${gib(b.ram)} → ${gib(a.ram)}\nPyTorch 显存：${gib(b.reserved)} → ${gib(a.reserved)}\n整卡显存：${gib(b.device_used)} → ${gib(a.device_used)}\n仅回收可释放部分；整卡数据包含其他程序。`;
        closeTimer = setTimeout(() => { panel.hidden = true; closeTimer = null; }, 3000);
      } catch(e){message.textContent=e.message || '连接失败，请确认服务仍在运行。';}
      finally{busy=false;clean.disabled=false;root.classList.remove('busy');fit();}
    };
  }
});


