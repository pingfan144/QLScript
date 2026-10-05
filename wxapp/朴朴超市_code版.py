#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
朴朴超市 签到组队 + 社群签到 动态 code 版

功能：
  1. wx_server 获取微信 code（POST {wx_server_url}/wx/code）
  2. silent_login 使用 code 换 token
  3. 每日签到
  4. 组队瓜分朴分（自动开团 + 账号间互相助力）
  5. 社群累计打卡
  6. 查询朴分
  7. PushPlus 推送
  8. 品赞代理，业务请求优先代理，失败直连兜底

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
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


APP_NAME = "朴朴超市小程序"
APPID = "wx122ef876a7132eb4"

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

CAUTH_URL = "https://cauth.pupuapi.com"
LOGIN_URL = f"{CAUTH_URL}/clientauth/user/society/miniapp/silent_login"
USER_INFO_URL = f"{CAUTH_URL}/clientauth/user/info"

J1_URL = "https://j1.pupuapi.com"
NEAR_LOCATION_URL = f"{J1_URL}/client/store/place/near_location_by_city/v2"
SIGN_INDEX_URL = f"{J1_URL}/client/game/sign/v2/index"
SIGN_URL = f"{J1_URL}/client/game/sign/v2"
TEAM_CODE_URL = f"{J1_URL}/client/game/coin_share/team/v3"
MY_TEAM_URL = f"{J1_URL}/client/game/coin_share/teams/{{team_code}}"
JOIN_TEAM_URL = f"{J1_URL}/client/game/coin_share/teams/{{team_code}}/join"
COIN_URL = f"{J1_URL}/client/coin"
SCENE_LAYOUT_URL = f"{J1_URL}/client/marketing/scenes/v6/layout"
TASK_GROUPS_URL = f"{J1_URL}/client/game/task_system/user_tasks/task_groups/{{activity_id}}"
COMMUNITY_SIGN_URL = f"{J1_URL}/client/game/task_system/user_tasks/task/{{activity_id}}/{{task_id}}/cumulative_clock"

SCENE_ID = "0199efbf-23bc-7480-b41f-65709cf61ae6"
STORE_ID = "8f3dfc01-3a82-4fbf-a681-94cc807b41a1"
PLACE_ID = "0195c06f-1236-7339-a5de-f3ca6bfebbf3"
CITY_ZIP = "350100"
PLACE_ZIP = "350102"

PP_VERSION = "2026081314"
PP_OS = "201"
COMMUNITY_PP_VERSION = "2026051101"
COMMUNITY_PP_OS = "001"

SIGN_V2 = "a643d6a2fac5e0e81c3f95352e9840ca"
SEAL_V2 = '{"a":"6fddd51d30fc3917611e9adb14dd82c34TUxVYiz","b":"rwjsAw21","c":"iFnPbyG6","f":"rk/R1MLjZUYFCnaxRmW0eKqiVjOJm6jdxVnKJ6ZFwbqlUTsyzDWbI6yh9UN5G4RzISwHnHUeGgFL8rwob2UgLcbNEbY5kDuQ0llb3kqmgFRHuGRlf0cP0GGgUuhdvO9IE1HcsVzqIskJrzwrbsgvxzZ3rGx3Z3gMELWdAo"}'
PP_SEQID = "yZg0H1JSNLnyY9K+ax7/NGMDZ+X9ZyNkAxaVGi1G/+tiDMgkAsCNXZ+rRmtw6ukDxxQZY8nnzkcVFEMik6wsbA=="

USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.46(0x18002e2c) NetType/WIFI Language/zh_CN "
    "miniProgram/wx122ef876a7132eb4"
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


