import requests, json, base64, io
from PIL import Image
s = requests.Session(); s.trust_env = False
for i in range(5):
    try:
        r = s.get('https://yyb.fuckinghigh.eu.org/yyb/api/captcha', headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        d = r.json()
        raw = base64.b64decode(d['png'].split(',', 1)[1])
        r1 = requests.post('http://172.17.0.1:7778', json={'image': base64.b64encode(raw).decode()}, timeout=15)
        orig = r1.json().get('result', '')
        img = Image.open(io.BytesIO(raw)).convert('L')
        img = img.point(lambda x: 255 if x > 160 else 0)
        img = img.resize((img.width*3, img.height*3), Image.LANCZOS)
        buf = io.BytesIO(); img.save(buf, format='PNG'); proc = buf.getvalue()
        r2 = requests.post('http://172.17.0.1:7778', json={'image': base64.b64encode(proc).decode()}, timeout=15)
        proc_txt = r2.json().get('result', '')
        print(f'第{i+1}组: 原图={orig}  预处理={proc_txt}')
    except Exception as e:
        print(f'第{i+1}组异常: {e}')
print('验证码图片已存 /ql/data/scripts/cap_test_last.png')
open('/ql/data/scripts/cap_test_last.png','wb').write(raw)
