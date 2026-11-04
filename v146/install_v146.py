#!/usr/bin/env python3
"""EXCAVATOR PRO v1.4.6: exact approved AI artwork + real lower chat composer.
Patches only ai() view and scoped CSS; no backend or database changes.
"""
from pathlib import Path
import hashlib, json, os, shutil, stat, subprocess, sys
from datetime import datetime
from urllib.request import Request, urlopen

BASE = os.getenv('EXPRO_V146_ASSETS', 'https://raw.githubusercontent.com/neuromix973-maker/ai-landin/expro-v146-assets/v146').rstrip('/')
R = Path(os.getenv('EXPRO_V146_ROOT', '/opt/excavator-pro/current/frontend'))
TEST = os.getenv('EXPRO_V146_TEST') == '1'
DIGESTS = {
    'ai_layout_v146.txt':'321aa40d9d9aaf427a6277bcd05e1ec8baff59aeaa9e11b5fcc6b3f824f083c1',
    'ai_style_v146.txt':'278731c905fb811eb81f1afbff186151f1713ea3526a5eec25073965e76b51c3',
    'approved_ai_banner_v146.webp':'dbf2fa264fdd625e3cbefa4315d98eff701f8589bfa4ee5b443ede7a1269fdb1',
    'approved_ai_face_v146.webp':'af5b980da1f2cf11831ff67303f1c33a1bcfd686d5992767861b929f97d7b9c2'
}

def get(name):
    u=f'{BASE}/{name}'
    with urlopen(Request(u,headers={'User-Agent':'EXCAVATOR-PRO-Updater/1.4.6'}),timeout=25) as response:
        b=response.read(250_000)
    if hashlib.sha256(b).hexdigest()!=DIGESTS[name]:
        raise RuntimeError('CHECKSUM FAILED: '+name)
    return b

def replace(s, a, b, filename):
    if s.count(a)!=1:
        raise RuntimeError('STOP: expected code differs in '+filename+' marker: '+a[:45])
    return s.replace(a,b,1)

def atomic_write(p,data):
    if p.exists():
        info=p.stat();mode=stat.S_IMODE(info.st_mode);uid=info.st_uid;gid=info.st_gid
    else:
        info=p.parent.stat();mode=0o644;uid=info.st_uid;gid=info.st_gid
    tmp=p.with_name(p.name+'.tmp-expro146')
    if tmp.exists():raise RuntimeError('Temporary file exists: '+str(tmp))
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        os.chown(tmp,uid,gid)
        os.chmod(tmp,mode)
        os.replace(tmp,p)
    finally:
        if tmp.exists():tmp.unlink()

