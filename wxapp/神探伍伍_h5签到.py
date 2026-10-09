#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
神探伍伍 有赞店铺签到（H5 Cookie 版）

背景（2026-10-09 逆向定论）：
  神探伍伍是「有赞」系小程序（appid wx44c7bf07c3c0325f，店铺 tuicashier.youzan.com，
  kdt_id=156883710，移动域名 shop157075878.m.youzan.com）。
  它的签到接口 checkinV2.json 有一道门禁：报 1000030102「手机号未授权」，
  真实依据是 platformInfo.hasRelatedMobile —— 店铺会员档案是否关联过手机号。

  微信小程序取码（wx_server / YYB 取 code）换到的登录态「不含会员/手机号档案」，
  所以走「微信 code → access_token 查询参数」这条常规路线，永远被 1000030102 拦。
  正解：用「已注册会员卡 + 已关联手机号」账号的 H5 登录态（KDTSESSIONID + open_token 两个 Cookie）。

  本脚本即走 H5 Cookie 路线，只用两个 Cookie：
    KDTSESSIONID  （.youzan.com 域，passport 会话）
    open_token    （shop{}.m.youzan.com 域，含 accessToken）

环境变量（青龙面板配置）：
  YZ_KDTSESSIONID   必填，有赞 passport 会话（浏览器 H5 登录后 cookies 里的 KDTSESSIONID）
  YZ_OPEN_TOKEN     必填，open_token Cookie 的完整 JSON 值（含 accessToken）
  YZ_KDT_ID         店铺号，默认 156883710
  YZ_CHECKIN_ID     签到活动 id，默认 4613526
  PLUSPLUS_TOKEN    可选，PushPlus 推送

账号扩展：KDTSESSIONID / OPEN_TOKEN 均支持逗号分隔的多账号（一一对应），
          多账号时用 YZ_KDTSESSIONID / YZ_OPEN_TOKEN 逗号分隔。

依赖：pip install requests

注意（诚实说明）：
  open_token 里 accessToken 有效期约 7 天，过期后本脚本会检测到登录态失效并明确报错。
  刷新方式（已实现全自动）：宿主机跑「有赞_token自动刷新.py」（headless Chromium + dcf-ocr
  自动过腾讯滑块 + 账密登录，已实测 24 秒全流程通过），拿到新 KDTSESSIONID/open_token 后
  自动更新本脚本读取的环境变量 YZ_KDTSESSIONID / YZ_OPEN_TOKEN，无需人工干预。
