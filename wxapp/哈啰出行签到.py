#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
哈啰出行签到小程序动态 code 版

功能：
  1. wx_server 获取微信 code（POST {wx_server_url}/wx/code）
  2. /api?user.account.weixinEasyLogin 使用 code 换 token
  3. 每日签到（common.welfare.signAndRecommend）
  4. 领普通宝箱（common.welfare.open.treasure.box）
  5. 查询金币余额（user.taurus.pointInfo）
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
  pip install requests
  socks5 代理需：
  pip install requests[socks]
"""

from __future__ import annotations
import json
import os
import random
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

import requests


APP_NAME = "哈啰出行小程序"
APPID = "wxb937e3d0b3ca117e"

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

BASE_URL = "https://api.hellobike.com/api"
LOGIN_URL = f"{BASE_URL}?user.account.weixinEasyLogin"
SIGN_URL = f"{BASE_URL}?common.welfare.signAndRecommend"
BOX_URL = f"{BASE_URL}?common.welfare.open.treasure.box"
POINT_URL = f"{BASE_URL}?user.taurus.pointInfo"

SIGN_PAYLOAD = {
    "from": "h5",
    "systemCode": 62,
    "platform": 4,
    "version": "6.72.1",
    "action": "common.welfare.signAndRecommend",
}

BOX_PAYLOAD = {
    "from": "h5",
    "systemCode": 62,
    "platform": 4,
    "version": "7.0.15",
    "action": "common.welfare.open.treasure.box",
    "cityCode": "021",
    "boxType": 1,
}

POINT_PAYLOAD = {
    "from": "h5",
    "systemCode": 62,
    "platform": 4,
    "version": "6.72.1",
    "action": "user.taurus.pointInfo",
    "pointType": 1,
}

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 15; PKX110 Build/AP3A.240617.008; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 "
    "Mobile Safari/537.36 XWEB/1460249 MMWEBSDK/20240301 MMWEBID/8694 "
    "MicroMessenger/8.0.48.2580(0x28003035) WeChat/arm64 Weixin "
    "NetType/5G Language/zh_CN ABI/arm64 miniProgram/" + APPID
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


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def log_title() -> None:
    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🚲 哈啰出行签到动态 code 版                 ║")
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


def common_headers(token: str | None = None) -> Dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "xweb_xhr": "1",
        "Referer": f"https://servicewechat.com/{APPID}/824/page-frame.html",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if token:
        headers["token"] = token
    return headers


def extract_token(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None

    candidates = [
        data.get("token"),
        data.get("accessToken"),
        data.get("access_token"),
        data.get("jwt"),
    ]

    inner = data.get("data")
    if isinstance(inner, dict):
        candidates.extend([
            inner.get("token"),
            inner.get("accessToken"),
            inner.get("access_token"),
            inner.get("jwt"),
        ])

        user = inner.get("user")
        if isinstance(user, dict):
            candidates.extend([
                user.get("token"),
                user.get("accessToken"),
                user.get("access_token"),
                user.get("jwt"),
            ])

    for item in candidates:
        if item and item != "null":
            return str(item)

    return None


def login_by_code(openid: str, code: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    try:
        print("🔐 [登录] 使用 code 换 token")
        payload = {
            "riskControlData": {
                "systemCode": 64,
                "network": "5g",
                "deviceLon": 121.74488362630208,
                "deviceLat": 31.02707302517361,
                "batteryLevel": "32",
                "openId": "",
                "unionId": "",
            },
            "version": "7.0.15",
            "releaseVersion": "7.0.15",
            "systemCode": "64",
            "appName": "AppHellobikeWXSS",
            "mobileModel": "PKX110",
            "weChatVersion": "8.0.48",
            "mobileSystem": "Android 15",
            "SDKVersion": "3.3.5",
            "systemPlatform": "android",
            "from": "wechat",
            "action": "user.account.weixinEasyLogin",
            "iv": None,
            "wechatLoginCode": code,
            "pageName": "pages/personal/index/index",
            "encryptedData": None,
            "city": "",
            "adCode": "",
            "cityCode": "",
            "channel": 0,
            "longitude": 121.74488362630208,
            "latitude": 31.02707302517361,
            "flagType": "WECHAT_SEAMLESS",
            "extendValue": json.dumps({"openId": ""}),
            "ssid": "5p3269gK0sd5Zcp_2026-01-01",
        }
        response = request_with_proxy(
            "POST",
            LOGIN_URL,
            headers=common_headers(),
            json=payload,
            proxies=proxies,
            openid=openid,
        )

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text[:800]}

        token = extract_token(data)
        if token:
            print(f"✅ [登录] token 获取成功: {mask(token)}")
            return token, data

        print(f"❌ [登录] 未识别 token 字段: {json_preview(data)}")
        return None, data
    except Exception as exc:
        print(f"❌ [登录] 请求异常: {exc}")
        return None, None


def api_post(openid: str, url: str, token: str, proxies: Dict[str, str] | None, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = dict(payload)
    body["token"] = token

    response = request_with_proxy(
        "POST",
        url,
        headers=common_headers(),
        json=body,
        proxies=proxies,
        openid=openid,
    )
    try:
        return response.json()
    except Exception:
        return {
            "code": -1,
            "msg": f"JSON解析失败: {response.text[:300]}",
        }


# ====================== token 缓存管理 ======================
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hello_token_cache.json")


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


def get_cached_token(openid: str) -> str | None:
    cache = load_token_cache()
    data = cache.get(openid)
    if data and data.get("token"):
        return data["token"]
    return None


def set_cached_token(openid: str, token: str) -> None:
    cache = load_token_cache()
    cache[openid] = {"token": token, "updateTime": datetime.now().isoformat()}
    save_token_cache(cache)


def login_with_cache(openid: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    """优先使用缓存 token（金币接口验证），失效自动 code 刷新"""
    cached_token = get_cached_token(openid)
    if cached_token:
        print("🔍 [缓存] 验证 token")
        try:
            points_resp = api_post(openid, POINT_URL, cached_token, proxies, POINT_PAYLOAD)
            if points_resp.get("code") == 0 and points_resp.get("data"):
                print("✅ [缓存] token 有效")
                return cached_token, None
        except Exception as exc:
            print(f"⚠️ [缓存] 验证异常: {exc}")
        print("⚠️ [缓存] token 已失效，重新登录")

    code = get_code(openid)
    if not code:
        return None, None

    token, raw_login = login_by_code(openid, code, proxies)
    if token:
        set_cached_token(openid, token)
    return token, raw_login


def run_account(index: int, total: int, openid: str) -> Dict[str, Any]:
    result = {
        "openid": openid,
        "success": False,
        "proxyStatus": "未使用代理",
        "proxyIp": "-",
        "token": "-",
        "signMsg": "-",
        "boxMsg": "-",
        "points": "-",
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
    result["token"] = mask(token)

    try:
        sign_resp = api_post(openid, SIGN_URL, token, proxies, SIGN_PAYLOAD)
        sign_data = sign_resp.get("data") or {}

        if sign_resp.get("code") == 0 and sign_data:
            if sign_data.get("doSignThisTime"):
                result["signMsg"] = f"签到成功 +{sign_data.get('bountyCountToday', 0)}"
            elif sign_data.get("didSignToday"):
                result["signMsg"] = "今日已签到"
            else:
                result["signMsg"] = "签到完成"
            print(f"✅ [签到] {result['signMsg']}")
        else:
            result["signMsg"] = sign_resp.get("msg") or sign_resp.get("message") or "签到失败"
            print(f"⚠️ [签到] {result['signMsg']}")

        wait_time = random.randint(2, 5)
        print(f"⏳ [宝箱] 领取前等待 {wait_time}s")
        sleep(wait_time)

        box_resp = api_post(openid, BOX_URL, token, proxies, BOX_PAYLOAD)
        box_data = box_resp.get("data") or {}

        if box_resp.get("code") == 0 and box_data.get("success"):
            result["boxMsg"] = f"领宝箱成功 +{box_data.get('rewardAmount', 0)}"
            print(f"✅ [宝箱] {result['boxMsg']}")
        elif box_data.get("status") == "COOLING" or not box_data.get("canContinue"):
            result["boxMsg"] = "宝箱冷却中"
            print(f"⚠️ [宝箱] {result['boxMsg']}")
        else:
            result["boxMsg"] = box_resp.get("msg") or box_resp.get("message") or "宝箱领取失败"
            print(f"⚠️ [宝箱] {result['boxMsg']}")

        point_resp = api_post(openid, POINT_URL, token, proxies, POINT_PAYLOAD)
        point_data = point_resp.get("data") or {}

        if point_resp.get("code") == 0 and point_data:
            result["points"] = f"{point_data.get('points', 0)} 金币 ≈{point_data.get('amount', 0)} 元"
            print(f"💰 [金币] {result['points']}")
        else:
            result["points"] = "查询失败"
            print(f"⚠️ [金币] {result['points']}")

        result["success"] = True
        return result

    except Exception as exc:
        result["error"] = traceback.format_exc().strip()
        print(f"❌ [账号] 执行失败: {exc}")
        return result


def build_notify(results: List[Dict[str, Any]]) -> str:
    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    content = f"""🚲 哈啰出行签到任务结果

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
📦 宝箱：{res["boxMsg"]}
💰 金币：{res["points"]}
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
                "boxMsg": "-",
                "points": "-",
                "error": traceback.format_exc().strip(),
            })

        if index < len(OPENIDS):
            print("⏳ [间隔] 等待 2s 后处理下一个账号")
            sleep(2)

    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🏁 哈啰出行任务执行完成                      ║")
    print(f"║ ✅ 成功: {success_count:<39}║")
    print(f"║ ❌ 失败: {fail_count:<39}║")
    print(f"║ 🕒 结束时间: {now_text():<32}║")
    print("╚" + "═" * 50 + "╝")

    send_pushplus("🚲 哈啰出行签到任务完成", build_notify(results))


if __name__ == "__main__":
    main()