def main():
    print('=== EXCAVATOR PRO V1.4.6 APPROVED AI UI ===',flush=True)
    if not R.is_dir():raise RuntimeError('Frontend not found')
    names=['views.js','style.css','app.js','server.html','pwa-update.js','sw.js','version.json']
    data={n:(R/n).read_text(encoding='utf-8') for n in names}
    v=json.loads(data['version.json'])
    if v.get('version')=='1.4.6':
        print('V1.4.6 ALREADY INSTALLED');return
    if v.get('version')!='1.4.5':
        raise RuntimeError('STOP: expected 1.4.5, actual '+str(v.get('version')))
    # No secrets collected and no AI requests are sent.
    if "case 'ai-form':" not in data['app.js'] or "'/ai/chat'" not in data['app.js']:
        raise RuntimeError('STOP: Missing actual Polza.ai chat submit handler')
    if "case 'exai-question':" not in data['app.js'] or "case 'exai-gallery':" not in data['app.js']:
        anchor="case 'ai-photo':"
        if anchor not in data['app.js']:
            raise RuntimeError('STOP: AI photo handler differs')
        additions="""case 'exai-question':{
 const area=document.querySelector('#ai-form textarea');
 if(area){area.value=btn.dataset.text||'';area.focus()}
 return;
 }
 case 'exai-gallery':{
 await go('diagnostics');
 notify('Выберите «Из галереи»');
 return;
 }
 """
        if "case 'exai-question':" in data['app.js']:
            additions=additions[additions.index("case 'exai-gallery':"):]
        elif "case 'exai-gallery':" in data['app.js']:
            additions=additions[:additions.index("case 'exai-gallery':")]
        data['app.js']=data['app.js'].replace(anchor,additions+anchor,1)
    raw={n:get(n) for n in DIGESTS}
    layout=raw['ai_layout_v146.txt'].decode('utf-8')
    styles=raw['ai_style_v146.txt'].decode('utf-8')
    view=data['views.js']; a=view.find('export function ai(){'); b=view.find('export function diagnostics(){',a)
    if a<0 or b<0:raise RuntimeError('STOP: AI view anchors missing')
    data['views.js']=view[:a]+layout+view[b:]
    if 'NG_APPROVED_EXPRO_AI_V146' in data['style.css']:
        raise RuntimeError('STOP: style already installed')
    data['style.css']+='\n'+styles
    data['app.js']=replace(data['app.js'],"from'./views.js?v=145'","from'./views.js?v=146'",'app.js')
    for old,new in [('style.css?v=145','style.css?v=146'),('app.js?v=145','app.js?v=146'),('pwa-update.js?v=145','pwa-update.js?v=146')]:
        data['server.html']=replace(data['server.html'],old,new,'server.html')
    data['pwa-update.js']=replace(data['pwa-update.js'],"const CURRENT = '1.4.5';","const CURRENT = '1.4.6';",'pwa-update.js')
    data['sw.js']=replace(data['sw.js'],'expro-shell-v145','expro-shell-v146','sw.js')
    v['version']='1.4.6';v['message']='Утверждённый портрет ИИ, чат и отправка снизу'
    data['version.json']=json.dumps(v,ensure_ascii=False)+'\n'
    for n in ('views.js','app.js','pwa-update.js','sw.js'):
        chk=subprocess.run(['node','--check','--input-type=module'],input=data[n],text=True,capture_output=True)
        if chk.returncode:raise RuntimeError('JS INVALID '+n+': '+chk.stderr[:250])
    print('PREFLIGHT: CODE & CHECKSUMS OK',flush=True)
    backup=Path('/opt/excavator-pro/backups')/('approved-ai-v146-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    if TEST: backup=R.parent/'test-backups'/backup.name
    backup.mkdir(parents=True,mode=0o700)
    for n in names:shutil.copy2(R/n,backup/n)
    newfiles=[R/'assets/approved_ai_banner_v146.webp',R/'assets/approved_ai_face_v146.webp']
    if any(p.exists() for p in newfiles):raise RuntimeError('STOP: artwork path already exists')
    applied=[]
    try:
        for n in names:
            p=R/n;atomic_write(p,data[n].encode('utf-8'));applied.append(p)
        for p in newfiles:
            atomic_write(p,raw[p.name]);applied.append(p)
        if not TEST:
            with urlopen('http://127.0.0.1:18450/static/version.json',timeout=10) as z:
                assert json.load(z)['version']=='1.4.6'
            with urlopen('http://127.0.0.1:18450/api/health',timeout=10) as z:
                assert json.load(z).get('ok') is True
            for p in newfiles:
                with urlopen('http://127.0.0.1:18450/assets/'+p.name,timeout=10) as z:
                    if hashlib.sha256(z.read()).hexdigest()!=DIGESTS[p.name]:
                        raise RuntimeError('PUBLIC ASSET MISMATCH: '+p.name)
    except Exception as e:
        for n in names:
            if R/n in applied:atomic_write(R/n,(backup/n).read_bytes())
        for p in newfiles:
            if p in applied and p.exists():p.unlink()
        raise RuntimeError('ROLLBACK: '+str(e))
    print('=== EXCAVATOR PRO V1.4.6 INSTALLED ===')
    print('APPROVED MAN PHOTO: REAL IMAGE INCLUDED')
    print('BOTTOM COMPOSER: FIXED ABOVE NAVIGATION')
    print('AI SUBMIT HANDLER: PRESERVED')
    print('BACKUP:',backup)
    print('DATABASE / OWNER ACCESS / TARIFF / POLZA: UNCHANGED')
if __name__=='__main__':
    try:main()
    except Exception as ex:print(str(ex),file=sys.stderr);sys.exit(1)