"""

from __future__ import annotations
import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


APP_NAME = "神探伍伍"
APPID = "wx44c7bf07c3c0325f"

KDT_ID = os.getenv("YZ_KDT_ID", "156883710")
CHECKIN_ID = os.getenv("YZ_CHECKIN_ID", "4613526")

SHOP_DOMAIN = f"shop157075878.m.youzan.com"  # 神探伍伍店铺固定移动域名
BASE = f"https://{SHOP_DOMAIN}"

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1")

PLUSPLUS_TOKEN = os.getenv("PLUSPLUS_TOKEN", "")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mask(value: Any) -> str:
    value = str(value or "")
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-6:]}"


def json_preview(data: Any, limit: int = 400) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)[:limit]
    except Exception:
        return str(data)[:limit]


def split_list(raw: str) -> List[str]:
    # open_token 是 JSON，内含逗号，故多账号用「换行」或「|」分隔，不用逗号
    raw = raw.replace("，", ",").replace("\r", "\n").replace("|", "\n")
    return [x.strip() for x in raw.split("\n") if x.strip()]


KDTSESSIONID_LIST = split_list(os.getenv("YZ_KDTSESSIONID", ""))
OPEN_TOKEN_LIST = split_list(os.getenv("YZ_OPEN_TOKEN", ""))


def build_session(kdtsessionid: str, open_token: str) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": BASE + "/",
    })
    s.cookies.set("KDTSESSIONID", kdtsessionid, domain=".youzan.com")
    s.cookies.set("open_token", open_token, domain=SHOP_DOMAIN)
    return s


def get_state(s: requests.Session) -> Dict[str, Any]:
    """查签到活动状态（读接口，含 isCheckin）"""
    url = f"{BASE}/wscump/checkin/get_activity_by_yzuid_v2.json?checkinId={CHECKIN_ID}&kdt_id={KDT_ID}"
    r = s.get(url, timeout=25, allow_redirects=False)
    try:
        return r.json()
    except Exception:
        return {"code": -1, "msg": f"JSON解析失败: {r.text[:200]}"}


def do_checkin(s: requests.Session) -> Dict[str, Any]:
    """执行签到（GET checkinV2.json 即签到动作）"""
    url = f"{BASE}/wscump/checkin/checkinV2.json?checkinId={CHECKIN_ID}&kdt_id={KDT_ID}"
    r = s.get(url, timeout=25, allow_redirects=False)
    try:
        return r.json()
    except Exception:
        return {"code": -1, "msg": f"JSON解析失败: {r.text[:200]}"}


def send_pushplus(title: str, content: str) -> None:
    if not PLUSPLUS_TOKEN:
        return
    try:
        requests.post(
            "https://www.pushplus.plus/send",
            json={"token": PLUSPLUS_TOKEN, "title": title, "content": content, "template": "txt"},
            timeout=10,
        )
    except Exception as exc:
        print(f"❌ [PushPlus] 推送失败: {exc}")


def run_account(idx: int, total: int, kdtsessionid: str, open_token: str) -> Dict[str, Any]:
    result = {"idx": idx, "signMsg": "-", "success": False, "error": ""}
    print()
    print("┌" + "─" * 50 + "┐")
    print(f"│ 🧩 账号 {idx} / {total:<37}│")
    print(f"│ 🎫 KDT {mask(kdtsessionid):<40}│")
    print("└" + "─" * 50 + "┘")

    try:
        s = build_session(kdtsessionid, open_token)

        st = get_state(s)
        if st.get("code") != 0:
            # 登录态失效的典型表现：userId must be >= 1 / 未登录
            msg = st.get("msg") or json_preview(st)
            if "userId" in str(msg) or "登录" in str(msg):
                result["signMsg"] = "登录态失效，需重新登录刷新 open_token"
                result["error"] = msg
                print(f"❌ [签到] {result['signMsg']}（{msg}）")
            else:
                result["signMsg"] = f"查询状态失败: {msg}"
                print(f"❌ [签到] {result['signMsg']}")
            return result

        data = st.get("data") or {}
        is_checkin = bool(data.get("isCheckin"))
        continues = data.get("continuesDay", 0)
        if is_checkin:
            result["signMsg"] = f"今日已签到（连续 {continues} 天）"
            result["success"] = True
            print(f"✅ [签到] {result['signMsg']}")
            return result

        print(f"⏳ [签到] 今日未签，执行签到...")
        res = do_checkin(s)
        code = res.get("code")
        msg = res.get("msg") or json_preview(res)
        if code == 0:
            result["signMsg"] = "签到成功"
            result["success"] = True
            print(f"✅ [签到] {result['signMsg']}")
        elif code == 1000030071:
            result["signMsg"] = "已达最大参与次数（今日已签/周期满）"
            result["success"] = True
            print(f"✅ [签到] {result['signMsg']}")
        elif code == 1000030102:
            result["signMsg"] = "手机号未授权（会员档案未关联手机号）"
            result["error"] = msg
            print(f"❌ [签到] {result['signMsg']} —— 需该账号在 H5 注册会员卡并关联手机号")
        elif code == 1000000002:
            result["signMsg"] = "未注册会员（userId must be >= 1）"
            result["error"] = msg
            print(f"❌ [签到] {result['signMsg']} —— 需该账号先注册店铺会员")
        else:
            result["signMsg"] = f"签到失败[{code}]: {msg}"
            result["error"] = msg
            print(f"❌ [签到] {result['signMsg']}")

    except Exception as exc:
        result["error"] = traceback.format_exc().strip()
        result["signMsg"] = f"执行异常: {exc}"
        print(f"❌ [账号] {result['signMsg']}")

    return result


def build_notify(results: List[Dict[str, Any]]) -> str:
    ok = sum(1 for r in results if r["success"])
    content = f"🔔 {APP_NAME} 签到结果\n\n━━━━━━━━━━━━━━━━\n🏁 {ok}/{len(results)} 成功\n🕒 {now_text()}\n━━━━━━━━━━━━━━━━\n"
    for r in results:
        icon = "✅" if r["success"] else "❌"
        content += f"\n🧩 账号 {r['idx']} {icon}\n📝 {r['signMsg']}\n"
        if r["error"]:
            content += f"⚠️ {r['error']}\n"
    return content


def main() -> None:
    print("╔" + "═" * 50 + "╗")
    print(f"║ 🔔 {APP_NAME} 有赞签到（H5 Cookie 版）     ║")
    print(f"║ 🕒 {now_text():<38}║")
    print("╚" + "═" * 50 + "╝")

    if not KDTSESSIONID_LIST or not OPEN_TOKEN_LIST:
        print("⚠️ 未配置 YZ_KDTSESSIONID / YZ_OPEN_TOKEN 环境变量")
        return
    if len(KDTSESSIONID_LIST) != len(OPEN_TOKEN_LIST):
        print("⚠️ YZ_KDTSESSIONID 与 YZ_OPEN_TOKEN 数量不一致（需一一对应）")
        return

    results = []
    for i, (kdt, token) in enumerate(zip(KDTSESSIONID_LIST, OPEN_TOKEN_LIST), 1):
        results.append(run_account(i, len(KDTSESSIONID_LIST), kdt, token))
        if i < len(KDTSESSIONID_LIST):
            time.sleep(1.5)

    ok = sum(1 for r in results if r["success"])
    print()
    print("╔" + "═" * 50 + "╗")
    print(f"║ 🏁 {APP_NAME} 执行完成                       ║")
    print(f"║ ✅ 成功: {ok:<39}║")
    print(f"║ ❌ 失败: {len(results) - ok:<39}║")
    print(f"║ 🕒 {now_text():<38}║")
    print("╚" + "═" * 50 + "╝")

    send_pushplus(f"{APP_NAME} 签到完成", build_notify(results))


if __name__ == "__main__":
    main()
