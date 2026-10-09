# -*- coding: utf-8 -*-
"""
回收蛙（wx5f671b00a9dfca58）签到脚本
=====================================
链路证据（反编译源码 hsw_recovery_wx）：
  - 签到动作  zm_reco/pages/welfare/welfare.js:317-344
      util.request_oa POST recycle/app/welfare/sign_in  body: user_id=uid
      （siteroot_oa = https://oa.syrecovery.com/api/，form 表单，无签名）
  - 签到状态  welfare.js:284-310 task_center_new（GET, we7 签名）→ data.qd_array[].is_qd
  - 登录(免手机号)  zm_reco/pages/my/my.js:448-462
      entry/wxapp/user_login（GET, we7 签名）data: m=zm_jyf, openid=wx_openid, type=wx
      → data.data.user.id 即 uid（user==0 表示未注册，需手机号注册，本脚本不处理）
  - code→openid  zm_reco/pages/authorization/authorization.js:166-188
      entry/wxapp/openid_new（GET, we7 签名）data: m=zm_jyf, code → openid/session_key/unionid
  - we7 签名  common/vendor.js:5432-5448 getSign:
      URL query 参数 + data 参数，按 name 排序去重，name=value 用 & 连接，
      md5(串 + siteInfo.token)。siteInfo 无 token 字段 → JS 里 token=undefined，
      实际拼接字面量 "undefined"（main.js:111-121 siteInfo 无 token/multiid，t 亦为 "undefined"）。

策略：优先使用本地缓存的 uid（持久业务登录态）；task_center_new 校验失效后，
通过 smallcat /wx/code 重新取 code → openid_new → user_login 换新 uid 并回写缓存。

用法：
  python 回收蛙_签到脚本.py              # 默认：实际执行签到（定时任务直接用这条）
  python 回收蛙_签到脚本.py --dry-run    # 干跑：只查状态，不签到（等价 HSW_DRY_RUN=1）
  python 回收蛙_签到脚本.py --execute    # 同默认，保留兼容
  python 回收蛙_签到脚本.py --selftest   # 本地签名构造自检（不联网）
环境变量：
  wx_server_url  smallcat 服务地址（默认 http://49.232.164.167:8787）
  wx_auth        smallcat AUTH默认留空（需在青龙配 wx_auth）
  hsw_openid     smallcat 账号 openid，多个用 & 分隔（默认内置 3 个）
  HSW_CACHE_FILE 缓存文件路径（默认与脚本同目录 hsw_cache.json）
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APPID = "wx5f671b00a9dfca58"

# main.js:111-121 siteInfo 常量（token/multiid 缺失 → 字面量 "undefined"）
SITEROOT = "https://www.syrecovery.com/app/index.php"
SITEROOT_OA = "https://oa.syrecovery.com/api/"
UNIACID = "373"
VERSION = "1.0.0"
MODULE = "zm_jyf"
TOKEN_LITERAL = "undefined"  # JS: m + (o = o || siteInfo.token) → m + undefined

WX_SERVER_URL = os.getenv("wx_server_url", "http://49.232.164.167:8787").rstrip("/")
WX_AUTH = os.getenv("wx_auth", "")
OPENIDS = [
    x.strip() for x in os.getenv(
        "hsw_openid",
        "owNAX6kivTB-QVRLU_MNkBe1O7N0&owNAX6qRxBBHqYApwo0Zd5ltlV8s&owNAX6pvBwZmrOpT8tvTc_OJueRA",
    ).split("&") if x.strip()
]

CACHE_FILE = os.getenv(
    "HSW_CACHE_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "hsw_cache.json"),
)

# 默认执行签到（脚本用途即定时签到）；--dry-run 或 HSW_DRY_RUN=1 才只读干跑
DRY_RUN = ("--dry-run" in sys.argv) or os.getenv("HSW_DRY_RUN") == "1"
EXECUTE = not DRY_RUN
SELFTEST = "--selftest" in sys.argv
# 手机号授权：2026-09-27 账号本人已明确授权（等价于客户端「授权手机号」点击），
# 仅用于未注册账号的一次性注册。设 HSW_PHONE_CONSENT=0 可关闭。
PHONE_CONSENT = os.getenv("HSW_PHONE_CONSENT", "1") == "1"


# ---------------------------------------------------------------- we7 签名
def we7_sign(url_query: dict, data: dict) -> str:
    """复刻 common/vendor.js getSign：URL 参数 + data 参数按 name 排序、去重、
    跳过空值，name=value 用 & 连接后 md5(串 + token字面量"undefined")。
    与 JS 语义对齐：同名参数 URL 侧优先；值为假(空串/0)的条目跳过。"""
    entries = []
    for k, v in list(url_query.items()) + list(data.items()):
        if k and v:  # JS: c[u].name && c[u].value
            entries.append((k, str(v)))
    # JS: sortBy("name") 稳定排序 + uniq(name) 保留首个 → URL 侧同名优先
    entries.sort(key=lambda kv: kv[0])
    seen, merged = set(), []
    for k, v in entries:
        if k in seen:
            continue
        seen.add(k)
        merged.append(f"{k}={v}")
    raw = "&".join(merged) + TOKEN_LITERAL
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def we7_get(do: str, data: dict, sessionid: str = "") -> dict:
    """复刻 util.request（GET 分支）：拼 URL、加 sign、发起请求。"""
    query = {
        "i": UNIACID,
        "t": TOKEN_LITERAL,   # siteInfo.multiid 未定义 → 字面量 "undefined"
        "v": VERSION,
        "from": "wxapp",
        "c": do.split("/")[0],
        "a": do.split("/")[1] if len(do.split("/")) > 1 else "",
        "do": do.split("/")[2] if len(do.split("/")) > 2 else "",
    }
    sign = we7_sign(query, data)
    params = dict(query)
    if sessionid:  # util.request: state=we7sid-{sessionid}（本流程 userInfo 为空，不带）
        params["state"] = "we7sid-" + sessionid
    params["sign"] = sign
    params.update({k: str(v) for k, v in data.items() if v is not None})
    url = SITEROOT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8").lstrip("\ufeff").strip()  # BOM 可能在前导空白后
    return json.loads(text)


def oa_post(path: str, data: dict) -> dict:
    """复刻 util.request_oa：POST siteroot_oa+path，form 表单，无签名。"""
    body = urllib.parse.urlencode({k: str(v) for k, v in data.items()}).encode()
    req = urllib.request.Request(
        SITEROOT_OA + path, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8-sig")
    try:
        return json.loads(text)
    except ValueError:
        return {"raw": text[:300]}


# ---------------------------------------------------------------- smallcat 取 code
def get_wx_code(openid: str) -> str:
    """取 wx.login code：YYB 面板模式（wx_auth 以 yyb_ 开头）走 /yyb/api/code，否则走 smallcat /wx/code。"""
    if WX_AUTH.startswith("yyb_"):
        base = WX_SERVER_URL if "yyb" in WX_SERVER_URL else "https://yyb.fuckinghigh.eu.org"
        qs = urllib.parse.urlencode({"appid": APPID, "openid": openid})
        req = urllib.request.Request(f"{base}/yyb/api/code?{qs}", headers={"X-API-Key": WX_AUTH})
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read().decode("utf-8"))
        if not payload.get("success") or not payload.get("code"):
            raise RuntimeError("YYB取code失败: " + str(payload.get("msg")))
        return payload["code"]

    body = json.dumps({"openid": openid, "appid": APPID}).encode()
    req = urllib.request.Request(
        WX_SERVER_URL + "/wx/code", data=body,
        headers={"auth": WX_AUTH, "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if not payload.get("status"):
        raise RuntimeError("取code失败: " + str(payload.get("message")))
    code = (payload.get("data") or {}).get("code")
    if not code:
        raise RuntimeError("取code失败: data.code 为空")
    return code


# ---------------------------------------------------------------- 缓存
def load_cache() -> dict:
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_uid(openid: str, uid) -> None:
    cache = load_cache()
    cache[openid] = {"uid": uid, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_FILE)


# ---------------------------------------------------------------- 业务链
def get_phone_raw(openid: str) -> dict:
    """取手机号授权加密数据：YYB 面板模式走 /yyb/api/get-phone-number，
    否则 POST {WX_SERVER_URL}/wx/getphonenumber（legacy encryptedData+iv）。"""
    if WX_AUTH.startswith("yyb_"):
        base = WX_SERVER_URL if "yyb" in WX_SERVER_URL else "https://yyb.fuckinghigh.eu.org"
        body = json.dumps({"appid": APPID, "openid": openid}).encode()
        req = urllib.request.Request(
            f"{base}/yyb/api/get-phone-number", data=body,
            headers={"X-API-Key": WX_AUTH, "Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read().decode("utf-8"))
        if not payload.get("success"):
            raise RuntimeError("YYB getphonenumber 失败: " + str(payload.get("msg")))
        wx_phone = (payload.get("data") or {}).get("wx_phone") or {}
        return {"encryptedData": wx_phone.get("encryptedData", ""), "iv": wx_phone.get("iv", "")}

    body = json.dumps({"openid": openid, "appid": APPID}).encode()
    req = urllib.request.Request(
        WX_SERVER_URL + "/wx/getphonenumber", data=body,
        headers={"auth": WX_AUTH, "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if not payload.get("status"):
        raise RuntimeError("getphonenumber 失败: " + str(payload.get("message")))
    return (payload.get("data") or {}).get("raw") or {}


def register(openid: str):
    """未注册兜底（authorization.js:163-268 完整注册链，需手机号授权）：
    /wx/code → openid_new(openid+session_key+unionid) → /wx/getphonenumber(encryptedData+iv)
    → phone_new 解析手机号 → oa recycle/app/login/user_login 注册 → uid 写缓存。
    返回 uid；失败抛异常。"""
    code = get_wx_code(openid)
    r1 = we7_get("entry/wxapp/openid_new", {"m": MODULE, "code": code})
    if r1.get("errno") != 0:
        raise RuntimeError("openid_new 失败 errno=%s" % r1.get("errno"))
    d1 = r1.get("data") or {}
    wx_openid, session_key, unionid = d1.get("openid"), d1.get("session_key", ""), d1.get("unionid", "")
    if not wx_openid:
        raise RuntimeError("openid_new 未返回 openid")

    raw = get_phone_raw(openid)
    enc_data, iv = raw.get("encryptedData"), raw.get("iv")
    if not enc_data or not iv:
        raise RuntimeError("getphonenumber 未返回 encryptedData/iv")

    # phone_new 响应是 JSON 文本（authorization.js:285 JSON.parse(n.data.trim())）
    r2 = we7_get("entry/wxapp/phone_new",
                 {"m": MODULE, "encryptedData": enc_data, "iv": iv, "session_key": session_key})
    text = r2.get("raw") if "raw" in r2 else json.dumps(r2, ensure_ascii=False)
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        raise RuntimeError("phone_new 响应非 JSON: " + str(text)[:200])
    if parsed.get("errno") != 0:
        raise RuntimeError("phone_new 失败 errno=%s（多为 session_key 与 encryptedData 不匹配）"
                           % parsed.get("errno"))
    phone = (parsed.get("data") or {}).get("phoneNumber")
    if not phone:
        raise RuntimeError("phone_new 未返回 phoneNumber")

    r3 = oa_post("recycle/app/login/user_login",
                 {"type": 1, "openid": wx_openid, "unionid": unionid,
                  "platform": 1, "phone": phone})  # platformCode("WX")=1
    if r3.get("code") != 1:
        raise RuntimeError("注册 user_login 失败: " + redact(r3)[:200])
    uid = (r3.get("data") or {}).get("user_id")
    if not uid:
        raise RuntimeError("注册成功但未返回 user_id")
    save_uid(openid, uid)
    print("注册成功，手机号 %s****%s 已绑定（uid 已写缓存）" % (phone[:3], phone[-2:]))
    return uid


def task_center(uid) -> dict:
    """只读状态查询（welfare.js:284-310 同参：m/uid/type=1）。"""
    return we7_get("entry/wxapp/task_center_new", {"m": MODULE, "uid": uid, "type": 1})


def status_valid(resp: dict) -> bool:
    """uid 有效性判定：errno==0 且 data 存在。"""
    if not isinstance(resp, dict):
        return False
    return resp.get("errno") == 0 and isinstance(resp.get("data"), (dict, list)) and resp.get("data")


def today_signed(resp: dict):
    """今日是否已签 —— **以顶层 data.is_qd 为准**（2026-09-29 实测校准）。

    实测证据（uid 540078，2026-09-29 16:55 周二）：
      签到前  顶层 is_qd=0 → qd_day=2 → jifen=20；提交后 顶层 is_qd=1 → qd_day=3 → jifen=30
      qd_array 里 is_day==1 的「周二」项 is_qd 恒为 1（签到前后都是 1）—— 该字段
      不能用作拦截依据，2026-09-29 11:30 的漏签就是被它误判掉的。
    返回 (is_qd or None, 判定来源说明)。
    """
    data = resp.get("data") or {}
    if "is_qd" in data:
        return data.get("is_qd"), "顶层is_qd"
    return None, "顶层无is_qd"


def status_snapshot(resp: dict) -> str:
    """日志用快照：顶层 is_qd/qd_day/积分 + 今日数组项（仅展示，不参与判定）"""
    data = resp.get("data") or {}
    u = data.get("user") or {}
    arr = data.get("qd_array") or []
    wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][time.localtime().tm_wday]
    today_item = next((it for it in arr if isinstance(it, dict) and it.get("title") == wd), None)
    return ("顶层is_qd=%s qd_day=%s jifen=%s 今日项(%s)=%s"
            % (data.get("is_qd"), data.get("qd_day"), u.get("jifen"), wd,
               json.dumps(today_item, ensure_ascii=False) if today_item else "n/a"))


def relogin(openid: str):
    """缓存失效兜底：/wx/code → openid_new → user_login(免手机号) → 新 uid。
    返回 (uid, 已缓存?)；user==0 表示未注册（需手机号授权注册），返回 None。"""
    code = get_wx_code(openid)
    resp = we7_get("entry/wxapp/openid_new", {"m": MODULE, "code": code})
    if resp.get("errno") != 0:
        raise RuntimeError("openid_new 失败 errno=%s" % resp.get("errno"))
    wx_openid = (resp.get("data") or {}).get("openid")
    if not wx_openid:
        raise RuntimeError("openid_new 未返回 openid")
    resp2 = we7_get("entry/wxapp/user_login",
                    {"m": MODULE, "openid": wx_openid, "type": "wx"})
    if resp2.get("errno") != 0:
        raise RuntimeError("user_login 失败 errno=%s" % resp2.get("errno"))
    user = (resp2.get("data") or {}).get("data", {}).get("user")
    if not user or user == 0:
        return None  # 未注册：注册链路需手机号授权，本脚本不处理
    uid = user.get("id")
    save_uid(openid, uid)
    return uid


def redact(obj) -> str:
    """脱敏输出：uid 只留长度，openid 打码。"""
    s = json.dumps(obj, ensure_ascii=False, default=str)
    for o in OPENIDS:
        if len(o) > 10:
            s = s.replace(o, o[:6] + "***" + o[-4:])
    return s


def run_account(openid: str) -> str:
    tag = "openid[" + openid[:8] + "…" + openid[-4:] + "]"
    cache = load_cache()
    uid = (cache.get(openid) or {}).get("uid")
    source = "缓存"

    # 1) 缓存 uid 优先，task_center_new 校验
    if uid:
        resp = task_center(uid)
        if not status_valid(resp):
            print(f"{tag} 缓存 uid 校验失效（errno={resp.get('errno')}），走 code 重登")
            uid, source = None, None
        else:
            data = resp.get("data") or {}
            print(f"{tag} 缓存 uid 有效，积分/签到面板已取到（qd_array 长度 {len(data.get('qd_array') or [])}）")

    # 2) 失效兜底：code → openid_new → user_login（未注册则走手机号注册链）
    if not uid:
        uid = relogin(openid)
        if uid is None:
            if not PHONE_CONSENT:
                print(f"{tag} 未注册且未开启手机号授权（HSW_PHONE_CONSENT=0），跳过")
                return "未注册"
            print(f"{tag} 未注册，走手机号注册链（已获账号本人授权）")
            uid = register(openid)
        source = "code重登"
        print(f"{tag} 重登成功获得新 uid（已写缓存）")

    # 3) 今日签到状态（判定只认顶层 is_qd；数组 is_day 项仅作展示）
    resp = task_center(uid)
    is_qd, basis = today_signed(resp)
    print(f"{tag} 状态快照: {status_snapshot(resp)} [{basis}]")
    if is_qd == 1:
        print(f"{tag} 今日已签到（顶层 is_qd=1），无需重复操作")
        return "已签到"
    if is_qd is None:
        print(f"{tag} 顶层未返回 is_qd，无法预判，仍按源码行为直接提交签到（后端负责防重）")

    # 4) 签到（源码 performSignIn 不做本地是否已签拦截，直接提交）
    if not EXECUTE:
        print(f"{tag} [干跑] 将执行 POST {SITEROOT_OA}recycle/app/welfare/sign_in user_id={uid}（去掉 --dry-run 即生效）")
        return "干跑"

    jifen_before = ((resp.get("data") or {}).get("user") or {}).get("jifen")
    sign_resp = oa_post("recycle/app/welfare/sign_in", {"user_id": uid})
    print(f"{tag} sign_in 响应: {redact(sign_resp)[:300]}")

    # 5) 复查：顶层 is_qd 翻 1 或积分增加 → 确认；sign_in code=1 → 后端已受理
    resp2 = task_center(uid)
    is_qd2, _ = today_signed(resp2)
    print(f"{tag} 复查快照: {status_snapshot(resp2)}")
    ok_backend = isinstance(sign_resp, dict) and sign_resp.get("code") == 1
    msg = str((sign_resp or {}).get("msg") or "") if isinstance(sign_resp, dict) else ""
    # 「今天已签过」也算成功：宽容匹配后端提示语（首次签到的响应是 code=1/msg=签到成功）
    already = re.search(r"已签|重复|already", msg, re.I) is not None
    jifen_after = ((resp2.get("data") or {}).get("user") or {}).get("jifen")
    gained = (isinstance(jifen_before, int) and isinstance(jifen_after, int)
              and jifen_after > jifen_before)
    if is_qd2 == 1:
        verdict = "签到成功（状态已确认，积分 %s→%s）" % (jifen_before, jifen_after)
    elif gained:
        verdict = "签到成功（积分 %s→%s）" % (jifen_before, jifen_after)
    elif ok_backend:
        verdict = "签到成功（后端 code=1，状态未刷新）"
    elif already:
        verdict = "已签到（后端提示重复，视为成功）"
    else:
        verdict = "签到失败：" + redact(sign_resp)[:160]
    print(f"{tag} {verdict}（uid来源:{source}）")
    return verdict


def selftest():
    """fixture：不联网，验证请求构造与签名复刻是否符合源码语义。"""
    q = {"i": "373", "t": "undefined", "v": "1.0.0", "from": "wxapp",
         "c": "entry", "a": "wxapp", "do": "task_center_new"}
    d = {"m": "zm_jyf", "uid": 123, "type": 1}
    s = we7_sign(q, d)
    # 人工展开：sorted(a,c,do,from,i,m,t,type,uid,v) + "undefined"
    expect_raw = ("a=wxapp&c=entry&do=task_center_new&from=wxapp&i=373&"
                  "m=zm_jyf&t=undefined&type=1&uid=123&v=1.0.0undefined")
    expect = hashlib.md5(expect_raw.encode()).hexdigest()
    assert s == expect, f"sign mismatch: {s} != {expect}"
    url = SITEROOT + "?" + urllib.parse.urlencode({**q, "sign": s, **{k: str(v) for k, v in d.items()}})
    assert url.startswith(SITEROOT + "?i=373&t=undefined&v=1.0.0"), url
    assert "c=entry" in url and "do=task_center_new" in url and "sign=" + s in url, url
    print("[selftest] 签名与 URL 构造校验通过")
    print("[selftest] 签名样本(非敏感):", s)

    # 今日判定 fixture（2026-09-29 漏签回归）：数组 is_day=1 项 is_qd=1，但顶层 is_qd=0 → 必须判未签
    buggy = {"errno": 0, "data": {"is_qd": 0, "qd_day": 2,
                                  "qd_array": [{"title": "周一", "is_qd": 1, "is_day": 0, "jf": "10"},
                                               {"title": "周二", "is_qd": 1, "is_day": 1, "jf": "10"},
                                               {"title": "周三", "is_qd": 0, "is_day": 0, "jf": "10"}]}}
    assert today_signed(buggy)[0] == 0, "顶层 is_qd=0 必须判为未签（勿再用数组 is_qd）"
    assert today_signed({"errno": 0, "data": {"is_qd": 1, "qd_day": 3}})[0] == 1, "顶层 is_qd=1 应判已签"
    assert today_signed({"errno": 0, "data": {}})[0] is None, "顶层无 is_qd 应返回 None"
    print("[selftest] 今日已签判定校验通过（顶层 is_qd 优先 + 数组误导字段回归）")


def main():
    if SELFTEST:
        selftest()
        if not any(a in sys.argv for a in ("--execute",)):
            return
    if not OPENIDS:
        print("未配置 hsw_openid")
        sys.exit(1)
    results = {}
    for idx, openid in enumerate(OPENIDS, 1):  # 单账号依次执行，一账号一次幂等动作
        key = "#%d %s…" % (idx, openid[:8])
        try:
            results[key] = run_account(openid)
        except Exception as e:  # noqa: BLE001
            results[key] = f"异常: {type(e).__name__}: {str(e)[:200]}"
    print("---- 汇总 ----")
    for k, v in results.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