def safe_data(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Safely extract 'data' from an API response, handling null/missing."""
    return resp.get("data") or {}


def log_title() -> None:
    print()
    print("╔" + "═" * 50 + "╗")
    print("║ ♻️ 朴朴超市签到组队+社群签到 code 版             ║")
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
        "Accept": "application/json",
        "pp-version": PP_VERSION,
        "pp-os": PP_OS,
        "Referer": f"https://servicewechat.com/{APPID}/797/page-frame.html",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def pupu_headers(account: Dict[str, Any]) -> Dict[str, str]:
    headers = common_headers(account["token"])
    headers.update({
        "pp-userid": account["user_id"],
        "pp-suid": account["suid"],
        "pp_storeid": account["store_id"],
        "pp-cityzip": str(account["city_zip"]),
        "Connection": "keep-alive",
    })
    return headers


def community_headers(account: Dict[str, Any]) -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "authorization": f"Bearer {account['token']}",
        "pp-userid": account["user_id"],
        "pp-suid": account["suid"],
        "pp_storeid": STORE_ID,
        "pp-placeid": PLACE_ID,
        "pp-cityzip": CITY_ZIP,
        "pp-placezip": PLACE_ZIP,
        "pp-version": COMMUNITY_PP_VERSION,
        "pp-os": COMMUNITY_PP_OS,
        "pp-seqid": PP_SEQID,
        "sign-v2": SIGN_V2,
        "seal-v2": SEAL_V2,
        "timestamp": str(int(time.time() * 1000)),
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://ma.pupumall.com",
        "referer": "https://ma.pupumall.com/",
        "x-requested-with": "com.tencent.mm",
    }


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
        response = request_with_proxy(
            "POST",
            LOGIN_URL,
            headers=common_headers(),
            json={"code": code},
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

        login_data = data.get("data") if isinstance(data, dict) else None
        if isinstance(login_data, dict) and (login_data.get("is_new_user") or login_data.get("is_bind_phone") is False):
            print("❌ [登录] 该微信账号在朴朴是新用户或未绑定手机号，静默登录不返回 token")
            print("    👉 请先用该微信号打开朴朴小程序，完成手机号授权登录一次，之后脚本即可自动登录")
            return None, data

        print(f"❌ [登录] 未识别 token 字段: {json_preview(data)}")
        return None, data
    except Exception as exc:
        print(f"❌ [登录] 请求异常: {exc}")
        return None, None


def api_get(openid: str, url: str, headers: Dict[str, str], proxies: Dict[str, str] | None) -> Dict[str, Any]:
    response = request_with_proxy(
        "GET",
        url,
        headers=headers,
        proxies=proxies,
        openid=openid,
    )
    try:
        return response.json()
    except Exception:
        return {
            "errcode": -1,
            "errmsg": f"JSON解析失败: {response.text[:300]}",
        }


def api_post(openid: str, url: str, headers: Dict[str, str], proxies: Dict[str, str] | None, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = request_with_proxy(
        "POST",
        url,
        headers=headers,
        json=payload,
        proxies=proxies,
        openid=openid,
    )
    try:
        return response.json()
    except Exception:
        return {
            "errcode": -1,
            "errmsg": f"JSON解析失败: {response.text[:300]}",
        }


def get_real_task(tasks: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    current_days = 0

    for task in tasks:
        current_days = max(current_days, int(task.get("finish_progress_value") or 0))

    next_day = current_days + 1

    for task in tasks:
        if int(task.get("task_progress_value") or 0) == next_day:
            return task

    return None


# ====================== token 缓存管理 ======================
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pupu_token_cache.json")


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


def get_cached_account(openid: str) -> Dict[str, Any] | None:
    cache = load_token_cache()
    data = cache.get(openid)
    if data and data.get("token"):
        return data
    return None


def set_cached_account(openid: str, token: str, user_id: Any, suid: Any) -> None:
    cache = load_token_cache()
    cache[openid] = {
        "token": token,
        "user_id": str(user_id or ""),
        "suid": str(suid or ""),
        "updateTime": datetime.now().isoformat(),
    }
    save_token_cache(cache)


def login_with_cache(openid: str, proxies: Dict[str, str] | None) -> Tuple[str | None, Dict[str, Any] | None]:
    """优先使用缓存 token（用户信息接口验证），失效自动 code 刷新"""
    cached = get_cached_account(openid)
    if cached:
        tmp_acc = {
            "token": cached["token"],
            "user_id": cached.get("user_id", ""),
            "suid": cached.get("suid", ""),
            "store_id": "",
            "city_zip": "",
        }
        print("🔍 [缓存] 验证 token")
        try:
            info_resp = api_get(openid, USER_INFO_URL, pupu_headers(tmp_acc), proxies)
            if info_resp.get("errcode") == 0:
                print("✅ [缓存] token 有效")
                return cached["token"], {"data": {"user_id": cached.get("user_id"), "suid": cached.get("suid")}}
        except Exception as exc:
            print(f"⚠️ [缓存] 验证异常: {exc}")
        print("⚠️ [缓存] token 已失效，重新登录")

    code = get_code(openid)
    if not code:
        return None, None

    token, raw_login = login_by_code(openid, code, proxies)
    if token:
        login_data = safe_data(raw_login)
        set_cached_account(openid, token, login_data.get("user_id"), login_data.get("suid"))
    return token, raw_login


def run_account(index: int, total: int, openid: str) -> Dict[str, Any]:
    result = {
        "openid": openid,
        "success": False,
        "proxyStatus": "未使用代理",
        "proxyIp": "-",
        "token": "-",
        "signMsg": "-",
        "teamMsg": "-",
        "communityMsg": "-",
        "coinMsg": "-",
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

    login_data = safe_data(raw_login)
    account = {
        "token": token,
        "user_id": str(login_data.get("user_id") or ""),
        "suid": str(login_data.get("suid") or ""),
        "store_id": "",
        "city_zip": "",
        "team_code": "",
        "team_need_help": False,
        "team_can_help": True,
        "team_max_help": 0,
        "team_helped_count": 0,
        "proxies": proxies,
    }
    result["account"] = account

    nick_name = login_data.get("nick_name") or ""
    print(f"👤 [用户] {nick_name} 登录成功")

    try:
        info_resp = api_get(openid, USER_INFO_URL, pupu_headers(account), proxies)
        if info_resp.get("errcode") == 0:
            info_data = safe_data(info_resp)
            phone = info_data.get("phone") or ""
            print(f"👤 [用户] 手机号 {mask(phone)}")
        else:
            print(f"⚠️ [用户] 查询用户信息失败: {info_resp.get('errmsg') or json_preview(info_resp, 300)}")

        lng = "119.31" + "".join(random.choices("0123456789", k=4))
        lat = "26.06" + "".join(random.choices("0123456789", k=4))
        loc_resp = api_get(openid, f"{NEAR_LOCATION_URL}?lng={lng}&lat={lat}", pupu_headers(account), proxies)
        if loc_resp.get("errcode") == 0:
            loc_list = safe_data(loc_resp)
            if isinstance(loc_list, list) and loc_list:
                loc = random.choice(loc_list)
                account["store_id"] = str(loc.get("service_store_id") or "")
                account["city_zip"] = str(loc.get("city_zip") or "")
                print(f"📍 [门店] {loc.get('name')} store_id={account['store_id']} city_zip={account['city_zip']}")
            else:
                print("⚠️ [门店] 附近门店列表为空")
        else:
            print(f"⚠️ [门店] 获取门店失败: {loc_resp.get('errmsg') or json_preview(loc_resp, 300)}")

        sign_resp = api_get(openid, SIGN_INDEX_URL, pupu_headers(account), proxies)
        if sign_resp.get("errcode") == 0:
            if safe_data(sign_resp).get("is_signed"):
                result["signMsg"] = "今天已签到"
                print(f"✅ [签到] {result['signMsg']}")
            else:
                sign_result = api_post(openid, f"{SIGN_URL}?supplement_id=", pupu_headers(account), proxies)
                if sign_result.get("errcode") == 0:
                    sign_data = safe_data(sign_result)
                    daily_coin = sign_data.get("daily_sign_coin") or 0
                    msg = f"签到成功: {daily_coin}积分"
                    for coupon in sign_data.get("coupon_list") or []:
                        condition = to_float(coupon.get("condition_amount")) / 100
                        discount = to_float(coupon.get("discount_amount")) / 100
                        msg += f", 满{condition:.2f}减{discount:.2f}券"
                    result["signMsg"] = msg
                    print(f"✅ [签到] {result['signMsg']}")
                else:
                    result["signMsg"] = sign_result.get("errmsg") or "签到失败"
                    print(f"⚠️ [签到] {result['signMsg']}")
        else:
            result["signMsg"] = sign_resp.get("errmsg") or "查询签到信息失败"
            print(f"⚠️ [签到] {result['signMsg']}")

        team_resp = api_post(openid, TEAM_CODE_URL, pupu_headers(account), proxies)
        if team_resp.get("errcode") == 0:
            team_data = team_resp.get("data") or {}
            team_code = team_data.get("team_id") if isinstance(team_data, dict) else team_data
            account["team_code"] = str(team_code or "")
            if not account["team_code"]:
                result["teamMsg"] = "获取组队码失败"
                print(f"⚠️ [组队] {result['teamMsg']}")
            else:
                my_team_resp = api_get(openid, MY_TEAM_URL.format(team_code=account["team_code"]), pupu_headers(account), proxies)
                if my_team_resp.get("errcode") == 0:
                    team_info = safe_data(my_team_resp)
                    status = team_info.get("status")
                    if status == 10:
                        account["team_need_help"] = True
                        account["team_max_help"] = int(team_info.get("target_team_member_num") or 0)
                        account["team_helped_count"] = int(team_info.get("current_team_member_num") or 0)
                        result["teamMsg"] = f"组队未完成: {account['team_helped_count']}/{account['team_max_help']}"
                        print(f"👥 [组队] {result['teamMsg']}")
                    elif status == 30:
                        reward = team_info.get("current_user_reward_coin") or 0
                        result["teamMsg"] = f"已组队成功, 获得了 {reward} 积分"
                        print(f"✅ [组队] {result['teamMsg']}")
                    else:
                        result["teamMsg"] = f"组队状态[{status}]"
                        print(f"⚠️ [组队] {result['teamMsg']}")
                else:
                    result["teamMsg"] = my_team_resp.get("errmsg") or "查询组队信息失败"
                    print(f"⚠️ [组队] {result['teamMsg']}")
        else:
            result["teamMsg"] = team_resp.get("errmsg") or "获取组队码失败"
            print(f"⚠️ [组队] {result['teamMsg']}")

        layout_resp = api_post(openid, SCENE_LAYOUT_URL, community_headers(account), proxies, payload={"scene_id": SCENE_ID})
        activity_id = ""
        if layout_resp.get("errcode") == 0:
            containers = safe_data(layout_resp).get("containers") or []
            for container in containers:
                for comp in container.get("components") or []:
                    content = comp.get("content") or {}
                    if "/task/list" in (content.get("route") or ""):
                        activity_id = content.get("link_id") or ""
                        break
                if activity_id:
                    break

        if not activity_id:
            result["communityMsg"] = "获取活动ID失败"
            print(f"⚠️ [社群] {result['communityMsg']}")
        else:
            print(f"✅ [社群] 获取活动ID成功: {activity_id}")

            tasks_resp = api_get(openid, TASK_GROUPS_URL.format(activity_id=activity_id), community_headers(account), proxies)
            if tasks_resp.get("errcode") != 0:
                result["communityMsg"] = tasks_resp.get("errmsg") or "获取任务失败"
                print(f"⚠️ [社群] {result['communityMsg']}")
            else:
                tasks = safe_data(tasks_resp).get("tasks") or []
                if not tasks:
                    result["communityMsg"] = "获取任务列表为空"
                    print(f"⚠️ [社群] {result['communityMsg']}")
                else:
                    task = get_real_task(tasks)
                    if not task:
                        result["communityMsg"] = "所有累计签到已完成"
                        print(f"✅ [社群] {result['communityMsg']}")
                    else:
                        clock_resp = api_post(
                            openid,
                            COMMUNITY_SIGN_URL.format(activity_id=activity_id, task_id=task.get("task_id")),
                            community_headers(account),
                            proxies,
                            payload={"task_group_round_id": task.get("task_group_round_id")},
                        )
                        if clock_resp.get("errcode") == 0:
                            result["communityMsg"] = f"社群累计签到成功: {task.get('task_name')}"
                            print(f"✅ [社群] {result['communityMsg']}")
                        elif "一天只能打卡一次" in (clock_resp.get("errmsg") or ""):
                            result["communityMsg"] = "今天已打卡"
                            print(f"✅ [社群] {result['communityMsg']}")
                        else:
                            result["communityMsg"] = clock_resp.get("errmsg") or "社群签到失败"
                            print(f"⚠️ [社群] {result['communityMsg']}")

        result["success"] = True
        return result

    except Exception as exc:
        result["error"] = traceback.format_exc().strip()
        print(f"❌ [账号] 执行失败: {exc}")
        return result


def join_team(needer: Dict[str, Any], helper: Dict[str, Any]) -> None:
    needer_account = needer["account"]
    helper_account = helper["account"]
    openid = needer["openid"]

    try:
        print(f"👥 [助力] 账号[{helper_account['user_id'][:8]}] 加入账号[{needer_account['user_id'][:8]}]的队伍")
        resp = api_post(
            openid,
            JOIN_TEAM_URL.format(team_code=needer_account["team_code"]),
            pupu_headers(helper_account),
            helper_account.get("proxies"),
        )

        if resp.get("errcode") == 0:
            helper_account["team_can_help"] = False
            needer_account["team_helped_count"] += 1
            print(f"✅ [助力] 入队成功: {needer_account['team_helped_count']}/{needer_account['team_max_help']}")
            if needer_account["team_helped_count"] >= needer_account["team_max_help"]:
                needer_account["team_need_help"] = False
                print("✅ [助力] 组队已满")
        else:
            msg = resp.get("errmsg") or "入队失败"
            code = resp.get("errcode")
            print(f"⚠️ [助力] 入队失败[{code}]: {msg}")
            if code == 100007:
                needer_account["team_need_help"] = False
            elif code == 100009:
                helper_account["team_can_help"] = False
    except Exception as exc:
        print(f"❌ [助力] 入队异常: {exc}")


def query_coin(result: Dict[str, Any], account: Dict[str, Any]) -> None:
    openid = result["openid"]

    try:
        resp = api_get(openid, COIN_URL, pupu_headers(account), account.get("proxies"))
        if resp.get("errcode") == 0:
            coin_data = safe_data(resp)
            balance = coin_data.get("balance") or 0
            expiring = coin_data.get("expiring_coin")
            expire_time = coin_data.get("expire_time")

            result["coinMsg"] = f"朴分: {balance}"
            print(f"💰 [朴分] {result['coinMsg']}")

            if expiring and expire_time:
                expire_date = datetime.fromtimestamp(int(expire_time) / 1000).strftime("%Y-%m-%d")
                result["coinMsg"] += f", {expiring}朴分将于{expire_date}过期"
                print(f"⚠️ [朴分] {expiring} 朴分将于 {expire_date} 过期")
        else:
            result["coinMsg"] = resp.get("errmsg") or "查询朴分失败"
            print(f"⚠️ [朴分] {result['coinMsg']}")
    except Exception as exc:
        result["coinMsg"] = f"查询朴分异常: {exc}"
        print(f"❌ [朴分] {result['coinMsg']}")


def build_notify(results: List[Dict[str, Any]]) -> str:
    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    content = f"""♻️ 朴朴超市签到组队+社群签到任务结果

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
👥 组队：{res["teamMsg"]}
🏘️ 社群：{res["communityMsg"]}
💰 朴分：{res["coinMsg"]}
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
                "teamMsg": "-",
                "communityMsg": "-",
                "coinMsg": "-",
                "error": traceback.format_exc().strip(),
            })

        if index < len(OPENIDS):
            print("⏳ [间隔] 等待 2s 后处理下一个账号")
            sleep(2)

    print()
    print("┌" + "─" * 50 + "┐")
    print("│ 👥 组队助力                                      │")
    print("└" + "─" * 50 + "┘")

    for needer in results:
        needer_account = needer.get("account")
        if not needer_account or not needer_account.get("team_need_help"):
            continue

        for helper in results:
            helper_account = helper.get("account")
            if helper_account is needer_account or not helper_account.get("team_can_help"):
                continue

            if not needer_account["team_need_help"]:
                break

            join_team(needer, helper)

    print()
    print("┌" + "─" * 50 + "┐")
    print("│ 💰 查询朴分                                      │")
    print("└" + "─" * 50 + "┘")

    for res in results:
        account = res.get("account")
        if account:
            query_coin(res, account)

    success_count = sum(1 for item in results if item["success"])
    fail_count = len(results) - success_count

    print()
    print("╔" + "═" * 50 + "╗")
    print("║ 🏁 朴朴超市任务执行完成                      ║")
    print(f"║ ✅ 成功: {success_count:<39}║")
    print(f"║ ❌ 失败: {fail_count:<39}║")
    print(f"║ 🕒 结束时间: {now_text():<32}║")
    print("╚" + "═" * 50 + "╝")

    send_pushplus("♻️ 朴朴超市签到组队+社群签到任务完成", build_notify(results))


if __name__ == "__main__":
    main()
