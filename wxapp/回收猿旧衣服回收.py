#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回收猿旧衣服回收 —— 青龙面板自动签到脚本
========================================================
小程序 appid : wxadd84841bd31a665
业务后端    : https://www.52bjy.com
             appkey=1079fb245839e765  secret=UppwYkfBlk  app=hsywx

流程：
  1. 登录(weixin_bind)：用 smallcat 取 wx.login code + iv + encryptedData，
     换取业务 username（持久，可跨天复用）。
  2. 查询签到状态(getsigninfo)，若当日已签则跳过。
  3. 执行签到(qiandao)。

【优先缓存 code 参数】
  - wx.login 的 code 会连同 iv/encryptedData 一起写入本地缓存文件，
    5 分钟内优先复用缓存 code，过期(失效/被消耗)后自动重新向 smallcat 获取。
  - 同时缓存登录得到的 username，之后每日签到直接复用，无需再登录。

依赖环境变量（青龙面板内配置）：
  wx_server_url    smallcat wx_server 地址   默认 http://49.232.164.167:8787
  wx_auth          smallcat auth 值         默认 
  hsy_openid       回收猿 openid，多个用 & 或 , 或换行分隔
  hsy_cache_file   缓存文件路径（可选）
"""

import os
import json
import time
import hashlib
import urllib.request
import urllib.parse

# ---------------- 常量（来自小程序源码） ----------------
HSY_APPID = "wxadd84841bd31a665"          # 回收猿小程序 appid
APPKEY = "1079fb245839e765"               # 业务 appkey
SECRET = "UppwYkfBlk"                     # 签名密钥
APP = "hsywx"                             # 业务 app 标识
BALL = "www"                              # 后端域名前缀
BASE_URL = f"https://{BALL}.52bjy.com"
MERCHANT_ID = "2"

CODE_CACHE_TTL = 300                       # code 缓存有效期（秒）

# ---------------- 环境变量 ----------------
WX_SERVER_URL = os.environ.get("wx_server_url", "http://49.232.164.167:8787").rstrip("/")
WX_AUTH = os.environ.get("wx_auth", "")
HSY_OPENID_ENV = os.environ.get("hsy_openid", "")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.environ.get("hsy_cache_file") or os.path.join(_SCRIPT_DIR, "回收猿_签到缓存.json")


def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------- smallcat 接口 ----------------
def smallcat_post(endpoint, body):
    req = urllib.request.Request(
        WX_SERVER_URL + endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"auth": WX_AUTH, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_code_and_userinfo(openid):
    """获取 wx.login code + getUserProfile 的 iv/encryptedData。
    YYB 面板模式（wx_auth 以 yyb_ 开头）：code 走 /yyb/api/code，
    iv/encryptedData 走 /yyb/api/invoke-cloud(webapi_getuserinfo)。"""
    if WX_AUTH.startswith("yyb_"):
        base = WX_SERVER_URL if "yyb" in WX_SERVER_URL else "https://yyb.fuckinghigh.eu.org"

        def yyb_req(method, url, body=None):
            data = json.dumps(body).encode("utf-8") if body is not None else None
            req = urllib.request.Request(
                url, data=data,
                headers={"X-API-Key": WX_AUTH, "Content-Type": "application/json"},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))

        qs = urllib.parse.urlencode({"appid": HSY_APPID, "openid": openid})
        code_resp = yyb_req("GET", f"{base}/yyb/api/code?{qs}")
        if not code_resp.get("success") or not code_resp.get("code"):
            raise RuntimeError(f"YYB 获取 wx code 失败: {code_resp.get('msg')}")
        code = code_resp["code"]

        ui_resp = yyb_req("POST", f"{base}/yyb/api/invoke-cloud", {
            "appid": HSY_APPID,
            "openid": openid,
            "raw_api_data": json.dumps({"api_name": "webapi_getuserinfo", "with_credentials": True}),
        })
        ui = ui_resp.get("data", {}) if ui_resp.get("success") else {}
        iv = ui.get("iv", "")
        encrypted_data = ui.get("encryptedData", "")
        if not iv or not encrypted_data:
            raise RuntimeError(f"YYB 获取 userinfo 失败: {ui_resp.get('msg')}")
        return code, iv, encrypted_data

    code_resp = smallcat_post("/wx/code", {"openid": openid, "appid": HSY_APPID})
    if code_resp.get("status") is not True or not code_resp.get("data", {}).get("code"):
        raise RuntimeError(f"获取 wx code 失败: {code_resp.get('message')}")
    code = code_resp["data"]["code"]

    ui_resp = smallcat_post("/wx/getuserinfo", {"openid": openid, "appid": HSY_APPID})
    ui = ui_resp.get("data", {}) if ui_resp.get("status") is True else {}
    iv = ui.get("iv", "")
    encrypted_data = ui.get("encryptedData", "")
    if not iv or not encrypted_data:
        raise RuntimeError(f"获取 userinfo 失败: {ui_resp.get('message')}")
    return code, iv, encrypted_data


# ---------------- 业务接口 ----------------
def weixin_bind(code, iv, encrypted_data):
    """复刻小程序 weixinOauth：weixin_bind 登录，返回 (username, token)"""
    # 签名串为源码中硬编码顺序（非排序）
    sign_str = (f"action=auth&appkey={APPKEY}&code={code}&inviter=&iv={iv}"
                f"&merchant_id={MERCHANT_ID}&method=weixin_bind&version=2{SECRET}")
    sign = md5(sign_str)
    url = (f"{BASE_URL}/api/app/hsy.php?action=auth&appkey={APPKEY}&code={code}"
           f"&inviter=&iv={iv}&merchant_id={MERCHANT_ID}&method=weixin_bind"
           f"&version=2&sign={sign}")
    data = urllib.parse.urlencode({"encryptedData": encrypted_data}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "EnvConnection": "test"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if not resp.get("isSucess") or not resp.get("data", {}).get("username"):
        raise RuntimeError(f"weixin_bind 失败: {resp.get('message')}")
    return resp["data"]["username"], resp["data"].get("jiufy_auth", "")


def ax_get(params):
    """复刻小程序 axGet：排序 key 拼接后 md5 签名，GET 请求"""
    php = params.pop("php")
    params.setdefault("merchant_id", MERCHANT_ID)
    params.setdefault("appkey", APPKEY)
    params.pop("sign", None)
    query = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    sign = md5(query + SECRET)
    url = f"{BASE_URL}/api/app/{php}?{query}&sign={sign}"
    req = urllib.request.Request(url, headers={"EnvConnection": "test"}, method="GET")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def get_sign_info(username):
    return ax_get({
        "php": "hsy.php", "action": "user", "appkey": APPKEY, "app": APP,
        "merchant_id": MERCHANT_ID, "method": "getsigninfo", "username": username,
        "version": 4, "sign": True,
    })


def do_qiandao(username):
    return ax_get({
        "php": "hsy.php", "action": "user", "appkey": APPKEY, "app": APP,
        "merchant_id": MERCHANT_ID, "method": "qiandao", "username": username,
        "version": 4, "sign": True,
    })


# ---------------- 缓存 ----------------
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    try:
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CACHE_FILE)
    except OSError as e:
        log(f"⚠️ 写缓存失败: {e}")


# ---------------- 账号处理 ----------------
def ensure_login(openid, cache):
    """优先缓存 code 登录，失效后重新获取，返回 (username, 是否命中缓存)"""
    entry = cache.setdefault(openid, {})

    # 已有 username 直接复用（持久登录态）
    if entry.get("username"):
        return entry["username"], True

    # 优先复用缓存 code（5 分钟内），否则重新获取
    now = time.time()
    code = entry.get("code")
    code_ts = entry.get("code_ts", 0)
    iv = entry.get("iv", "")
    encrypted_data = entry.get("encryptedData", "")
    if not code or not iv or not encrypted_data or (now - code_ts) > CODE_CACHE_TTL:
        log("  无可用缓存 code，重新获取 code / userinfo ...")
        code, iv, encrypted_data = fetch_code_and_userinfo(openid)
        entry["code"] = code
        entry["iv"] = iv
        entry["encryptedData"] = encrypted_data
        entry["code_ts"] = now
        save_cache(cache)
    else:
        log(f"  命中缓存 code（{int(now - code_ts)}s 前获取），直接复用")

    try:
        username, token = weixin_bind(code, iv, encrypted_data)
    except RuntimeError:
        # code 失效，强制重新获取一次
        log("  缓存 code 失效，重新获取后重试登录 ...")
        code, iv, encrypted_data = fetch_code_and_userinfo(openid)
        entry["code"] = code
        entry["iv"] = iv
        entry["encryptedData"] = encrypted_data
        entry["code_ts"] = time.time()
        username, token = weixin_bind(code, iv, encrypted_data)

    entry["username"] = username
    entry["token"] = token
    save_cache(cache)
    return username, False


def process_account(openid, index, cache):
    log(f"账号#{index} {openid}")
    try:
        username, cached = ensure_login(openid, cache)
        log(f"  {'复用缓存 username' if cached else '登录成功'}: {username}")

        info = get_sign_info(username)
        if not info.get("isSucess"):
            # 登录态可能失效，清掉缓存 username 后重登录一次
            log(f"  查询签到状态异常: {info.get('message')}，尝试重新登录 ...")
            cache.get(openid, {}).pop("username", None)
            cache.get(openid, {}).pop("token", None)
            save_cache(cache)
            username, _ = ensure_login(openid, cache)
            log(f"  重新登录 username={username}")
            info = get_sign_info(username)
        if not info.get("isSucess"):
            log(f"  查询签到状态失败: {info.get('message')}")
            return
        d = info.get("data", {})
        hassign = d.get("hassign", 0)
        balance = d.get("balance", "0")
        day = d.get("thisturn", 0)
        log(f"  签到状态: 已连续 {day} 天, 今日{'已签' if hassign == 1 else '未签'}, 余额 {balance} 元")

        if hassign == 1:
            log("  ✅ 今日已签到，跳过")
            return

        res = do_qiandao(username)
        if res.get("isSucess"):
            rd = res.get("data", {})
            log(f"  ✅ 签到成功! 本次奖励 {rd.get('qiandao_award', '?')} 元")
        else:
            msg = res.get("message") or ""
            if any(k in msg for k in ("已签", "已经", "重复", "签过")):
                log("  ✅ 今日已签到（后端返回已签）")
            else:
                log(f"  ❌ 签到失败: {msg}")
    except Exception as e:
        log(f"  ❌ 执行失败: {e}")


def parse_openids(raw):
    raw = raw.strip()
    if not raw:
        return []
    for sep in ("\n", "&", ","):
        raw = raw.replace(sep, "|")
    return [x.strip() for x in raw.split("|") if x.strip()]


def main():
    log("=" * 50)
    log("回收猿旧衣服回收 自动签到")
    log("=" * 50)

    openids = parse_openids(HSY_OPENID_ENV)
    if not openids:
        log("❌ 未配置 hsy_openid，请先在青龙环境变量中配置")
        log("   示例: hsy_openid=openid1&openid2&openid3")
        return

    cache = load_cache()
    log(f"共 {len(openids)} 个账号")
    for i, oid in enumerate(openids, 1):
        process_account(oid, i, cache)
        if i < len(openids):
            time.sleep(2)

    log("=" * 50)
    log("全部完成")


if __name__ == "__main__":
    main()
