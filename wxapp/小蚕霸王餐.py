#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
小蚕霸王餐小程序 code 发帖版

功能：
  1. wx_server 获取微信 code（POST {wx_server_url}/wx/code）
  2. /rpc 使用 code 换 token
  3. 查询用户信息
  4. 每日签到
  5. PushPlus 推送
  6. 品赞代理，业务请求优先代理，失败直连兜底

环境变量：
  wx_server_url     wx_server 服务地址，默认 http://49.232.164.167:8787
  wx_auth           wx_server 认证 token（auth 请求头）
  WCS_OPENIDS       账号 openid 列表，逗号分隔（也可直接改脚本顶部 OPENIDS）
  PLUSPLUS_TOKEN    PushPlus token，可选
  PROXY_API         品赞代理提取 API，可选
  PROXY_TYPE        http / socks5，默认 http
  XC_CITY           城市 adcode，默认 0，避免发布时暴露地区
  XC_PAGE_VERSION   小程序页面版本号，默认 785
  XC_SILK_ID        备用 silk_id，仅在接口解析失败时使用，可选
  XC_USER_ID        备用 user_id，仅在接口解析失败时使用，可选

依赖：
  pip install requests
  socks5 代理需：
  pip install requests[socks]
"""

from __future__ import annotations
import hashlib
import json
import os
import random
import sys
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

import requests

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


APP_NAME = "小蚕霸王餐小程序"
APPID = "wx52ae177248081591"
APP_ID = 20

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

XC_CITY = os.getenv("XC_CITY", "0")
XC_PAGE_VERSION = os.getenv("XC_PAGE_VERSION", "785")
XC_VERSION = "3.19.6.54"
XC_SILK_ID = os.getenv("XC_SILK_ID", "")
XC_USER_ID = os.getenv("XC_USER_ID", "")

SESSION_ID = str(uuid.uuid4())

RPC_URL = "https://gw.xiaocantech.com/rpc"

RPC_SERVICE_BY_PREFIX = {
    "WechatOpenapiService": "WechatOpenapi",
    "SilkwormService": "Silkworm",
    "ActivityTaskMobileService": "ActivityTask",
    "VipRightsService": "SilkwormVip",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 "
    "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI "
    "MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) "
    "UnifiedPCWindowsWechat(0xf2541c37) XWEB/25364"
)


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


def md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def log_title() -> None:
    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🐛 小蚕霸王餐小程序 code 版                    ║")
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


def get_code(openid: str) -> str | None:
    # YYB 面板模式：wx_auth 填 yyb_ 开头的 API Key，走 YYB 取码接口
    if WX_AUTH.startswith("yyb_"):
        base = WX_SERVER_URL if "yyb" in WX_SERVER_URL else "https://yyb.fuckinghigh.eu.org"
        try:
            resp = direct_session().get(
                f"{base}/yyb/api/code",
                params={"appid": APPID, "openid": openid},
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
    print(f"🔐 [授权] 请求 wx_server: appid={APPID} openid={mask(openid)}")

    try:
        response = direct_session().post(
            url,
            headers={"auth": WX_AUTH, "Content-Type": "application/json"},
            json={"appid": APPID, "openid": openid},
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


def make_x_nami(silk_id: Any) -> str:
    m = uuid.uuid4().hex
    x = str(int(silk_id or 0))
    return m[:4] + x + m[4:20 - len(x) - 4]


def rpc_headers(
    server_name: str,
    method_name: str,
    silk_id: Any = 0,
    user_id: Any = 0,
    token: str | None = None,
) -> Dict[str, str]:
    timestamp_ms = int(time.time() * 1000)
    x_nami = make_x_nami(silk_id)
    sign_seed = md5_hex(f"{server_name}.{method_name}".lower())
    x_ashe = md5_hex(sign_seed + str(timestamp_ms) + x_nami)

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": f"https://servicewechat.com/{APPID}/{XC_PAGE_VERSION}/page-frame.html",
        "servername": server_name,
        "methodname": method_name,
        "x-annie": "XC",
        "x-platform": "mini",
        "x-version": XC_VERSION,
        "version": XC_VERSION,
        "x-app-sr": str(APP_ID),
        "x-city": XC_CITY,
        "x-nami": x_nami,
        "x-garen": str(timestamp_ms),
        "x-ashe": x_ashe,
        "x-model": "microsoft microsoft",
        "x-session-id": SESSION_ID,
        "x-teemo": str(int(silk_id or 0)),
        "x-vayne": str(int(user_id or 0)),
        "xweb_xhr": "1",
    }

    if token:
        headers["x-sivir"] = token

    return headers


def rpc_post(
    openid: str,
    method_name: str,
    payload: Dict[str, Any],
    token: str | None,
    proxies: Dict[str, str] | None,
    *,
    silk_id: Any = 0,
    user_id: Any = 0,
) -> Dict[str, Any]:
    prefix = method_name.split(".", 1)[0]
    fallback = prefix[:-len("Service")] if prefix.endswith("Service") else prefix
    service_name = RPC_SERVICE_BY_PREFIX.get(prefix, fallback)
    headers = rpc_headers(
        service_name,
        method_name,
        silk_id=silk_id,
        user_id=user_id,
        token=token,
    )

    response = request_with_proxy(
        "POST",
        RPC_URL,
        headers=headers,
        json=payload,
        proxies=proxies,
        openid=openid,
    )

    try:
        data = response.json()
        if not isinstance(data, dict):
            return {"status": {"code": -1, "msg": f"非JSON对象: {response.text[:300]}"}}
        return data
    except Exception:
        return {
            "status": {"code": -1, "msg": f"JSON解析失败: {response.text[:300]}"},
        }


def login_by_code(openid: str, code: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    try:
        print("🔐 [登录] 使用 code 换 token")
        data = rpc_post(
            openid,
            "WechatOpenapiService.MiniLogin",
            {"code": code, "app_id": APP_ID},
            None,
            proxies,
            silk_id=0,
            user_id=0,
        )

        status = data.get("status") or {}
        if status.get("code") != 0:
            print(f"❌ [登录] 登录失败: {json_preview(data)}")
            return None, data

        user_info = data.get("user_info") or {}
        token_obj = user_info.get("token") or {}
        access_token = token_obj.get("access_token") or token_obj.get("token")

        if not access_token:
            print(f"❌ [登录] 未识别 token 字段: {json_preview(data)}")
            return None, data

        print("✅ [登录] token 获取成功")
        return access_token, data
    except Exception as exc:
        print(f"❌ [登录] 请求异常: {exc}")
        return None, None


def get_client_user_info(
    openid: str,
    token: str,
    proxies: Dict[str, str] | None,
    login_data: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    login_user_info = (login_data or {}).get("user_info") or {}
    user_id = login_user_info.get("user_id") or XC_USER_ID
    silk_id = login_user_info.get("silk_id") or XC_SILK_ID

    payload = {
        "inviter_silk_id": 0,
        "up": {"rcp": 1, "rc": 0, "dm": "microsoft", "re_ch": ""},
        "from_po_id": 0,
        "from_aid": 0,
        "app_id": APP_ID,
    }

    if silk_id:
        payload["silk_id"] = int(silk_id)
    else:
        payload["user_id"] = int(user_id)

    try:
        print("👤 [用户] 获取用户信息")
        data = rpc_post(
            openid,
            "SilkwormService.GetClientUserInfo",
            payload,
            token,
            proxies,
            silk_id=0,
            user_id=user_id,
        )

        status = data.get("status") or {}
        if status.get("code") != 0:
            print(f"❌ [用户] 获取用户信息失败: {json_preview(data)}")
            return None, data

        user_info = data.get("user_info") or {}
        if not user_info.get("silk_id"):
            print(f"❌ [用户] 未解析到 silk_id: {json_preview(data)}")
            return None, data

        print("✅ [用户] 用户信息获取成功")
        return user_info, data
    except Exception as exc:
        print(f"❌ [用户] 请求异常: {exc}")
        return None, None


def sign_in(
    openid: str,
    token: str,
    proxies: Dict[str, str] | None,
    silk_id: Any,
    user_id: Any,
) -> Dict[str, Any]:
    try:
        print("📅 [签到] 查询签到状态")
        days_data = rpc_post(
            openid,
            "VipRightsService.UserSignInDays",
            {"silk_id": int(silk_id), "app_id": APP_ID},
            token,
            proxies,
            silk_id=silk_id,
            user_id=user_id,
        )

        days = int(days_data.get("days", 0) or 0)
        if days_data.get("is_today_signed") is True:
            msg = f"今日已签到，连续 {days} 天"
            print(f"✅ [签到] {msg}")
            return {"success": True, "msg": msg, "data": days_data}

        print("✅ [签到] 今日未签到，开始签到")
        sign_data = rpc_post(
            openid,
            "ActivityTaskMobileService.SignIn",
            {"silk_id": int(silk_id), "app_id": APP_ID},
            token,
            proxies,
            silk_id=silk_id,
            user_id=user_id,
        )

        status = sign_data.get("status") or {}
        code = status.get("code")
        msg = status.get("msg") or sign_data.get("msg") or "签到失败"

        if code == 0:
            point = sign_data.get("point")
            if point is not None:
                msg = f"签到成功，获得 {point}，连续 {days} 天"
            else:
                msg = f"签到成功，连续 {days} 天"
            print(f"✅ [签到] {msg}")
            return {"success": True, "msg": msg, "data": sign_data}

        if code == 10001 or "重复" in str(msg) or "已签" in str(msg):
            msg = f"今日已签到，连续 {days} 天"
            print(f"✅ [签到] {msg}")
            return {"success": True, "msg": msg, "data": sign_data}

        print(f"❌ [签到] {msg}: {json_preview(sign_data, 300)}")
        return {"success": False, "msg": str(msg), "data": sign_data}
    except Exception as exc:
        print(f"❌ [签到] 请求异常: {exc}")
        return {"success": False, "msg": str(exc), "data": None}


# ====================== token 缓存管理 ======================
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xiaocan_token_cache.json")


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
    except Exception as exc:
        print(f"❌ [缓存] 保存失败: {exc}")


def get_cached_session(openid: str) -> Dict[str, Any] | None:
    cache = load_token_cache()
    data = cache.get(openid)
    if data and data.get("token"):
        return data
    return None


def set_cached_session(openid: str, token: str, user_id: Any, silk_id: Any) -> None:
    cache = load_token_cache()
    cache[openid] = {
        "token": token,
        "user_id": user_id,
        "silk_id": silk_id,
        "updateTime": datetime.now().isoformat(),
    }
    save_token_cache(cache)


def login_with_cache(openid: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    """优先使用缓存 token（用户信息接口验证），失效自动 code 刷新"""
    cached = get_cached_session(openid)
    if cached:
        fake_login = {"user_info": {"user_id": cached.get("user_id"), "silk_id": cached.get("silk_id")}}
        print("🔍 [缓存] 验证 token")
        try:
            info, _ = get_client_user_info(openid, cached["token"], proxies, fake_login)
            if info:
                print("✅ [缓存] token 有效")
                return cached["token"], fake_login
        except Exception as exc:
            print(f"⚠️ [缓存] 验证异常: {exc}")
        print("⚠️ [缓存] token 已失效，重新登录")

    code = get_code(openid)
    if not code:
        return None, None

    token, raw_login = login_by_code(openid, code, proxies)
    if token:
        lu = (raw_login or {}).get("user_info") or {}
        set_cached_session(openid, token, lu.get("user_id"), lu.get("silk_id"))
    return token, raw_login


def run_account(index: int, total: int, openid: str) -> Dict[str, Any]:
    result = {
        "openid": openid,
        "success": False,
        "proxyStatus": "未使用代理",
        "proxyIp": "-",
        "token": "-",
        "signMsg": "-",
        "error": "",
    }

    log_account_header(index, total, openid)

    proxies, proxy_ip = get_valid_proxy(openid)
    result["proxyStatus"] = "使用专属代理" if proxies else "使用直连"
    result["proxyIp"] = proxy_ip or "-"

    sleep(PROXY_FETCH_INTERVAL)

    delay = random.randint(2, 6)
    print(f"⏳ [延迟] 启动延迟 {delay}s")
    sleep(delay)

    token, raw_login = login_with_cache(openid, proxies)
    if not token:
        result["error"] = f"登录失败: {json_preview(raw_login)}"
        return result

    result["token"] = "已获取"

    try:
        user_info, raw_user = get_client_user_info(openid, token, proxies, raw_login)
        if not user_info:
            result["error"] = f"获取用户信息失败: {json_preview(raw_user)}"
            return result

        silk_id = user_info.get("silk_id")
        user_id = user_info.get("user_id") or (raw_login or {}).get("user_info", {}).get("user_id") or 0

        sign_result = sign_in(openid, token, proxies, silk_id, user_id)
        result["signMsg"] = sign_result["msg"]
        result["success"] = sign_result["success"]
        return result

    except Exception as exc:
        result["error"] = traceback.format_exc().strip()
        print(f"❌ [账号] 执行失败: {exc}")
        return result


def build_notify(results: List[Dict[str, Any]]) -> str:
    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    content = f"""🐛 小蚕霸王餐任务结果

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
📝 签到：{res["signMsg"]}
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
                "error": traceback.format_exc().strip(),
            })

        if index < len(OPENIDS):
            print("⏳ [间隔] 等待 2s 后处理下一个账号")
            sleep(2)

    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🏁 小蚕霸王餐任务执行完成                      ║")
    print(f"║ ✅ 成功: {success_count:<39}║")
    print(f"║ ❌ 失败: {fail_count:<39}║")
    print(f"║ 🕒 结束时间: {now_text():<32}║")
    print("╚" + "═" * 50 + "╝")

    send_pushplus("🐛 小蚕霸王餐任务完成", build_notify(results))


if __name__ == "__main__":
    main()
