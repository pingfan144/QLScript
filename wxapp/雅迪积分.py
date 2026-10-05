#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==========================================================
# 功能说明：code 换 token（含缓存与自动刷新）
# 机制：wx_server 服务获取微信 code → 小程序登录接口换取 token → 缓存到本地 JSON；
#       下次运行先读取缓存 token，并调用用户信息接口验证是否仍有效；
#       有效则直接复用（无需再获取 code）；失效或过期则重新获取 code 自动刷新。
# ==========================================================


"""
雅迪智行积分任务 code 版

功能：
  1. wx_server 获取微信 code（雅迪小程序，POST {wx_server_url}/wx/code）
  2. 小程序 openid-login 用 code 换 token（token 与 App 端业务网关通用）
  3. 每日签到
  4. 积分任务：评论帖子 x3 / 浏览帖子 x5 / 点赞 x15
  5. 评论、浏览、点赞的帖子自动获取且不重复（本地记录已用帖子，避免风控黑号）
  6. PushPlus 推送
  7. 品赞代理，业务请求优先代理，失败直连兜底


环境变量：
  wx_server_url     wx_server 服务地址，默认 http://49.232.164.167:8787
  wx_auth           wx_server 认证 token（auth 请求头）
  WCS_OPENIDS       账号 openid 列表，逗号分隔（也可直接改脚本顶部 OPENIDS）
  PLUSPLUS_TOKEN    PushPlus token，可选
  PROXY_API         品赞代理提取 API，可选
  PROXY_TYPE        http / socks5，默认 http

依赖：
  pip install requests pycryptodome
  socks5 代理需：
  pip install requests[socks]
"""

from __future__ import annotations
import base64
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import json
import os
import random
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import quote, unquote

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

APP_NAME = "雅迪智行积分任务"
MINI_WX_APPID = "wx7f3ba7d63fd3f32b"

WX_SERVER_URL = os.getenv("wx_server_url", "http://49.232.164.167:8787").rstrip("/")
WX_AUTH = os.getenv("wx_auth", "")

# 账号列表：wcs 服务对应的微信 openid，可用环境变量 WCS_OPENIDS 配置（逗号分隔）
OPENIDS = [
    openid.strip()
    for openid in os.getenv("WCS_OPENIDS", "").replace("，", ",").split(",")
    if openid.strip()
]

PLUSPLUS_TOKEN = os.getenv("PLUSPLUS_TOKEN", "")
PROXY_API = os.getenv("PROXY_API", "")
PROXY_TYPE = os.getenv("PROXY_TYPE", "http").lower()

PROXY_RETRY_TIMES = 3
PROXY_VALIDATE_URL = "http://httpbin.org/ip"
PROXY_FETCH_INTERVAL = 3
ENABLE_DIRECT_FALLBACK = True
REQUEST_TIMEOUT = 30

GATEWAY = "https://gw.yadeaiot.com.cn"

# 小程序网关（登录用）
MINI_GW_APPID = "558e680351f0480c94e3ab30235afcd5"
MINI_AES_KEY = b"FSCMK51e210c4a69"

# 原生 App 业务网关（任务接口）
NATIVE_GW_APPID = "0e7b1d094c7b4073b7c958edbbbc1115"
NATIVE_AES_KEY = b"cIDJ9f05d1604703"

LOGIN_PATH = "/user/wx-mp/openid-login"
VALIDATE_PATH = "/userappruleinfo/queryuserappruleinfobyuserid"
TASK_LIST_PATH = "/userIntegralTask/queryIntegralTask"
SIGN_LIST_PATH = "/userappruleinfo/getsigninlistNew"
SIGN_IN_PATH = "/userappruleinfo/addsigninbyuseridNew"
INTEGRAL_INFO_PATH = "/userappruleinfo/queryintegralinfobyuserid"
PREMIUM_LIST_PATH = "/blog/essay/premium-list"
THEME_LIST_PATH = "/blog/conversation-theme/page-list/by/name"
THEME_ESSAY_PATH = "/blog/conversation-essay/page-list"
ESSAY_DETAIL_PATH = "/blog/essay/detail"
LIKE_PATH = "/blog/essay-comment-reply/like/or/not"
COMMENT_INSERT_PATH = "/blog/essay/conversation/nearby/comment-reply/insert"

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yadea_token_cache.json")
USED_POSTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yadea_used_posts.json")

# 任务编码
TASK_COMMENT = 8           # 有效评论 3 次 1 分 x3
TASK_BROWSE = 31           # 浏览 1 篇 1 分 x5
TASK_LIKE = 37             # 点赞 5 次 1 分 x3


COMMENT_TEXTS = [
    "打卡打卡",
    "支持支持",
    "好车好车",
    "点赞来了",
    "很不错呀",
    "路过看看",
    "支持一下",
]


USER_AGENT = "Dart/3.2 (dart:io)"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sleep(seconds: float) -> None:
    time.sleep(seconds)


def mask(value: Any) -> str:
    value = str(value or "")
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-6:]}"


def json_preview(data: Any, limit: int = 800) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)[:limit]
    except Exception:
        return str(data)[:limit]


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_data(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Safely extract 'data' from an API response, handling null/missing."""
    return resp.get("data") or {}


def log_title() -> None:
    print()
    print("╔" + "═" * 50 + "╗")
    print("║ ♻️ 雅迪智行积分任务 code 版                    ║")
    print(f"║ 🕒 启动时间: {now_text():<32}║")
    print(f"║ 🔢 账号数量: {len(OPENIDS):<34}║")
    print("╚" + "═" * 50 + "╝")


def log_account_header(index: int, total: int, openid: str) -> None:
    print()
    print("┌" + "─" * 50 + "┐")
    print(f"│ 🧩 账号 {index} / {total:<37}│")
    print(f"│ 👤 openid {openid:<36}│")
    print("└" + "─" * 50 + "┘")


def direct_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def parse_proxy_response(text: Any) -> Dict[str, Any] | None:
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)

    text = text.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
        proxy_obj = None

        if isinstance(data.get("data"), list) and data["data"]:
            proxy_obj = data["data"][0]
        elif isinstance(data.get("data"), dict):
            proxy_obj = data["data"]
        elif data.get("ip") and data.get("port"):
            proxy_obj = data
        elif isinstance(data.get("result"), dict):
            proxy_obj = data["result"]

        if proxy_obj:
            host = proxy_obj.get("ip") or proxy_obj.get("host")
            port = proxy_obj.get("port")
            if host and port:
                return {
                    "host": str(host),
                    "port": int(port),
                    "username": proxy_obj.get("user") or proxy_obj.get("username") or "",
                    "password": proxy_obj.get("pass") or proxy_obj.get("password") or "",
                }
    except Exception:
        pass

    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            return {
                "host": parts[0],
                "port": int(parts[1]),
                "username": parts[2] if len(parts) > 2 else "",
                "password": parts[3] if len(parts) > 3 else "",
            }

    return None


def build_proxy_dict(proxy_info: Dict[str, Any] | None) -> Dict[str, str] | None:
    if not proxy_info:
        return None

    host = proxy_info["host"]
    port = proxy_info["port"]
    username = proxy_info.get("username", "")
    password = proxy_info.get("password", "")

    auth = ""
    if username and password:
        auth = f"{quote(username)}:{quote(password)}@"

    scheme = "socks5" if PROXY_TYPE == "socks5" else "http"
    proxy_url = f"{scheme}://{auth}{host}:{port}"

    print(f"🛠️ [代理] 生成 {scheme.upper()} 代理 {host}:{port}")

    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def validate_proxy(proxies: Dict[str, str] | None) -> Tuple[bool, str]:
    if not proxies:
        return False, ""

    try:
        response = requests.get(PROXY_VALIDATE_URL, proxies=proxies, timeout=15)
        if response.status_code == 200:
            try:
                ip = response.json().get("origin", "未知")
            except Exception:
                ip = "未知"
            print(f"✅ [代理] 验证通过，出口 IP: {ip}")
            return True, ip
    except Exception as exc:
        print(f"⚠️ [代理] 验证失败: {exc}")

    return False, ""


def get_valid_proxy(account_name: str) -> Tuple[Dict[str, str] | None, str]:
    if not PROXY_API:
        print(f"⚠️ [代理] {account_name} 未配置 PROXY_API，使用直连")
        return None, ""

    print(f"🌐 [代理] {account_name} 正在获取品赞代理...")

    for index in range(1, PROXY_RETRY_TIMES + 1):
        try:
            response = direct_session().get(PROXY_API, timeout=15)
            proxy_info = parse_proxy_response(response.text)

            if not proxy_info:
                print(f"⚠️ [代理] 第 {index} 次代理解析失败")
                continue

            print(f"✅ [代理] 提取到 {proxy_info['host']}:{proxy_info['port']}")
            proxies = build_proxy_dict(proxy_info)

            ok, ip = validate_proxy(proxies)
            if ok:
                return proxies, ip

            print(f"⚠️ [代理] 第 {index} 次代理不可用")
        except Exception as exc:
            print(f"⚠️ [代理] 第 {index} 次获取代理异常: {exc}")

        if index < PROXY_RETRY_TIMES:
            sleep(2)

    print("⚠️ [代理] 获取失败，使用直连")
    return None, ""


def request_with_proxy(
    method: str,
    url: str,
    *,
    proxies: Dict[str, str] | None = None,
    openid: str = "",
    **kwargs,
) -> requests.Response:
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    if proxies:
        try:
            return requests.request(method, url, proxies=proxies, **kwargs)
        except Exception as exc:
            print(f"⚠️ [代理] {openid} 代理请求失败: {exc}")
            if not ENABLE_DIRECT_FALLBACK:
                raise
            print("🔁 [兜底] 切换直连重试")

    session = direct_session()
    return session.request(method, url, **kwargs)


def send_pushplus(title: str, content: str) -> None:
    if not PLUSPLUS_TOKEN:
        print("⚠️ [PushPlus] 未配置 PLUSPLUS_TOKEN，跳过推送")
        return

    try:
        requests.post(
            "https://www.pushplus.plus/send",
            json={
                "token": PLUSPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "txt",
            },
            timeout=10,
        )
        print("✅ [PushPlus] 推送成功")
    except Exception as exc:
        print(f"❌ [PushPlus] 推送失败: {exc}")


# ====================== 网关加解密 ======================
def aes_ecb_encrypt(plain: str, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_ECB)
    ct = cipher.encrypt(pad(plain.encode("utf-8"), 16))
    return base64.b64encode(ct).decode()


def aes_ecb_decrypt(b64text: str, key: bytes) -> str:
    raw = base64.b64decode(unquote(b64text))
    cipher = AES.new(key, AES.MODE_ECB)
    pt = cipher.decrypt(raw)
    try:
        pt = unpad(pt, 16)
    except Exception:
        pass
    return pt.decode("utf-8", errors="replace")


def gateway_sign(key: bytes, ts: int, payload: Dict[str, Any], add_gateway: bool = True) -> str:
    body = dict(payload)
    if add_gateway:
        body["_gateway"] = "True"
    plain = "gatewayTimestamp={}&json={}".format(
        ts, json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    )
    return aes_ecb_encrypt(plain, key)


def native_headers(token: str, ts: int, sign: str) -> Dict[str, str]:
    return {
        "Content-Type": "x-www-form-urlencoded;charset=utf-8",
        "gatewayAppId": NATIVE_GW_APPID,
        "gatewaySign": sign,
        "gatewayTimestamp": str(ts),
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
        "app-version": "8.8.9",
        "app-version-type": "1",
        "os": "android",
        "request-agent": "2",
        "language": "zh_CN",
        "app-market": "XIAOMI",
        "device-brand": "XIAOMI",
        "phone-model": "25010PN30C",
        "deviceid": "b84ec531-37fa-48e8-a698-c4ae8818c3f9",
        "loginid": "b84ec531-37fa-48e8-a698-c4ae8818c3f9",
        "push-operator": "2",
        "req-id": "325f229d-f27e-4d49-a5f6-eac5b93314ae",
    }


def mini_login_headers(ts: int, sign: str) -> Dict[str, str]:
    return {
        "Content-Type": "x-www-form-urlencoded;charset=utf-8",
        "gatewayAppId": MINI_GW_APPID,
        "gatewaySign": sign,
        "gatewayTimestamp": str(ts),
        "App-Name": "WECHAT_MINI_PROGRAM_TRY",
        "User-Agent": "Mozilla/5.0 MicroMessenger/7.0.20.1781 MiniProgramEnv/Windows",
        "Referer": f"https://servicewechat.com/{MINI_WX_APPID}/74/page-frame.html",
    }


def native_request(
    path: str,
    payload: Dict[str, Any],
    token: str,
    proxies: Dict[str, str] | None = None,
    openid: str = "",
) -> Dict[str, Any]:
    ts = int(time.time() * 1000)
    sign = gateway_sign(NATIVE_AES_KEY, ts, payload)
    headers = native_headers(token, ts, sign)
    url = f"{GATEWAY}/api/app{path}"
    response = request_with_proxy("POST", url, headers=headers, data={}, proxies=proxies, openid=openid)
    try:
        decrypted = aes_ecb_decrypt(response.text, NATIVE_AES_KEY)
        return json.loads(decrypted)
    except Exception:
        return {
            "code": -1,
            "msg": f"响应解析失败: {response.text[:300]}",
        }

# ====================== code 换取 token ======================
def get_code(openid: str) -> str | None:
    # YYB 面板模式：wx_auth 填 yyb_ 开头的 API Key，走 YYB 取码接口
    if WX_AUTH.startswith("yyb_"):
        base = WX_SERVER_URL if "yyb" in WX_SERVER_URL else "https://yyb.fuckinghigh.eu.org"
        try:
            resp = direct_session().get(
                f"{base}/yyb/api/code",
                params={"appid": MINI_WX_APPID, "openid": openid},
                headers={"X-API-Key": WX_AUTH},
                timeout=60,
            )
            data = resp.json()
        except Exception as exc:
            print(f"❌ [授权] YYB 取码异常: {exc}")
            return None
        if data.get("success") and data.get("code"):
            print("✅ [授权] code 获取成功 (YYB)")
            return data["code"]
        print(f"❌ [授权] YYB 取码失败: {json_preview(data)}")
        return None
    url = f"{WX_SERVER_URL}/wx/code"
    print(f"🔐 [授权] 请求 wx_server: appid={MINI_WX_APPID} openid={mask(openid)}")

    try:
        response = direct_session().post(
            url,
            headers={"auth": WX_AUTH, "Content-Type": "application/json"},
            json={"appid": MINI_WX_APPID, "openid": openid},
            timeout=30,
        )
        try:
            data = response.json()
        except Exception:
            data = response.text.strip()

        code = (data.get("data") or {}).get("code") if isinstance(data, dict) else None
        if code:
            print("✅ [授权] code 获取成功")
            return code

        print(f"❌ [授权] code 获取失败: {json_preview(data)}")
        return None
    except Exception as exc:
        print(f"❌ [授权] code 获取异常: {exc}")
        return None


def login_by_code(openid: str, code: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    try:
        print("🔐 [登录] 使用 code 换 token")
        ts = int(time.time() * 1000)
        payload = {"appid": MINI_WX_APPID, "loginCode": code, "thirdLoginType": 12}
        sign = gateway_sign(MINI_AES_KEY, ts, payload, add_gateway=False)
        headers = mini_login_headers(ts, sign)

        response = request_with_proxy(
            "POST",
            f"{GATEWAY}/api/app{LOGIN_PATH}",
            headers=headers,
            data={},
            proxies=proxies,
            openid=openid,
        )

        try:
            decrypted = aes_ecb_decrypt(response.text, MINI_AES_KEY)
            data = json.loads(decrypted)
        except Exception:
            data = {"raw": response.text[:800]}

        if data.get("code") != "000000":
            if data.get("code") == "720500":
                print("❌ [登录] 登录失败(720500): 雅迪网关返回『网络不稳定』")
                print("    👉 最常见原因：该微信号从未登录过『雅迪智行』小程序，雅迪侧没有账号")
                print("       请先用该微信号打开雅迪智行小程序完成手机号登录，或用雅迪智行 App 登录一次")
                print("       若已有账号仍报此错，多为风控：稍后重试或配置 PROXY_API 更换出口 IP")
            else:
                print(f"❌ [登录] 登录失败: {json_preview(data)}")
            return None, data

        token = (data.get("data") or {}).get("userInfoVo", {}).get("token")
        if token:
            print(f"✅ [登录] token 获取成功: {mask(token)}")
            return token, data

        print(f"❌ [登录] 未识别 token 字段: {json_preview(data)}")
        return None, data
    except Exception as exc:
        print(f"❌ [登录] 请求异常: {exc}")
        return None, None


def jwt_expire_time(token: str) -> str | None:
    """解析 JWT 中的 exp，返回 iso 格式过期时间"""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        info = json.loads(base64.b64decode(payload))
        exp = info.get("exp")
        if exp:
            return datetime.fromtimestamp(exp).isoformat()
    except Exception:
        pass
    return None


# ====================== Token 缓存管理 ======================
def load_token_cache() -> Dict[str, Any]:
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        print(f"⚠️ [缓存] 读取失败: {exc}")
    return {}


def save_token_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print("✅ [缓存] Token保存成功")
    except Exception as exc:
        print(f"❌ [缓存] 保存失败: {exc}")


def get_cached_token(openid: str) -> str | None:
    cache = load_token_cache()
    data = cache.get(openid)
    if data and data.get("token") and data.get("expireTime"):
        try:
            expire = datetime.fromisoformat(data["expireTime"]).timestamp() * 1000
            if time.time() * 1000 < expire - 3600 * 1000:
                print(f"✅ [缓存] 使用 {openid} token")
                return data["token"]
        except Exception as exc:
            print(f"⚠️ [缓存] 过期时间解析异常: {exc}")
    return None


def set_cached_token(openid: str, token: str, expire_time: str) -> None:
    cache = load_token_cache()
    cache[openid] = {"token": token, "expireTime": expire_time, "updateTime": datetime.now().isoformat()}
    save_token_cache(cache)


def validate_token(token: str, proxies: Dict[str, str] | None, openid: str) -> bool:
    resp = native_request(VALIDATE_PATH, {}, token, proxies, openid)
    return resp.get("code") == "000000"


def login_with_cache(openid: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    """优先使用缓存 token（用户信息接口验证），失效自动 code 刷新（登录失败自动重试 1 次）"""
    cache_token = get_cached_token(openid)
    if cache_token:
        print("🔍 [缓存] 验证 token")
        try:
            if validate_token(cache_token, proxies, openid):
                print("✅ [缓存] token 有效")
                return cache_token, None
        except Exception as exc:
            print(f"⚠️ [缓存] 验证异常: {exc}")
        print("⚠️ [缓存] token 已失效，重新登录")

    raw_login = None
    for attempt in (1, 2):
        code = get_code(openid)
        if not code:
            return None, None

        token, raw_login = login_by_code(openid, code, proxies)
        if token:
            expire_time = jwt_expire_time(token)
            if not expire_time:
                expire_time = datetime.fromtimestamp(time.time() + 7 * 24 * 3600).isoformat()
            set_cached_token(openid, token, expire_time)
            return token, raw_login

        if attempt < 2:
            print("⏳ [登录] 5s 后重新获取 code 重试")
            sleep(5)

    return None, raw_login


# ====================== 已用帖子去重 ======================
def load_used_posts() -> set:
    try:
        if os.path.exists(USED_POSTS_FILE):
            with open(USED_POSTS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("used", []))
    except Exception as exc:
        print(f"⚠️ [去重] 读取失败: {exc}")
    return set()


def save_used_posts(used: set) -> None:
    try:
        with open(USED_POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"used": sorted(used), "updateTime": now_text()}, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"❌ [去重] 保存失败: {exc}")


def fetch_post_pool(token: str, proxies: Dict[str, str] | None, openid: str, limit: int = 60) -> List[int]:
    """从精选列表 + 主题帖子列表自动抓取帖子 essayId（过滤官方账号）"""
    pool: List[int] = []
    seen = set()

    def collect(records: List[Dict[str, Any]]) -> None:
        for r in records or []:
            if r.get("officialCertification") == 1:
                continue
            if r.get("isLike"):
                continue
            eid = r.get("essayId") or r.get("id")
            if eid and eid not in seen:
                seen.add(eid)
                pool.append(eid)

    try:
        for page in (1, 2, 3):
            resp = native_request(PREMIUM_LIST_PATH, {"current": page, "size": 20}, token, proxies, openid)
            if resp.get("code") != "000000":
                break
            collect((resp.get("data") or {}).get("records", []))
            if len(pool) >= limit:
                break
    except Exception as exc:
        print(f"⚠️ [帖子] 精选列表获取异常: {exc}")

    if len(pool) < limit:
        try:
            resp = native_request(THEME_LIST_PATH, {"current": 1, "size": 20}, token, proxies, openid)
            themes = (resp.get("data") or {}).get("records", []) if resp.get("code") == "000000" else []
            for theme in themes[:8]:
                tid = theme.get("id")
                if not tid:
                    continue
                resp = native_request(THEME_ESSAY_PATH, {"current": 1, "size": 20, "themeId": str(tid)}, token, proxies, openid)
                if resp.get("code") != "000000":
                    continue
                collect((resp.get("data") or {}).get("records", []))
                if len(pool) >= limit:
                    break
        except Exception as exc:
            print(f"⚠️ [帖子] 主题帖子获取异常: {exc}")

    print(f"📚 [帖子] 抓取到候选帖子 {len(pool)} 篇")
    return pool


def pick_posts(
    token: str,
    proxies: Dict[str, str] | None,
    openid: str,
    count: int,
    used: set,
) -> List[int]:
    """取 count 个未使用过的帖子，并立刻标记为已用"""
    if count <= 0:
        return []
    pool = fetch_post_pool(token, proxies, openid, max(count + 10, 30))
    fresh = [eid for eid in pool if str(eid) not in used]
    if len(fresh) < count:
        print(f"⚠️ [帖子] 可用帖子不足（需要 {count}，只有 {len(fresh)}），按现有数量执行")
    picked = fresh[:count]
    for eid in picked:
        used.add(str(eid))
    save_used_posts(used)
    return picked


# ====================== 任务执行 ======================
def get_task_remaining(tasks: List[Dict[str, Any]], task_code: int) -> int:
    for t in tasks or []:
        if t.get("taskCode") == task_code:
            limit = t.get("limitTimes") or 0
            done = t.get("completeTimes") or 0
            return max(0, limit - done)
    return 0


def get_task_status(tasks: List[Dict[str, Any]]) -> str:
    names = {8: "评论帖子", 31: "浏览帖子", 37: "点赞"}
    parts = []
    for t in tasks or []:
        code = t.get("taskCode")
        if code in names:
            parts.append(f"{names[code]}{t.get('completeTimes', 0)}/{t.get('limitTimes', 0)}")
    return " ".join(parts)


def do_signin(token: str, proxies: Dict[str, str] | None, openid: str) -> str:
    try:
        resp = native_request(SIGN_LIST_PATH, {}, token, proxies, openid)
        if resp.get("code") != "000000":
            return f"查询签到列表失败({resp.get('code')})"
        today = datetime.now().strftime("%Y-%m-%d")
        for item in resp.get("data") or []:
            if item.get("date") == today:
                if item.get("isSignin") == 1:
                    return "今日已签到"
                break
        resp = native_request(SIGN_IN_PATH, {}, token, proxies, openid)
        if resp.get("code") == "000000":
            value = resp.get("data")
            return f"签到成功(+{value}积分)" if value is not None else "签到成功"
        if resp.get("code") == "120168":
            return "今日已签到"
        return f"签到失败({resp.get('code')} {resp.get('msg')})"
    except Exception as exc:
        return f"签到异常: {exc}"


def do_comments(token: str, proxies: Dict[str, str] | None, openid: str, completes: int, used: set) -> Tuple[int, List[str]]:
    """有效评论 3 次 = 1 次完成，返回 (完成数, 明细)"""
    success = 0
    logs = []
    total = completes * 3
    if total <= 0:
        return 0, ["今日已完成"]
    posts = pick_posts(token, proxies, openid, total, used)
    for i, eid in enumerate(posts):
        try:
            text = COMMENT_TEXTS[random.randint(0, len(COMMENT_TEXTS) - 1)]
            payload = {"type": 2, "parentId": -1, "essayId": eid, "text": text}
            resp = native_request(COMMENT_INSERT_PATH, payload, token, proxies, openid)
            if resp.get("code") == "000000":
                success += 1
            else:
                logs.append(f"评论#{eid}失败({resp.get('code')} {resp.get('msg')})")
        except Exception as exc:
            logs.append(f"评论#{eid}异常: {exc}")
        if i < len(posts) - 1:
            sleep(random.randint(3, 7))
    logs.append(f"成功 {success}/{total} 条评论")
    return min(success // 3, completes), logs


def do_browse(token: str, proxies: Dict[str, str] | None, openid: str, count: int, used: set) -> Tuple[int, List[str]]:
    """浏览帖子，1 篇 = 1 次完成"""
    success = 0
    logs = []
    if count <= 0:
        return 0, ["今日已完成"]
    posts = pick_posts(token, proxies, openid, count, used)
    for i, eid in enumerate(posts):
        try:
            resp = native_request(ESSAY_DETAIL_PATH, {"id": str(eid)}, token, proxies, openid)
            if resp.get("code") == "000000":
                success += 1
            else:
                logs.append(f"浏览#{eid}失败({resp.get('code')} {resp.get('msg')})")
        except Exception as exc:
            logs.append(f"浏览#{eid}异常: {exc}")
        if i < len(posts) - 1:
            sleep(random.randint(3, 7))
    logs.append(f"成功 {success}/{count} 篇")
    return success, logs


def do_like(token: str, proxies: Dict[str, str] | None, openid: str, completes: int, used: set) -> Tuple[int, List[str]]:
    """点赞 5 次 = 1 次完成"""
    success = 0
    logs = []
    total = completes * 5
    if total <= 0:
        return 0, ["今日已完成"]
    posts = pick_posts(token, proxies, openid, total, used)
    for i, eid in enumerate(posts):
        try:
            payload = {"id": eid, "type": 2, "action": 0}
            resp = native_request(LIKE_PATH, payload, token, proxies, openid)
            if resp.get("code") == "000000":
                success += 1
            else:
                logs.append(f"点赞#{eid}失败({resp.get('code')} {resp.get('msg')})")
        except Exception as exc:
            logs.append(f"点赞#{eid}异常: {exc}")
        if i < len(posts) - 1:
            sleep(random.randint(3, 7))
    logs.append(f"成功 {success}/{total} 次点赞")
    return min(success // 5, completes), logs


# ====================== 账号主流程 ======================
def run_account(index: int, total: int, openid: str) -> Dict[str, Any]:
    result = {
        "openid": openid,
        "success": False,
        "proxyStatus": "-",
        "proxyIp": "-",
        "token": "-",
        "signMsg": "-",
        "commentMsg": "-",
        "browseMsg": "-",
        "likeMsg": "-",
        "integral": "-",
        "error": "",
    }

    log_account_header(index, total, openid)

    try:
        proxies, proxy_ip = get_valid_proxy(openid)
        result["proxyStatus"] = "代理" if proxies else "直连"
        result["proxyIp"] = proxy_ip or "-"

        token, _ = login_with_cache(openid, proxies)
        if not token:
            result["error"] = "token 获取失败"
            print("❌ [账号] token 获取失败")
            return result
        result["token"] = mask(token)

        # 任务列表
        tasks_resp = native_request(TASK_LIST_PATH, {"type": 1, "versionLimit": 3}, token, proxies, openid)
        if tasks_resp.get("code") != "000000":
            result["error"] = f"任务列表获取失败({tasks_resp.get('code')})"
            print(f"❌ [任务] 获取失败: {json_preview(tasks_resp)}")
            return result
        tasks = tasks_resp.get("data") or []
        print(f"📋 [任务] 当前进度: {get_task_status(tasks)}")

        # 1. 每日签到
        print("📝 [签到] 开始执行")
        result["signMsg"] = do_signin(token, proxies, openid)
        print(f"✅ [签到] {result['signMsg']}")

        used = load_used_posts()

        # 2. 评论帖子（每天 3 次，3 条评论 = 1 次）
        remaining = get_task_remaining(tasks, TASK_COMMENT)
        if remaining > 0:
            print(f"💬 [评论帖子] 剩余 {remaining} 次")
            ok_count, logs = do_comments(token, proxies, openid, remaining, used)
            result["commentMsg"] = f"完成 {ok_count}/{remaining} 次"
            for log in logs:
                print(f"   {log}")
            print(f"✅ [评论帖子] {result['commentMsg']}")
        else:
            result["commentMsg"] = "今日已完成"
            print("✅ [评论帖子] 今日已完成")

        # 3. 浏览帖子（每天 5 次）
        remaining = get_task_remaining(tasks, TASK_BROWSE)
        if remaining > 0:
            print(f"👀 [浏览帖子] 剩余 {remaining} 次")
            ok_count, logs = do_browse(token, proxies, openid, remaining, used)
            result["browseMsg"] = f"完成 {ok_count}/{remaining} 次"
            for log in logs:
                print(f"   {log}")
            print(f"✅ [浏览帖子] {result['browseMsg']}")
        else:
            result["browseMsg"] = "今日已完成"
            print("✅ [浏览帖子] 今日已完成")

        # 4. 点赞（每天 3 次，5 赞 = 1 次）
        remaining = get_task_remaining(tasks, TASK_LIKE)
        if remaining > 0:
            print(f"👍 [点赞] 剩余 {remaining} 次")
            ok_count, logs = do_like(token, proxies, openid, remaining, used)
            result["likeMsg"] = f"完成 {ok_count}/{remaining} 次"
            for log in logs:
                print(f"   {log}")
            print(f"✅ [点赞] {result['likeMsg']}")
        else:
            result["likeMsg"] = "今日已完成"
            print("✅ [点赞] 今日已完成")

        # 最终积分
        try:
            info = native_request(INTEGRAL_INFO_PATH, {}, token, proxies, openid)
            if info.get("code") == "000000":
                result["integral"] = str((info.get("data") or {}).get("totalValue", "-"))
                print(f"💰 [积分] 当前总积分: {result['integral']}")
            else:
                result["integral"] = "-"
        except Exception as exc:
            print(f"⚠️ [积分] 查询异常: {exc}")

        result["success"] = True
        return result

    except Exception as exc:
        result["error"] = traceback.format_exc().strip()
        print(f"❌ [账号] 执行失败: {exc}")
        return result


def build_notify(results: List[Dict[str, Any]]) -> str:
    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    content = f"""♻️ 雅迪智行积分任务结果

━━━━━━━━━━━━━━━━━━━━
🏁 总结：{success_count} 成功 / {fail_count} 失败
🕒 时间：{now_text()}
━━━━━━━━━━━━━━━━━━━━
"""

    for idx, res in enumerate(results, 1):
        icon = "✅" if res["success"] else "❌"

        content += f"""
🧩 账号 {idx}
👤 openid：{mask(res["openid"])}
🌐 代理：{res["proxyStatus"]}
📡 出口IP：{res["proxyIp"]}
🔐 Token：{res["token"]}
📝 签到：{res["signMsg"]}
💬 评论帖子：{res["commentMsg"]}
👀 浏览帖子：{res["browseMsg"]}
👍 点赞：{res["likeMsg"]}
💰 总积分：{res["integral"]}
{icon} 结果：{"成功" if res["success"] else "失败"}
"""

        if not res["success"]:
            content += f"❌ 原因：{res['error']}\n"

        content += "━━━━━━━━━━━━━━━━━━━━\n"

    return content


def main() -> None:
    log_title()

    if not OPENIDS:
        print("⚠️ 未配置账号 openid，请设置环境变量 WCS_OPENIDS（逗号分隔）或修改脚本顶部 OPENIDS")
        return

    results: List[Dict[str, Any]] = []

    for index, openid in enumerate(OPENIDS, 1):
        try:
            result = run_account(index, len(OPENIDS), openid)
            results.append(result)
        except Exception as exc:
            print(f"❌ [主程序] {openid} 执行异常: {exc}")
            results.append({
                "openid": openid,
                "success": False,
                "proxyStatus": "-",
                "proxyIp": "-",
                "token": "-",
                "signMsg": "-",
                "commentMsg": "-",
                "browseMsg": "-",
                "likeMsg": "-",
                "integral": "-",
                "error": traceback.format_exc().strip(),
            })

        if index < len(OPENIDS):
            print("⏳ [间隔] 等待 2s 后处理下一个账号")
            sleep(2)

    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🏁 雅迪智行积分任务执行完成                    ║")
    print(f"║ ✅ 成功: {success_count:<39}║")
    print(f"║ ❌ 失败: {fail_count:<39}║")
    print(f"║ 🕒 结束时间: {now_text():<32}║")
    print("╚" + "═" * 50 + "╝")

    notify = build_notify(results)
    print()
    print(notify)
    send_pushplus("雅迪智行积分任务", notify)


if __name__ == "__main__":
    main()
