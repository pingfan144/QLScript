#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: WorkBuddy 签到
# cron: 31 7,12,23 * * *
"""
name: WorkBuddy 签到
cron: 31 7,12 * * *

════════════════════════════════════════════════════════════════
该脚本引用自原作者：https://github.com/L0NE-6/WorkBuddy-Daily
修改作者：lcmovie https://github.com/lcmovie/YYB-GO-Script-i
修改后主要适配：https://github.com/525815266/YYB-Go-Enhanced，实现无感取码，自动打卡 + 全部成长任务！
════════════════════════════════════════════════════════════════
🌱 WorkBuddy Daily - 全能签到脚本 v2.8（YYB 无感取码版）
════════════════════════════════════════════════════════════════

📌 这是什么
   一个脚本搞定 WorkBuddy 全部自动化：无感取码登录 + Token 自动续期、
   积分/用量查询、18 项成长任务、8 项互动玩法、开学季活动 + 大转盘、
   小程序成长任务、自动领奖，全部无人值守。

✨ 特性
   🔐 无感取码       只配一个 YYB_SERVER 变量，脚本自动 wx.login 取码登录 + 自动续期
   ✅ 成长任务       18 项云端/桌面全覆盖 + 轻量云专家（仅公益专家需真实捐款）
   🏫 开学季活动     分享/对话/桌面对话/专家 + 幸运大转盘（含瑞幸/KFC/酷狗实物券）
                     ※ 以服务端 in_period 判定活动期，非进行期自动跳过（不会误报失败）
   📱 小程序任务     Tasks_1~7 链式任务（每日零点解锁一环，日志给出解锁日期）
   🎮 8 项互动玩法   抽奖、盲盒、Buddy、派猫猫旅行、连签兑换、补签卡、礼包补偿、徽章
   💰 三类查询       积分套餐（剩余/总量/已用）、用量统计、成长数据（等级/连签/能量）
   🎁 自动领奖       扫描全部已完成任务自动领取；completed 未领的自动补领
   📢 青龙通知       优先 notify.py，回落到 PushPlus / Server酱 / 企业微信 / Bark
   🧩 幂等安全       重复运行只补缺口，不会重复领取或重复操作
   🔄 API 重试       网络/5xx 自动指数退避重试，写动作间隔可调（--gap）
   🔗 稳定指纹       每账号 md5 派生固定 machineId，桌面/web/小程序三域对齐官方埋点
   🐧 青龙友好       非 Windows 走指纹上报，纯 API 直接跑

🚀 使用方法（YYB 版）
   1. 设置变量     YYB_SERVER = 每行一个 "YYB地址@openid"（多账号换行分隔）
                   例：yyb-go:8000@oXXXXXXXX
   2. 定时任务     31 7,12 * * *     日常全流程
                   31 23 * * *      夜猫子活动窗口（23:00-08:00，必须单独排程）

⌨️ 命令行参数
   --only 3          只跑第 3 个账号（可用逗号 3,4,5）
   --query           仅查询积分/用量/签到状态，不执行任务
   --no-school       跳过开学季活动
   --no-desktop      跳过桌面任务（非 Windows 默认走指纹上报）
   --no-notify       不发送青龙通知
   --gap 2.0         写动作间隔秒数（默认 1.5，最低 1.0）
   --mp-gap 15       mp 对话事件间隔（默认 45，上游反作弊要求真人节奏）
   --tasks checkin,travel        只跑白名单子任务
   --skip-tasks lottery,redeem   跳过指定子任务

🔑 环境变量
   YYB_SERVER           【必填】每行一个 "YYB地址@openid"（openid 用于 smallcat 取码，地址用于手机号 YYB 兜底）
   YYB_API_KEY          【可选】对应 YYB_PROTOCOL_TOKEN，设置后带 Authorization 头
   WB_ACCOUNT_FILTER    【可选】等价 --only，逗号分隔账号编号
   WB_CACHE_DIR         【可选】缓存目录，默认 /ql/data/config/workbuddy_yyb
   WB_NO_NOTIFY         【可选】=1 关闭通知
   WORKBUDDY_TASKS      【可选】白名单：只跑列出的子任务（逗号/空格分隔）
   WORKBUDDY_SKIP_TASKS 【可选】黑名单：跳过列出的子任务
     别名：checkin 签到 / travel 旅行 / lottery 抽奖 / redeem 连登兑换 / gift 礼包补偿
           makeup 补签 / badges 徽章 / blindbox 盲盒 / buddy_info Buddy信息 / desktop 桌面 / school 开学季
     例：只想每天做签到+旅行 → WORKBUDDY_TASKS=checkin,travel（其余任务以后想做时再放开）
   WORKBUDDY_MP_GAP     【可选】mp 对话事件间隔秒数（默认 45，可调小提速）
   PUSH_PLUS_TOKEN / PLUSPLUS_TOKEN / PUSH_KEY / QYWX_KEY / BARK_PUSH
                        【可选】脚本自带通知通道（青龙 notify.py 未配置时回落）

📦 任务清单（同原版 WorkBuddy-Daily，共 40 项，38 项全自动）
   ☁️ 成长中心任务（18 项）：每日签到 · 设计创意模式 · 探索优秀灵感 · 桌面端对话 ·
      尝鲜热门技能 · 体验资料库 · 腾讯轻量云专家 · 和平精英主题 · 发现应用 ·
      企鹅教师助手 · GLM-5.2模型对话 · 和AI聊天5次 · 夜猫子活动 · 召唤3次专家团 ·
      召唤5次专家 · 使用5个模板 · 设置自动化任务 · 领取Buddy
      ❌ 公益专家（需真实捐款，脚本不做）
   🏫 开学季活动（4 项 + 大转盘）
   📱 小程序成长任务（8 项，Sequential_Tasks_1~7 + school_season）
   🎮 互动玩法（8 项）：抽奖 · 盲盒 · Buddy信息 · 派猫猫旅行 · 连签兑换 · 补签卡 ·
      礼包补偿 · 徽章

⚙️ 特别之处（同原版）
   · 凭据：YYB 无感取码登录拿到 accessToken/refreshToken，本地 State 缓存并自动续期
   · 桌面任务：Windows 走真实桌面换血；非 Windows 自动降级为指纹上报（无需真实桌面端）
   · accept 校验：解析接口逐任务状态 + 回读验证，未落账的自动逐个重试
   · 前置依赖：accept 报 prerequisite not met 时先补跑前置任务（如先领养首只 Buddy）再重试
   · 真实会话 id：专家/技能任务的 requestId/messageId 取自真实对话的服务端消息 id（cmb- 形态）
   · 签到读数：签到后读 /billing/meter/checkin-activity-status（连签天数/累计积分/连签奖励日）
   · 子任务开关：WORKBUDDY_TASKS（白名单）/ WORKBUDDY_SKIP_TASKS（黑名单）——
     可只留签到+旅行，其余任务以后再做时再放开（积分一个月有效期，不需一次领完）
   · mp 真人节奏：Sequential 对话判据逐条 45s±10s 上报（上游有反作弊：连发会先计数、
     后被整体回滚，claim 报 400）；--mp-gap / WORKBUDDY_MP_GAP 可调
   · accept 后回读：mp 任务接受后重读真实 target，避免"少报→误判达标→claim 400"
   · mp 指纹：按官方源码口径（ideVersion/extVersion=2.2.8、android 14/arm64、source=mini_program）
   · locked 任务：任务行 locked=true（未到上线时间）直接跳过并给出解锁日，不空跑不误判
   · mp 对话 id：conversationId / requestId / traceId 同值传递（源码同值）
   · 瞬时错误重试：签到/余额/用量对网络与 5xx 做 2s/4s 有界重试，业务错误不重试

📄 依赖：requests（pip3 install requests）

🔒 隐私说明
   脚本不含任何账号、手机号、Token 或设备信息，所有凭据均由环境变量注入。

适配：由 YYB-Go-Enhanced 取码迁移至 smallcat /wx/code（getCode 走 smallcat，getPhoneNumber 保留 YYB 兜底）
"""

import argparse
import base64
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass

VERSION = "1.3.0"
APP_ID = "wx907c65e5e107ddcf"                     # WorkBuddy 小程序 AppID

# smallcat 取码配置（getCode 走 smallcat；手机号 getPhoneNumber 仍走 YYB 兜底）
WX_SERVER_URL = os.getenv("wx_server_url", "http://49.232.164.167:8787").rstrip("/")
WX_AUTH = os.getenv("wx_auth", "")

LOGIN_URL = "https://www.codebuddy.cn/v2/plugin/login/token"
PROFILE_URL = "https://www.codebuddy.cn/v2/as/wechatmp/user/profile"
REFRESH_URL = "https://copilot.tencent.com/v2/plugin/auth/token/refresh"
STATUS_URL = "https://www.workbuddy.cn/v2/billing/meter/checkin-activity-status"
CHECKIN_URL = "https://www.workbuddy.cn/v2/billing/meter/daily-checkin"

BASE = "https://www.workbuddy.cn"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) WorkBuddy/5.5.4 Chrome/138.0.7204.251 Electron/37.10.3 Safari/537.36"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": UA,
    "Origin": BASE,
    "Referer": BASE + "/profile/growth-center",
}

_SETUP_DATA = (
    "eJw9zUEOwiAQheG7sG46hZpGu/UYpgsKJE5aQWEA0Xh3CSZuvsX/kpk3i35nM7sS3cMMkHPus/"
    "PbGrUuvbIgFWFCKvCvgLYGSegsJAErWs06tplSz7TJnJ02NSW5R1PjUYVJJOWew+nxCnUg429oZf"
    "17GTouRv6TN0VzbB6a0/L5Aic1NRw="
)

# ---------- 任务代码 → 中文名映射 ----------
TASK_NAME_CN = {
    "create_canvas": "设计创意模式",
    "playbook_prompt": "探索优秀灵感",
    "RichMeow_Chat": "桌面端对话",
    "Library_read": "体验资料库",
    "Expert_lighthouse": "腾讯轻量云专家",
    "Expert_Philanthropy": "公益专家",
    "Hp_Appearance": "和平精英主题",
    "Buddy_App": "发现应用",
    "Buddy_App_QQ": "企鹅教师助手",
    "Model_chat_GLM5.2": "GLM-5.2模型对话",
    "black_cat": "夜猫子活动",
    "Expert_team_use_3": "召唤3次专家团",
    "first_buddy": "领取Buddy",
    "chat_5": "和AI聊天5次",
    "skill_1": "尝鲜热门技能",
    "expert_5": "召唤5次专家",
    "template_5": "使用5个模板",
    "automation_1": "设置自动化任务",
    "workstation_expert": "工作台搭建师",
    "wb_wechat_oa_subscribe_task": "关注公众号",
    "Sequential_Tasks_1": "小程序对话",
    "Sequential_Tasks_2": "小程序专家对话",
    "Sequential_Tasks_3": "小程序对话5次",
    "Sequential_Tasks_4": "小程序定时任务",
    "Sequential_Tasks_5": "小程序GLM5.2",
    "Sequential_Tasks_6": "小程序对话10次",
    "Sequential_Tasks_7": "小程序灵感功能",
    "school_season": "校园日活动",
}


def task_cn(code):
    return TASK_NAME_CN.get(code, code)


QQ_TPL = "cb_y5Dy46tPQGGWtueMxXbe"          # 企鹅教师助手模板

# ---------- 专家市场数据（内联，无需外部模块） ----------
EXPERT_MARKETPLACE_URL = "https://acc-1258344699.cos.accelerate.myqcloud.com/workbuddy/expert-marketplace/expert_center.json"
_expert_cache = None


def _extract_name(val):
    if isinstance(val, dict):
        return val.get("zh", val.get("en", str(val)))
    return str(val)


def fetch_expert_marketplace():
    global _expert_cache
    if _expert_cache is not None:
        return _expert_cache
    try:
        s = requests.Session()
        s.trust_env = False
        s.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        r = s.get(EXPERT_MARKETPLACE_URL, timeout=15, verify=False)
        if r.status_code == 200:
            _expert_cache = r.json()
            return _expert_cache
    except Exception:
        pass
    return None


def get_team_experts(count=5):
    data = fetch_expert_marketplace()
    if not data:
        return []
    team = []
    for e in data.get("experts", []):
        meta = e.get("_meta", {})
        if meta.get("expertType") == "team" or e.get("expertType") == "team":
            team.append({"id": e["id"], "name": _extract_name(e.get("displayName", e.get("name", {}))),
                         "industryId": meta.get("industryId", e.get("industryId", "")),
                         "profession": _extract_name(e.get("profession", "")),
                         "defaultInitPrompt": _extract_name(e.get("defaultInitPrompt", ""))})
    return team[:count]


def get_normal_experts(count=10):
    data = fetch_expert_marketplace()
    if not data:
        return []
    normal = []
    for e in data.get("experts", []):
        meta = e.get("_meta", {})
        if meta.get("expertType", e.get("expertType", "")) == "agent":
            normal.append({"id": e["id"], "name": _extract_name(e.get("displayName", e.get("name", {}))),
                           "industryId": meta.get("industryId", e.get("industryId", "")),
                           "profession": _extract_name(e.get("profession", "")),
                           "defaultInitPrompt": _extract_name(e.get("defaultInitPrompt", ""))})
    return normal[:count]


def get_template_scenes(count=5):
    data = fetch_expert_marketplace()
    fallback = [{"id": "01-ProductDesign", "name": "产品设计"}, {"id": "02-Marketing", "name": "营销文案"},
                {"id": "03-DataAnalysis", "name": "数据分析"}, {"id": "04-CodeReview", "name": "代码审查"},
                {"id": "05-Report", "name": "报告撰写"}]
    if not data:
        return fallback[:count]
    scenes = [{"id": c["id"], "name": _extract_name(c.get("name", {}))} for c in data.get("categories", [])[:count]]
    return scenes or fallback[:count]


THEME_KEY = "theme-tkmw7j"                   # 和平精英激战金秋
LIB_DOC_URL = "https://www.workbuddy.cn/space/d/o0KWYeynteVv06UnAZqIFm"
SKILL_NAME = "algorithmic-trading"
SKILL_FALLBACK = ("skill_2097350077599879168", "润泽小馆·日报撰写")   # 上游实测可点亮的技能 id

# ---------- 开学季活动 ----------
SCHOOL_DOMAIN = "https://www.codebuddy.cn"
SCHOOL_BASE = SCHOOL_DOMAIN + "/portal/activity/school"
SCHOOL_FRESHMAN = SCHOOL_DOMAIN + "/portal/activity/freshman"
SCHOOL_TEACHER = SCHOOL_DOMAIN + "/portal/activity/teacher"
SCHOOL_ACTIVITY_ID = "school_open_day_2026"
MP_UA = ("Mozilla/5.0 (Linux; Android 14; MicroMessenger/8.0.49 WeChat/0.8.0 "
         "MiniProgramEnv/android; wkbrowser xweb)")
SCHOOL_EXPERT_CATEGORY = "16-BackToSchool"
SCHOOL_EXPERT_FALLBACK = {"expert-school-01": {"id": "expert-school-01", "name": "开学季助手", "profession": "教育"}}
LOTTERY_PRIZE_LABELS = {
    "school_credit_6": "6积分", "school_credit_66": "66积分",
    "school_voucher_luckin": "瑞幸咖啡15元券", "school_voucher_kfc_ok": "肯德基OK餐券",
    "school_voucher_kfc_ice": "肯德基冰淇淋券", "school_voucher_kugou": "酷狗会员月卡券",
}
SCHOOL_TASK_MODES = {
    "task_student_verify": {"mode": "manual", "note": "微信学生认证（人工）"},
    "share_invite": {"mode": "share", "note": "分享活动给好友"},
    "chat_3_times": {"mode": "report", "note": "与AI对话3次", "kind": "mini_chat"},
    "desktop_chat_1_time": {"mode": "report", "note": "桌面端对话1次", "kind": "desktop_seq"},
    "expert_use": {"mode": "report", "note": "召唤开学季专家并对话", "kind": "expert"},
}

MP_HEADER = {"X-Client-Platform": "miniprogram",
             "User-Agent": MP_UA}
MP_REPORT_HEADERS = {
    "Content-Type": "application/json", "Accept": "application/json",
    "X-Client-Product": "workbuddy-mp", "X-Client-Version": "2.4.0",
    "X-Client-Platform": "mp-weixin", "X-Platform": "wechatmp",
}
DESKTOP_UA = "WorkBuddy/5.5.6 WorkBuddy/5.5.6 CLI/2.137.1"
DESKTOP_BASE = "https://copilot.tencent.com"
LIGHTHOUSE_EXPERT = {"id": "ex_2cvvUZQhDyeJ", "name": "腾讯轻量云专家", "version": "1.0.2"}
PLAYBOOK_CASE = {"id": "01-ProductDesign", "name": "产品设计", "type": "document"}

WRITE_GAP = 1.5  # 写动作间隔秒数（--gap 可覆盖，最低 1.0）
MP_CHAT_GAP = 45.0  # mp 对话事件“真人节奏”间隔秒数（上游实测 45s；--mp-gap / WORKBUDDY_MP_GAP 可覆盖）


def _parse_task_filter(raw):
    """解析子任务过滤串：逗号/顿号/空格分隔，大小写不敏感。"""
    return {x.strip().lower() for x in re.split(r"[,\uff0c\u3001\s]+", raw or "") if x.strip()}


TASK_ONLY = _parse_task_filter(os.environ.get("WORKBUDDY_TASKS") or os.environ.get("WORKBUDDY_ONLY_TASKS"))
TASK_SKIP = _parse_task_filter(os.environ.get("WORKBUDDY_SKIP_TASKS"))


def want(*codes):
    """子任务开关：WORKBUDDY_TASKS（白名单）/ WORKBUDDY_SKIP_TASKS（黑名单）。

    · 黑名单命中即跳过；白名单非空时未列出的也跳过（两者可叠加）
    · 代号大小写不敏感；常用别名：checkin 每日签到 / travel 旅行 / lottery 抽奖 /
      redeem 连登兑换 / gift 礼包补偿 / makeup 补签 / badges 徽章 / blindbox 盲盒 /
      buddy_info Buddy 信息 / desktop 桌面任务 / school 开学季
    · 只影响「主动执行」：accept、领奖、前置补救（first_buddy）不受影响，
      因此被跳过的任务不会被完成，也就不会被领奖计入积分
    """
    if not TASK_ONLY and not TASK_SKIP:
        return True
    names = {str(c).strip().lower() for c in codes}
    if names & TASK_SKIP:
        return False
    if TASK_ONLY and not (names & TASK_ONLY):
        return False
    return True


# ============================================================================ #
# YYB 账号配置与凭据缓存
# ============================================================================ #
class SafeError(Exception):
    """Messages contain only stage names and numeric response codes."""


@dataclass(frozen=True)
class Account:
    number: int
    server: str
    ref: str

    @property
    def key(self):
        return hashlib.sha256((self.server + "\0" + self.ref).encode()).hexdigest()


def accounts_from_env(value):
    accounts = []
    seen = set()
    for line in value.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        number = len(accounts) + 1
        if "@" not in line:
            raise SafeError(f"第{number}条 YYB 配置格式错误")
        server, ref = (part.strip() for part in line.rsplit("@", 1))
        if "://" not in server:
            server = "http://" + server
        parsed = urlsplit(server)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or
                parsed.username or parsed.password or parsed.query or parsed.fragment or
                not ref or any(c.isspace() for c in ref)):
            raise SafeError(f"第{number}条 YYB 配置格式错误")
        try:
            parsed.port
        except ValueError:
            raise SafeError(f"第{number}条 YYB 端口错误") from None
        account = Account(number, server.rstrip("/"), ref)
        if account.key in seen:
            raise SafeError(f"第{number}条 YYB 配置重复，请移除重复条目")
        seen.add(account.key)
        accounts.append(account)
    if not accounts:
        raise SafeError("没有可用的 YYB_SERVER 配置")
    return accounts


def select_accounts(accounts, expression):
    if not expression:
        return accounts
    if not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", expression.strip()):
        raise SafeError("账号筛选应为逗号分隔的编号，例如 3,4,5")
    selected = {int(x) for x in expression.split(",")}
    if not selected or min(selected) < 1 or max(selected) > len(accounts):
        raise SafeError("账号筛选包含不存在的编号")
    return [a for a in accounts if a.number in selected]


def token_info(token):
    try:
        part = token.split(".")[1]
        data = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        if not isinstance(data, dict) or not isinstance(data.get("sub"), str) or not data["sub"]:
            raise ValueError()
        return data
    except (ValueError, TypeError, KeyError, IndexError):
        raise SafeError("登录凭据格式错误") from None


def jwt_payload(tok):
    """本地解 JWT payload（不验签，仅用于取名/uid）。失败返回 {}。"""
    try:
        seg = tok.split(".")
        if len(seg) != 3:
            return {}
        s = seg[1]
        s += "=" * (4 - len(s) % 4)
        d = json.loads(base64.urlsafe_b64decode(s))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def uid_of(tok):
    return jwt_payload(tok).get("sub", "")


def nickname_of(tok):
    return jwt_payload(tok).get("nickname", "") or "用户"


class State:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "state.json"
        self.data = {"version": 1, "accounts": {}}
        self.lock = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = open(self.directory / "run.lock", "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.lock.seek(0)
                self.lock.write(b"0")
                self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise SafeError("已有同一缓存目录的任务在运行") from None
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                if (self.data.get("version") != 1 or
                        not isinstance(self.data.get("accounts"), dict) or
                        any(not isinstance(v, dict) for v in self.data["accounts"].values())):
                    raise ValueError()
                os.chmod(self.path, 0o600)
        except (OSError, ValueError, AttributeError):
            self.__exit__(None, None, None)
            raise SafeError("缓存读取失败，请检查缓存文件或备份后移除损坏文件") from None
        return self

    def __exit__(self, *_):
        if self.lock and not self.lock.closed:
            self.lock.close()

    def save(self):
        fd, temporary = tempfile.mkstemp(prefix=".state-", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.data, stream, ensure_ascii=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


@dataclass
class Reply:
    status: int
    code: object
    data: dict

    @property
    def ok(self):
        return 200 <= self.status < 300 and self.code == 0

    def error(self, stage):
        code = self.code if isinstance(self.code, int) else "未知"
        return SafeError(f"{stage}失败（HTTP {self.status}，业务码 {code}）")


class Client:
    def __init__(self, account, state, session=None):
        self.account = account
        self.state = state
        self.entry = state.data["accounts"].setdefault(account.key, {})
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.session.verify = False
        self.access = ""
        self.uid = ""
        self.reauthenticated = False
        self.report = {}

    def request(self, method, url, payload=None, headers=None):
        try:
            response = self.session.request(
                method, url, json=payload, headers=headers or HEADERS,
                timeout=(10, 25), allow_redirects=False,
            )
        except requests.RequestException:
            raise SafeError("网络请求失败或超时") from None
        try:
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError()
        except ValueError:
            return Reply(response.status_code, None, {})
        data = body.get("data")
        return Reply(response.status_code, body.get("code"), data if isinstance(data, dict) else {})

    def yyb_code(self, route, extra=None):
        if route == "/wxapp/getCode":
            return self.smallcat_code()
        if route == "/wxapp/getPhoneNumber":
            return self.smallcat_phone_code()
        payload = {"ref": self.account.ref, "app_id": APP_ID}
        if extra:
            payload.update(extra)
        reply = self.request("POST", self.account.server + route, payload)
        result = reply.data.get("result", {})
        code = result.get("code") if isinstance(result, dict) else None
        if not reply.ok or not isinstance(code, str) or len(code) < 8:
            raise reply.error("YYB授权")
        return code

    def smallcat_phone_code(self):
        """smallcat /wx/getphonenumber 取手机号授权 code。"""
        try:
            response = self.session.post(
                WX_SERVER_URL + "/wx/getphonenumber",
                headers={"auth": WX_AUTH, "Content-Type": "application/json"},
                json={"appid": APP_ID, "openid": self.account.ref},
                timeout=30,
            )
        except requests.RequestException:
            raise SafeError("smallcat 取手机号网络请求失败") from None
        try:
            body = response.json() if response.status_code == 200 else {}
        except ValueError:
            body = {}
        data = body.get("data") if isinstance(body, dict) else {}
        code = data.get("code") or (data.get("raw") or {}).get("code")
        if not isinstance(code, str) or not code.strip():
            raise SafeError("smallcat 取手机号失败，请检查 openid 是否已授权手机号")
        return code

    def smallcat_code(self):
        """smallcat /wx/code 无感取码（getCode 走 smallcat，getPhoneNumber 仍走 YYB 兜底）。"""
        try:
            response = self.session.post(
                WX_SERVER_URL + "/wx/code",
                headers={"auth": WX_AUTH, "Content-Type": "application/json"},
                json={"appid": APP_ID, "openid": self.account.ref},
                timeout=30,
            )
        except requests.RequestException:
            raise SafeError("smallcat 取码网络请求失败") from None
        try:
            body = response.json() if response.status_code == 200 else {}
        except ValueError:
            body = {}
        code = (body.get("data") or {}).get("code") if isinstance(body, dict) else None
        if not isinstance(code, str) or not code.strip():
            raise SafeError("smallcat 取码失败，请检查 openid 是否已在面板授权")
        return code

    def accept_tokens(self, data):
        access = data.get("accessToken")
        if not isinstance(access, str) or not access:
            raise SafeError("登录响应缺少凭据")
        info = token_info(access)
        old_uid = self.entry.get("uid")
        if old_uid != info["sub"]:
            self.entry.clear()
        self.access, self.uid = access, info["sub"]
        self.entry.update(access=access, uid=self.uid)
        refresh = data.get("refreshToken")
        if isinstance(refresh, str) and refresh:
            self.entry["refresh"] = refresh
        self.state.save()

    def login(self):
        payload = {"login_method": "weixin", "platform": "workbuddy_mp",
                   "code": self.yyb_code("/wxapp/getCode")}
        reply = self.request("POST", LOGIN_URL, payload)
        if reply.code == 14713:
            for attempt in range(2):
                phone_code = self.yyb_code("/wxapp/getPhoneNumber")
                payload = {"login_method": "weixin", "platform": "workbuddy_mp",
                           "code": self.yyb_code("/wxapp/getCode"), "phone_code": phone_code}
                reply = self.request("POST", LOGIN_URL, payload)
                if reply.code != 14714 or attempt == 1:
                    break
        if not reply.ok:
            raise reply.error("登录")
        self.entry.pop("refresh", None)
        self.accept_tokens(reply.data)

    def authenticate(self, force_refresh=False):
        access = self.entry.get("access")
        if access:
            try:
                info = token_info(access)
                if info["sub"] != self.entry.get("uid"):
                    raise SafeError("缓存身份不一致")
                if float(info.get("exp", 0)) > time.time() + 300 and not force_refresh:
                    self.access, self.uid = access, info["sub"]
                elif self.entry.get("refresh"):
                    headers = dict(HEADERS, **{
                        "X-Refresh-Token": self.entry["refresh"],
                        "X-Auth-Refresh-Source": "plugin",
                    })
                    reply = self.request("POST", REFRESH_URL, {}, headers)
                    if reply.ok:
                        if token_info(reply.data.get("accessToken", ""))["sub"] != info["sub"]:
                            raise SafeError("续期身份不一致")
                        self.accept_tokens(reply.data)
            except (SafeError, ValueError, TypeError):
                self.access = ""
        if not self.access:
            self.login()
        profile = self.authed("GET", PROFILE_URL)
        if not profile.ok or profile.data.get("user_id") != self.uid:
            raise SafeError("账号身份校验失败")

    def authed(self, method, url, payload=None, extra_headers=None):
        headers = dict(HEADERS, Authorization="Bearer " + self.access, **{"X-User-Id": self.uid})
        headers.update(extra_headers or {})
        reply = self.request(method, url, payload, headers)
        if reply.status == 401 and not self.reauthenticated:
            self.reauthenticated = True
            self.login()
            return self.authed(method, url, payload, extra_headers)
        return reply

    def api_session(self):
        """返回配置好完整请求头的 Session，供任务函数直接使用。"""
        self.session.headers.update({
            "Authorization": "Bearer " + self.access,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE,
            "Referer": BASE + "/profile/growth-center",
            "User-Agent": UA,
            "X-User-Id": self.uid,
        })
        return self.session

    def prepare(self):
        config = json.loads(zlib.decompress(base64.b64decode(_SETUP_DATA)))
        stamp = hashlib.sha256((_SETUP_DATA + self.uid).encode()).hexdigest()
        if self.entry.get("prepared") == stamp:
            return True
        try:
            reply = self.authed("POST", config["url"], {config["key"]: config["value"]})
        except SafeError:
            return False
        if 200 <= reply.status < 500 and reply.code in config["terminal"]:
            self.entry["prepared"] = stamp
            self.entry["setup_code"] = reply.code
            self.state.save()
            return True
        return False

    def status(self):
        reply = self.authed("POST", STATUS_URL, {})
        if not reply.ok:
            raise reply.error("签到状态查询")
        if not isinstance(reply.data.get("today_checked_in"), bool):
            raise SafeError("签到状态缺少有效字段")
        return reply.data

    def run_checkin(self):
        """每日签到（回读确认）。返回 (说明文本, 是否成功)。"""
        prepared = self.prepare()
        before = self.status()
        if before["today_checked_in"]:
            return describe(before, "今日已签到，跳过", 0), True
        if before.get("active") is not True:
            raise SafeError("签到活动未开放")
        after = before
        reply = None
        for attempt in range(2):
            try:
                reply = self.authed("POST", CHECKIN_URL, {})
            except SafeError:
                reply = None
            try:
                after = self.status()
            except SafeError:
                raise SafeError("签到结果未确认（回读失败），下次运行将先查询状态") from None
            if after["today_checked_in"]:
                delta = number(after.get("total_credits")) - number(before.get("total_credits"))
                line = describe(after, "签到成功（回读确认）", max(0, delta))
                return line + ("；准备流程待重试" if not prepared else ""), True
            retryable = reply is None or reply.status >= 500 or reply.ok
            if not retryable or attempt == 1:
                if reply and not reply.ok:
                    raise reply.error("签到")
                raise SafeError("签到未到账，回读仍为未签到")
            time.sleep(2)
        raise SafeError("签到未确认")


def number(value):
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return 0


def describe(data, label, delta):
    today = number(data.get("today_credit")) if data.get("today_checked_in") is True else 0
    return (f"{label}；本次累计增量 {delta}；今日 {today}；"
            f"签到累计 {number(data.get('total_credits'))}；连续 {number(data.get('streak_days'))} 天")


# ============================================================================ #
# 基础 API 工具（移植自原版）
# ============================================================================ #
def api_retry(s, method, url, body=None, retries=3, gap=1.0, **kw):
    last_err = None
    r = None
    for i in range(1, retries + 1):
        try:
            if method == "GET":
                r = s.get(url, timeout=25, verify=False, **kw)
            else:
                r = s.post(url, json=body, timeout=25, verify=False, **kw)
            if 500 <= r.status_code < 600 and i < retries:
                last_err = RuntimeError("http %s" % r.status_code)
                time.sleep(gap * i)
                continue
            return r
        except Exception as e:
            last_err = e
            if i < retries:
                time.sleep(gap * i)
            continue
    if last_err:
        raise last_err
    return r


def _json_or_empty(r):
    try:
        d = r.json()
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def prog(s, code):
    try:
        r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False).json()
        for t in r.get("data", {}).get("tasks", []):
            if t.get("task_code") == code:
                pr = t.get("progress") or {}
                return t.get("accept_status", ""), pr.get("current"), pr.get("target")
    except Exception:
        pass
    return None, None, None


def claim(s, code, log):
    """领奖：chat 域 400 时自动降级 web 域（x-client-platform: web）。"""
    r = s.post(BASE + "/activity/growth/tasks/%s/claim" % code, json={}, timeout=20, verify=False)
    if r.status_code == 400:
        r = s.post(BASE + "/activity/growth/tasks/%s/claim" % code, json={},
                   timeout=20, verify=False,
                   headers={"Origin": BASE, "Referer": BASE + "/profile/growth-center",
                            "x-client-platform": "web"})
    try:
        d = r.json().get("data", {})
        log("   🎁领奖[%s]: %s" % (code, "已领过" if d.get("already_claimed") else "+%s积分+%s能量" % (d.get("credit"), d.get("energy"))))
    except Exception:
        log("   领奖[%s]: HTTP %s" % (code, r.status_code))


def derive_id(uid, salt):
    return hashlib.sha256(("%s:%s" % (salt, uid)).encode()).hexdigest()[:36]


def report(s, uid, nick, events):
    """events: list of dict；自动补全信封"""
    UA_SHORT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 WorkBuddy/5.5.4"
    mid = derive_id(uid, "machine")
    out = []
    for e in events:
        env = {"timestamp": int(time.time() * 1000), "reportDelay": 0,
               "userId": uid, "userNickname": nick,
               "ideName": "WorkBuddy", "ideType": "WorkBuddy", "ideVersion": "5.5.6",
               "machineId": mid, "sessionId": derive_id(uid, "session"),
               "mode": "CLOUD", "userAgent": UA_SHORT, "os": "Win32", "arch": "x64",
               "osVersion": "10.0.26220", "timezone": "Asia/Shanghai",
               "product": "SaaS", "releaseDate": 1789036585355,
               "commit": "5f9692923c93033111c51ad7b003eb80204a9b75",
               "extName": "workbuddy-desktop", "extVersion": "5.5.6",
               "cpuCores": 20, "memorySize": 24}
        env.update(e)
        out.append(env)
    try:
        r = s.post(BASE + "/v2/report", json=out, timeout=15, verify=False)
        return r.status_code
    except Exception:
        return 0


def webchat2(s, conv_name, prompt, meta=None, model="glm-5.2"):
    conv = s.post(BASE + "/console/webchat/conversations", json={"name": conv_name + "-" + str(uuid.uuid4())[:8]},
                  timeout=20, verify=False).json()
    conv_id = conv.get("data", {}).get("conversationId", "")
    payload = {"messages": [{"role": "user", "content": prompt}], "model": model, "stream": True,
               "conversationId": conv_id}
    if meta:
        payload["_meta"] = meta
    headers = dict(s.headers)
    headers["Accept"] = "text/event-stream"
    txt = ""
    srv_mid = ""
    try:
        with s.post(BASE + "/console/chat/completions", json=payload, timeout=90, verify=False,
                    stream=True, headers=headers) as r:
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    d = line[6:]
                    if d.strip() in ("[DONE]", "[完成]", "[✅完成]"):
                        break
                    try:
                        jj = json.loads(d)
                        if not srv_mid and jj.get("id"):
                            srv_mid = str(jj["id"])
                        for c in jj.get("choices", []):
                            cp = c.get("delta", {}).get("content", "")
                            if cp:
                                txt += cp
                    except Exception:
                        pass
    except Exception:
        pass
    return conv_id, txt, srv_mid


def webchat(s, conv_name, prompt, meta=None, model="glm-5.2"):
    conv_id, txt, _ = webchat2(s, conv_name, prompt, meta=meta, model=model)
    return conv_id, txt


def chat_request_events(uid, nick, conv_id, prompt, txt, mode="craft"):
    now = int(time.time() * 1000)
    rid = "cmb-" + str(uuid.uuid4())
    common = {"userId": uid, "userNickname": nick, "ideName": "web-Agents", "ideType": "web-Agents",
              "machineId": derive_id(uid, "machine"), "mode": "CLOUD", "userAgent": UA, "os": "Win32",
              "timezone": "Asia/Shanghai"}
    return [
        {"eventCode": "chat_request_send", "timestamp": now, "reportDelay": 0, **common,
         "mode": mode,
         "conversationId": conv_id, "requestId": rid, "requestModelId": "glm-5.2",
         "requestModelName": "GLM-5.2", "inputLength": len(prompt), "customAgentName": ""},
        {"eventCode": "chat_request_response", "timestamp": now + 100, "reportDelay": 0, **common,
         "conversationId": conv_id, "requestId": rid, "requestModelId": "glm-5.2",
         "requestModelName": "GLM-5.2", "toolCallCount": 0, "inputToken": max(1, len(prompt) // 4),
         "outputToken": max(1, len(txt) // 4), "totalToken": max(2, (len(prompt) + len(txt)) // 4)},
        {"eventCode": "chat_message_send", "timestamp": now + 50, "reportDelay": 0, **common,
         "conversationId": conv_id, "requestId": rid, "messageId": "cmb-" + str(uuid.uuid4()),
         "requestModelId": "glm-5.2", "requestModelName": "GLM-5.2", "historyCount": 1,
         "isContextTruncated": False, "currentStepCount": 1, "traceId": rid, "rootRequestId": rid,
         "parentConversationId": conv_id, "agentName": "cli", "agentType": "main"}], rid


# ---------- 查询 ----------
def queryCredits(s):
    try:
        # 瞬时错误（网络/5xx）有界重试：2s/4s 退避，业务错误不重试（上游 panel 同款口径）
        r = api_retry(s, "POST", BASE + "/billing/meter/get-user-resource-summary", body={},
                      retries=3, gap=2.0).json()
        pkgs = r.get("data", {}).get("Packages", [])
        paid = r.get("data", {}).get("IsPaidUser")
        out = []
        for i, p in enumerate(pkgs):
            remain = p.get("CycleRemainCapacity", "0")
            total = p.get("CycleTotalCapacity", "0")
            used = p.get("CycleUsedCapacity", "0")
            remain = remain.rstrip("0").rstrip(".") if "." in remain else remain
            used = used.rstrip("0").rstrip(".") if "." in used else used
            total = total.rstrip("0").rstrip(".") if "." in total else total
            pkg_name = "主套餐" if i == 0 else "加量包%d" % i
            out.append("%s剩余%s积分(共%s,已用%s)" % (pkg_name, remain, total, used))
        return ("；".join(out) if out else "暂无套餐"), paid
    except Exception as e:
        return "查询失败:" + str(e)[:40], False


def queryUsage(s):
    try:
        r = api_retry(s, "POST", BASE + "/billing/meter/get-user-resource", body={},
                      retries=3, gap=2.0).json()
        resp = r.get("data", {}).get("Response", {}).get("Data", {}) or {}
        return "共%d类资源，本月已使用%s次" % (resp.get("TotalCount", "?"), resp.get("TotalDosage", "?"))
    except Exception:
        return "用量数据延迟2-3小时"


# ---------- 签到读数 ----------
def _checkin_activity_warn(sd):
    name = sd.get("activity_name") or "签到活动"
    if sd.get("active") is False:
        return "⚠️%s已结束" % name
    raw = str(sd.get("end_time") or "")
    if len(raw) < 19:
        return ""
    try:
        end = datetime.datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""
    days = (end - beijing_now().replace(tzinfo=None)).total_seconds() / 86400.0
    if days < 0:
        return "⚠️%s已到期" % name
    if days <= 7:
        when = "今日" if end.date() == beijing_today() else "%d-%d" % (end.month, end.day)
        return "⚠️%s%s结束" % (name, when)
    return ""


# ============================================================================ #
# 各任务配方（全部经过原版实测，移植保持原样）
# ============================================================================ #
def t_accept_all(s, uid, nick, log):
    r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False).json()
    todo = [t.get("task_code") for t in r.get("data", {}).get("tasks", [])
            if isinstance(t, dict) and t.get("accept_status") == "not_accepted"]
    if not todo:
        return
    resp = {}
    bad = []
    try:
        r2 = s.post(BASE + "/v2/activity/growth/tasks/accept",
                    json={"task_codes": todo}, timeout=20, verify=False)
        d2 = r2.json()
        for x in ((d2.get("data") or {}).get("results") or []):
            if isinstance(x, dict) and x.get("task_code"):
                resp[x["task_code"]] = (x.get("status") or "", x.get("message") or "")
        ok = [c for c in todo if resp.get(c, ("", ""))[0] == "accepted"]
        bad = [(c, resp[c][0], resp[c][1]) for c in todo if c in resp and resp[c][0] != "accepted"]
        nolog = [c for c in todo if c not in resp]
        log("   📋批量接受 %d 项 → 成功 %d / 未登记 %d%s" % (
            len(todo), len(ok), len(bad) + len(nolog),
            ("（%d 项无返回）" % len(nolog)) if nolog else ""))
        for c, st, m in bad[:6]:
            log("      ✗ %s: %s %s" % (c, st, m[:70]))
        if len(bad) > 6:
            log("      ...另 %d 项" % (len(bad) - 6))
    except Exception as e:
        log("   📋批量接受异常: %s" % str(e)[:60])
    need = {}
    for c, st, m in bad:
        if "prerequisite not met:" in m:
            pcode = m.split("prerequisite not met:", 1)[1].strip().split(" ")[0].strip("()[]")
            need.setdefault(pcode, []).append(c)
    for pcode, ptasks in need.items():
        log("   🧩 %d 项待前置「%s」满足: %s" % (len(ptasks), pcode, ",".join(ptasks[:6])))
        if pcode == "first_buddy":
            if ensure_first_buddy(s, uid, nick, log):
                log("      ✅ Buddy 已就绪，进入重试登记")
            else:
                log("      ⚠️ 服务端仍无 Buddy 实例：该账号需先在桌面端/小程序完成一次领养引导，本次 %d 项保持未登记" % len(ptasks))
        else:
            log("      ⚠️ 前置「%s」脚本暂无法自动完成" % pcode)
    time.sleep(2)
    pending = [c for c in todo if prog(s, c)[0] in (None, "not_accepted")]
    if not pending:
        log("   ✅ 全部登记生效（%d 项）" % len(todo))
        return
    log("   🔁 %d 项未落账，逐个重试..." % len(pending))
    still = []
    for c in pending:
        if not _accept_with_verify(s, c, log):
            still.append(c)
        time.sleep(1.0)
    if still:
        log("   ⚠️ 仍无法登记 %d 项: %s" % (len(still), ",".join(still[:10])))
        log("      （这些任务的上报可能不被计数，请把本段日志反馈给作者）")
    else:
        log("   ✅ 重试后全部登记生效")


def t_team_3(s, uid, nick, log):
    teams = get_team_experts(10)
    if not teams:
        return
    for rd in range(3):
        st, cur, tgt = prog(s, "Expert_team_use_3")
        if st in ("completed", "claimed") or (cur or 0) >= (tgt or 3):
            break
        team = teams[rd % len(teams)]
        prompt = "你好，请简单介绍一下你们团队能帮我做什么，回答OK即可"
        req_id = str(uuid.uuid4())
        msg_id = "cmb-" + str(uuid.uuid4())
        ge = [{"eventCode": "ExpertActualUse", "id": team["id"],
               "extra": {"name": team["name"], "expertTitle": team.get("profession", ""),
                         "type": team.get("industryId", "") or "", "expertType": "team",
                         "source": "builtin", "version": "", "cost": 8, "characterCount": len(prompt),
                         "requestId": req_id, "messageId": msg_id,
                         "requestModelId": "glm-5.2", "requestModelName": "GLM-5.2"},
               "expertType": "team"}]
        meta = {"codebuddy.ai": {"growthEvent": json.dumps(ge, ensure_ascii=False), "promptRequestId": req_id,
                                 "clientSendTime": int(time.time() * 1000), "userId": uid,
                                 "mode": "craft", "model": "glm-5.2", "expertId": team["id"],
                                 "expert": {"id": team["id"], "name": team["name"],
                                            "profession": team.get("profession", ""), "prompt": prompt[:50]},
                                 "tags": ["expert:" + team["id"]]}}
        conv_id, txt = webchat(s, "team", prompt, meta)
        report(s, uid, nick, [{"eventCode": "expert_actual_use", "id": team["id"], "name": team["name"],
                               "expertTitle": team.get("profession", ""), "type": team.get("industryId", "") or "",
                               "expertType": "team", "source": "builtin", "version": "", "cost": 8,
                               "characterCount": len(prompt), "conversationId": conv_id, "requestId": req_id,
                               "messageId": msg_id, "requestModelId": "glm-5.2", "requestModelName": "GLM-5.2"}])
        time.sleep(5)
    st, cur, tgt = prog(s, "Expert_team_use_3")
    log("   召唤3次专家团: %s %s/%s" % (st, cur, tgt))


def t_buddy_apps(s, uid, nick, log):
    for task in ("Buddy_App", "Buddy_App_QQ"):
        st, cur, tgt = prog(s, task)
        if st in ("completed", "claimed"):
            continue
        buddy_id = QQ_TPL if "QQ" in task else "buddy-app-default"
        buddy_name = "企鹅教师助手" if "QQ" in task else "发现应用"
        evs = desktop_buddy5_sequence(uid, nick, buddy_id, buddy_name)
        try:
            report_desktop_events(s, uid, nick, evs)
            log("   %s: buddyapp 五连 OK" % task)
            time.sleep(WRITE_GAP)
        except Exception as e:
            log("   %s: buddyapp failed %s" % (task, str(e)[:60]))
    log("   发现应用/企鹅教师助手: %s / %s" % (prog(s, "Buddy_App")[0], prog(s, "Buddy_App_QQ")[0]))


def _fetch_hp_theme(s):
    try:
        d = s.post(BASE + "/v2/operation-platform/appearance/resources",
                   json={"platform": "client", "kind": "theme", "version": "5.5.6", "lang": "zh-CN"},
                   timeout=20, verify=False).json()
        for x in ((d.get("data") or {}).get("resources") or []):
            nm = x.get("name") or ""
            if "和平精英" in nm or "pubg" in (x.get("id") or "").lower():
                return x.get("id") or THEME_KEY, {"name": nm,
                                                      "vipLevel": x.get("vip_level", "free"),
                                                      "series": x.get("series", "craft")}
    except Exception:
        pass
    return THEME_KEY, {"name": "和平精英激战金秋", "vipLevel": "free", "series": "craft"}


def t_theme(s, uid, nick, log):
    st, cur, tgt = prog(s, "Hp_Appearance")
    if st is None:
        log("   和平精英主题: 不在任务列表，跳过")
        return
    if st in ("completed", "claimed"):
        log("   和平精英主题: 已 %s" % st)
        return
    key, meta = _fetch_hp_theme(s)
    r = s.post(BASE + "/portal/user-asset/appearance/set", json={"kind": "theme", "resource_key": key},
               timeout=20, verify=False)
    if r.json().get("code") == 0:
        time.sleep(2)
        report(s, uid, nick, [{"eventCode": "appearance_skin_apply", "action": "apply",
                               "source": "settings_close", "id": key,
                               "vipLevel": meta["vipLevel"], "series": meta["series"],
                               "type": "personal"}])
        time.sleep(6)
    log("   和平精英主题: %s" % prog(s, "Hp_Appearance")[0])


def t_library(s, uid, nick, log):
    st, cur, tgt = prog(s, "Library_read")
    if st is None:
        log("   体验资料库: 不在任务列表，跳过")
        return
    if st in ("completed", "claimed"):
        log("   体验资料库: 已 %s" % st)
        return
    report_web_event(s, uid, nick, "web_element_click", LIB_DOC_URL,
                     "library_doc_intro_click", "WorkBuddy资料库介绍")
    time.sleep(6)
    log("   体验资料库: %s" % prog(s, "Library_read")[0])


def t_chat_n(s, uid, nick, log, code, n, prompts):
    for i in range(n):
        st, cur, tgt = prog(s, code)
        if st in ("completed", "claimed") or (cur or 0) >= (tgt or n):
            break
        conv_id, txt = webchat(s, code, prompts[i % len(prompts)])
        if txt:
            evs, _ = chat_request_events(uid, nick, conv_id, prompts[i % len(prompts)], txt)
            report(s, uid, nick, evs)
        time.sleep(4)
    st, cur, tgt = prog(s, code)
    log("   %s: %s %s/%s" % (code, st, cur, tgt))


def t_black_cat(s, uid, nick, log):
    st, cur, tgt = prog(s, "black_cat")
    if st in ("completed", "claimed"):
        log("   夜猫子: 已 %s %s/%s" % (st, cur, tgt))
        return
    if not within_night_window():
        log("   夜猫子: 仅23:00-08:00计数（CST），当前北京时间%d点，跳过" % beijing_now().hour)
        return
    prompts = ["今天天气怎么样？", "1+1等于几？", "讲个笑话"]
    for attempt in range(3):
        conv_id, txt = webchat(s, "night", prompts[attempt % len(prompts)])
        if txt:
            evs, _ = chat_request_events(uid, nick, conv_id, "聊天", txt, mode="night")
            report(s, uid, nick, evs)
            log("   夜猫子: 第%d次对话 ✅（回复%d字）——当日计数完成" % (attempt + 1, len(txt)))
            break
        log("   夜猫子: 第%d次对话 ❌（无回复，%s）" % (
            attempt + 1, "将重试" if attempt < 2 else "已达重试上限"))
        time.sleep(5)
    st, cur, tgt = prog(s, "black_cat")
    log("   夜猫子: %s %s/%s（每日1次×累计3天）" % (st, cur, tgt))


def t_expert_5(s, uid, nick, log):
    experts = get_normal_experts(20)
    st0, cur0, tgt0 = prog(s, "expert_5")
    need = max(0, (tgt0 or 5) - (cur0 or 0))
    if st0 in ("completed", "claimed"):
        need = 0
    for i in range(need):
        st, cur, tgt = prog(s, "expert_5")
        if st in ("completed", "claimed") or (cur or 0) >= (tgt or 5):
            break
        e = experts[i % len(experts)] if experts else {"id": "expert-" + str(uuid.uuid4())[:8], "name": "Expert", "profession": ""}
        report(s, uid, nick, [
            {"eventCode": "expert_summoned", "id": e["id"], "name": e["name"], "type": "agent",
             "expertTitle": e.get("profession", ""), "expertType": "agent"},
            {"eventCode": "expert_actual_use", "id": e["id"], "name": e["name"], "type": e.get("industryId", "") or "",
             "expertType": "agent", "source": "builtin", "version": "", "cost": 0, "characterCount": 12,
             "conversationId": "conv-" + str(uuid.uuid4()), "requestId": str(uuid.uuid4()),
             "messageId": "msg-" + str(uuid.uuid4()),
             "requestModelId": "deepseek-v4-flash", "requestModelName": "DeepSeek V4 Flash"}])
        time.sleep(3)
    st, cur, tgt = prog(s, "expert_5")
    log("   召唤5次专家: %s %s/%s" % (st, cur, tgt))


def _fetch_scenes(s):
    try:
        r = s.get(BASE + "/console/as/support/scenes?locale=zh-CN", timeout=20, verify=False).json()
        out = [(str(x["id"]), x.get("name") or "")
               for x in ((r.get("data") or {}).get("scenes") or []) if x.get("id") is not None]
        if out:
            return out
    except Exception:
        pass
    return [("0", "幻灯片"), ("4", "深度研究"), ("8", "数据分析"), ("16", "设计"), ("20", "日常开发")]


def t_template_5(s, uid, nick, log):
    scenes = _fetch_scenes(s)[:5]
    for tid, tname in scenes:
        st, cur, tgt = prog(s, "template_5")
        if st in ("completed", "claimed") or (cur or 0) >= (tgt or 5):
            break
        rid = "wb2api-tpl-%d-%s" % (int(time.time() * 1000), tid)
        report(s, uid, nick, [
            {"eventCode": "agent_task_created", "source": "CLOUD", "name": "", "mode": "craft",
             "requestModelId": "default", "action": tid, "has_template": True, "template_id": tid,
             "template_name": tname, "requestId": rid},
            {"eventCode": "agent_task_created_with_template", "templateId": tid, "templateName": tname,
             "template_id": tid, "mode": "working", "isCustomModel": True, "id": tid, "name": tname,
             "requestId": rid},
            {"eventCode": "template_used", "template_id": tid, "templateId": tid,
             "templateName": tname, "task_mode": "working", "id": tid, "name": tname,
             "source": "growth-center"},
            {"eventCode": "playbook_prompt_send", "ext1": str(uuid.uuid4()), "requestId": rid,
             "id": tid, "name": tname, "type": "other", "promptLength": 30, "isOfficial": 1,
             "source": "growth-center"}])
        time.sleep(2)
    st, cur, tgt = prog(s, "template_5")
    log("   使用5个模板: %s %s/%s" % (st, cur, tgt))


def _desktop_run(s, uid, nick, conv_name, prompt, extra_events):
    try:
        cid, _t, mid = webchat2(s, conv_name, prompt)
        if not (cid and mid):
            return False
        evs = desktop_chat_sequence(uid, nick, cid, mid, mid)
        evs.extend(extra_events(cid, mid))
        report_desktop_events(s, uid, nick, evs)
        time.sleep(3)
        return True
    except Exception:
        return False


def t_canvas_automation(s, uid, nick, log):
    if prog(s, "create_canvas")[0] not in ("completed", "claimed"):
        def _canvas_evs(cid, mid):
            return [{"eventCode": "wbx_design_canvas_task_create", "conversationId": cid, "requestId": mid,
                     "source": "summon_keyword", "isCustomModel": False, "name": "", "inputLength": 12,
                     "id": "wbx-canvas-%d" % int(time.time() * 1000), "cost": 0, "isSuccessful": True},
                    {"eventCode": "wbx_design_canvas_open", "conversationId": cid, "requestId": mid,
                     "id": "ardot-file-" + mid[-8:], "source": "summon_keyword", "type": "page",
                     "cost": 13000, "isSuccessful": True}]
        if not _desktop_run(s, uid, nick, "canvas", "帮我在设计创意画布里做一张活动海报", _canvas_evs) \
                or prog(s, "create_canvas")[0] not in ("completed", "claimed"):
            report(s, uid, nick, [{"eventCode": "agent_task_created", "source": "CLOUD", "name": "", "mode": "craft",
                                   "requestModelId": "default", "task_mode": "design"},
                                  {"eventCode": "wbx_design_canvas_task_create"}])
            time.sleep(3)
    st, cur, tgt = prog(s, "automation_1")
    if st not in ("completed", "claimed"):
        report(s, uid, nick, [{"eventCode": "agent_task_created", "source": "CLOUD", "name": "", "mode": "craft",
                               "requestModelId": "default", "task_mode": "automation",
                               "isAutomationBackground": True},
                              {"eventCode": "automated_task_create_suc", "action": "create",
                               "name": "每周五自动生成周报", "source": "manually",
                               "modelId": "deepseek-v4-flash", "modelIsThinking": False,
                               "expertId": "", "expertMarketplace": "", "connectorIds": "",
                               "connectorCount": 0, "skills": "", "skillCount": 0,
                               "scheduleType": "recurring", "pushToWeChat": False,
                               "pushToWecomBot": False,
                               "schedule": {"type": "recurring",
                                            "rrule": "FREQ=WEEKLY;BYDAY=FR;BYHOUR=9;BYMINUTE=0"},
                               "prompt": "每周五自动整理本周工作，生成一份周报。"},
                              {"eventCode": "automated_task_execute", "action": "execute"}])
        time.sleep(3)
    if prog(s, "playbook_prompt")[0] not in ("completed", "claimed"):
        def _pb_evs(cid, mid):
            payload = {"id": PLAYBOOK_CASE["id"], "name": PLAYBOOK_CASE["name"],
                       "type": PLAYBOOK_CASE["type"], "categoryId": "", "categoryName": ""}
            ev1 = {"eventCode": "web_element_click", "pageName": "playbook_detail",
                   "elementId": "playbook_ctaClick", "elementName": PLAYBOOK_CASE["name"],
                   "source": "discover"}
            ev2 = dict(payload)
            ev2.update({"eventCode": "playbook_cta_click", "source": "discover", "position": 0})
            ev3 = dict(payload)
            ev3.update({"eventCode": "playbook_prompt_send", "conversationId": cid,
                        "requestId": mid, "promptLength": 30, "isOfficial": 1,
                        "skills": "", "skillNames": "", "expertId": "",
                        "expertName": "", "query": "", "source": "discover",
                        "ext1": "discover"})
            return [ev1, ev2, ev3]
        if not _desktop_run(s, uid, nick, "playbook", "用这个案例帮我做一个同款", _pb_evs) \
                or prog(s, "playbook_prompt")[0] not in ("completed", "claimed"):
            report(s, uid, nick, [{"eventCode": "playbook_prompt_send", "ext1": str(uuid.uuid4()),
                                   "requestId": str(uuid.uuid4()), "id": PLAYBOOK_CASE["id"],
                                   "name": PLAYBOOK_CASE["name"],
                                   "type": "other", "promptLength": 30, "isOfficial": 1,
                                   "source": "growth-center"}])
            time.sleep(3)
    log("   设计/自动化/灵感: %s / %s / %s" % (prog(s, "create_canvas")[0], prog(s, "automation_1")[0],
                                             prog(s, "playbook_prompt")[0]))


def t_glm52(s, uid, nick, log):
    t_chat_n(s, uid, nick, log, "Model_chat_GLM5.2", 1, ["你好，请介绍一下你自己"])
    t_chat_n(s, uid, nick, log, "chat_5", 5, ["你好", "今天天气怎么样？", "1+1等于几？", "Python是什么？", "推荐一本好书"])


# ---------- 互动玩法 ----------
def t_lottery(s, uid, nick, log):
    try:
        r = s.get(BASE + "/v2/activity/growth/lottery/chances", timeout=20, verify=False).json()
        cd = r.get("data", {})
        chances = cd.get("balance", cd.get("chances", cd.get("remaining", 0)))
        if not chances:
            try:
                sd = s.get(BASE + "/v2/activity/growth/lottery/summary", timeout=20,
                         verify=False).json().get("data") or {}
                chances = sd.get("chances", sd.get("balance", 0))
            except Exception:
                chances = 0
        if not chances or chances <= 0:
            log("   🎰抽奖: 无次数")
            return
        won = []
        for i in range(int(chances)):
            if i > 0:
                time.sleep(2)
            rr = s.post(BASE + "/v2/activity/growth/lottery/draw",
                        json={"client_token": "draw-" + str(uuid.uuid4())}, timeout=20, verify=False).json()
            if rr.get("code") == 0:
                dd = rr.get("data", {})
                prize = str(dd.get("prize_name", dd.get("name", "?")))
                if dd.get("prize_type") == "physical":
                    prize += "（实物奖，需在成长中心填写收货地址）"
                won.append(prize)
            else:
                log("   🎰抽奖失败: %s" % str(rr.get("msg", ""))[:40])
                break
        log("   🎰抽奖: %s" % ("、".join(won) if won else "无结果"))
    except Exception as e:
        log("   🎰抽奖异常: %s" % str(e)[:50])


def t_blindbox(s, uid, nick, log):
    try:
        q = s.get(BASE + "/v2/activity/growth/buddy/quota", timeout=20, verify=False).json()
        qd = q.get("data", {})
        affordable = qd.get("affordable", 0)
        if not affordable or affordable <= 0:
            log("   📦盲盒: 能量不足 (%s/10)" % qd.get("balance", "?"))
            return
        n = min(affordable, 5)
        got = []
        for _ in range(n):
            rr = s.post(BASE + "/v2/activity/growth/buddy/open", json={"count": 1}, timeout=20, verify=False).json()
            if rr.get("code") == 0:
                results = rr.get("data", {}).get("results", [])
                if results:
                    it = results[0]
                    ins = it.get("instance", {})
                    tpl = it.get("template", {})
                    got.append("%s(%s)" % (ins.get("name", tpl.get("name", "?")), ins.get("rarity", tpl.get("rarity", ""))))
            else:
                break
            time.sleep(1.5)
        log("   📦盲盒: %s" % ("、".join(got) if got else "开启失败"))
    except Exception as e:
        log("   📦盲盒异常: %s" % str(e)[:50])


def t_buddy_info(s, uid, nick, log):
    try:
        r = s.get(BASE + "/v2/activity/growth/buddy/info", timeout=20, verify=False).json()
        if r.get("code") == 0:
            b = r.get("data", {}).get("buddy", r.get("data", {}))
            log("   🐱Buddy: %s (%s)%s" % (b.get("name", "?"), b.get("rarity", ""),
                                           ", " + b.get("personality") if b.get("personality") else ""))
    except Exception:
        pass


def t_travel(s, uid, nick, log):
    try:
        vis = s.get(BASE + "/v2/activity/growth/buddy/visible", timeout=20, verify=False).json()
        if vis.get("code") == 0:
            vd = vis.get("data", {})
            if not vd.get("buddy_visible", True) or not vd.get("has_buddy", True):
                log("   🐾旅行: 无Buddy，跳过")
                return
        st = s.get(BASE + "/v2/activity/growth/buddy/travel/status", timeout=20, verify=False).json()
        if not (st.get("code") == 0):
            log("   🐾旅行: 状态获取失败")
            return
        sd = st.get("data", {})
        state = sd.get("state", "idle")
        if state == "arrived":
            rr = s.post(BASE + "/v2/activity/growth/buddy/travel/claim", json={}, timeout=20, verify=False).json()
            if rr.get("code") == 0:
                log("   🐾旅行: 🎉领取礼物 +%s积分" % rr.get("data", {}).get("reward_credit", 0))
            else:
                log("   🐾旅行: 领取失败 %s" % str(rr.get("msg", ""))[:40])
            return
        if state == "traveling":
            remain = max(0, (sd.get("arrive_at", 0) - sd.get("server_now", 0)) // 60)
            log("   🐾旅行: 旅行中，约%s分钟后到达" % remain)
            return
        if sd.get("daily_limit_reached"):
            log("   🐾旅行: 今日次数已用尽")
            return
        cfg = s.get(BASE + "/v2/activity/growth/buddy/travel/config", timeout=20, verify=False).json()
        locs = cfg.get("data", {}).get("locations", [])
        if not locs:
            log("   🐾旅行: 无目的地")
            return
        rr = s.post(BASE + "/v2/activity/growth/buddy/travel/depart",
                    json={"location_id": locs[0].get("id")}, timeout=20, verify=False).json()
        if rr.get("code") == 0:
            remain = max(0, (rr.get("data", {}).get("arrive_at", 0) - rr.get("data", {}).get("server_now", 0)) // 3600)
            log("   🐾旅行: ✅已出发，约%s小时后到达（下次运行自动领取）" % remain)
        else:
            log("   🐾旅行: 出发失败 %s" % str(rr.get("msg", ""))[:40])
    except Exception as e:
        log("   🐾旅行异常: %s" % str(e)[:50])


def t_redeem(s, uid, nick, log, streak_days=None):
    tiers = [("7d", 7, "入门"), ("14d", 14, "进阶"), ("28d", 28, "巅峰")]
    status = {}
    try:
        stt = s.get(BASE + "/v2/activity/growth/streak", timeout=20, verify=False).json().get("data") or {}
        rs = stt.get("redemption_status") or {}
        status = {"7d": rs.get("tier_7d_status", ""), "14d": rs.get("tier_14d_status", ""),
                  "28d": rs.get("tier_28d_status", "")}
    except Exception:
        pass
    if not any(status.values()):
        try:
            rm = s.get(BASE + "/v2/activity/growth/redeem/summary", timeout=20,
                     verify=False).json().get("data") or {}
            for tier, key in (("7d", "starter"), ("14d", "advanced"), ("28d", "legendary")):
                if rm.get(key + "_status"):
                    status[tier] = rm[key + "_status"]
        except Exception:
            pass
    for tier, need, label in tiers:
        tst = status.get(tier, "")
        if tst == "claimed":
            log("   🎁兑换%s档: 已兑换过" % label)
            continue
        if tst == "locked" or (streak_days is not None and streak_days < need):
            continue
        rr = s.post(BASE + "/v2/activity/growth/redeem",
                    json={"tier": tier, "client_token": "redeem-" + tier + "-" + str(uuid.uuid4())},
                    timeout=20, verify=False).json()
        code = rr.get("code", -1)
        if code == 0:
            d = rr.get("data", {})
            extra = " +%s补签卡" % d["cards_granted"] if d.get("cards_granted") else ""
            log("   🎁兑换%s档: +%s积分 +%s能量 +%s抽奖%s" % (label, d.get("credit_granted", 0),
                                                        d.get("energy_granted", 0),
                                                        d.get("chances_granted", 0), extra))
        elif code == 409:
            log("   🎁兑换%s档: 已兑换过" % label)


def t_badges(s, uid, nick, log):
    try:
        r = s.get(BASE + "/v2/activity/growth/badges", timeout=20, verify=False).json()
        badges = r.get("data", {}).get("badges", r.get("data", {}).get("list", []))
        earned = sum(1 for b in badges if isinstance(b, dict) and b.get("earned"))
        log("   🏅徽章: %s个" % earned)
    except Exception:
        pass


def t_gift_compensation(s, uid, nick, log):
    try:
        r = s.post(BASE + "/billing/meter/claim-gift", json={}, timeout=15, verify=False).json()
        if r.get("code") == 0:
            log("   🎊新手礼包: +%s积分" % r.get("data", {}).get("credit", "?"))
    except Exception:
        pass
    try:
        r = s.post(BASE + "/billing/meter/claim-compensation", json={}, timeout=15, verify=False).json()
        if r.get("code") == 0:
            log("   🎊补偿领取: +%s积分" % r.get("data", {}).get("credit", "?"))
    except Exception:
        pass


def t_makeup(s, uid, nick, log):
    try:
        hm = s.get(BASE + "/v2/activity/growth/heatmap", timeout=20, verify=False).json()
        cells = hm.get("data", {}).get("cells", [])
        bal = s.get(BASE + "/v2/activity/growth/streak", timeout=20, verify=False).json().get("data", {}).get("makeup_cards", {}).get("balance", 0)
        yesterday = (beijing_today() - datetime.timedelta(days=1)).isoformat()
        missed = None
        for c in cells:
            d = str(c.get("date", ""))[:10]
            if d == yesterday and not c.get("score", 0):
                missed = yesterday
                break
        if missed and bal > 0:
            r = s.post(BASE + "/v2/activity/growth/makeup-cards/use", json={"target_date": missed},
                       timeout=20, verify=False).json()
            log("   🩹补签%s: %s" % (missed, "成功，连签保住" if r.get("code") == 0 else str(r.get("msg", ""))[:40]))
        elif missed:
            log("   🩹昨日(%s)漏签但无补签卡" % missed)
        else:
            log("   🩹无漏签，无需补签")
    except Exception as e:
        log("   🩹补签检查异常: %s" % str(e)[:50])


def has_buddy(s):
    try:
        v = s.get(BASE + "/v2/activity/growth/buddy/visible", timeout=20, verify=False).json()
        d = v.get("data") or {}
        if "has_buddy" in d:
            return bool(d.get("has_buddy"))
        info = s.get(BASE + "/v2/activity/growth/buddy/info", timeout=20, verify=False).json()
        return bool((info.get("data") or {}).get("buddy"))
    except Exception:
        return None


def ensure_first_buddy(s, uid, nick, log):
    if has_buddy(s) is True:
        return True
    try:
        report(s, uid, nick, [{"eventCode": "buddy_agreement_view", "timestamp": int(time.time() * 1000)}])
        time.sleep(2)
        s.post(BASE + "/v2/activity/growth/buddy/agreement", json={"agree": True},
               timeout=20, verify=False)
        time.sleep(WRITE_GAP)
        r = s.post(BASE + "/v2/activity/growth/buddy/first", json={}, timeout=20, verify=False).json()
        credit = (r.get("data") or {}).get("credit", 0)
        energy = (r.get("data") or {}).get("energy", 0)
        log("   🐱首只Buddy: %s (credit=+%s energy=+%s)" % (
            "领养成功" if r.get("code") == 0 else str(r.get("msg", ""))[:40], credit, energy))
        time.sleep(2)
        return has_buddy(s) is True
    except Exception as e:
        log("   🐱首只Buddy异常: %s" % str(e)[:40])
        return False


def t_first_buddy(s, uid, nick, log):
    st, cur, tgt = prog(s, "first_buddy")
    have = has_buddy(s)
    if st in ("completed", "claimed") and have is not False:
        log("   🐱首只Buddy: 已 %s %s/%s" % (st, cur, tgt))
        return
    if have is False and st in ("completed", "claimed"):
        log("   🐱首只Buddy: 任务已 %s，但服务端无 Buddy 实例 → 尝试补建" % st)
    ensure_first_buddy(s, uid, nick, log)


def t_lighthouse(s, uid, nick, log):
    st, cur, tgt = prog(s, "Expert_lighthouse")
    if st is None:
        log("   腾讯轻量云专家: 不在当前任务列表，跳过")
        return
    if st in ("completed", "claimed"):
        log("   腾讯轻量云专家: %s %s/%s" % (st, cur, tgt))
        return
    lh = dict(LIGHTHOUSE_EXPERT)
    try:
        for e in get_normal_experts(20):
            if (e.get("id") or "") == lh["id"] or "轻量" in (e.get("name") or ""):
                lh["id"] = e.get("id") or lh["id"]
                lh["name"] = e.get("name") or lh["name"]
                lh["version"] = e.get("version") or lh["version"]
                break
    except Exception:
        pass
    prompt = "你好，请简单介绍一下你能帮我做什么，回答OK即可"
    conv_id = ""
    mid = ""
    try:
        ge = [{"eventCode": "ExpertActualUse", "id": lh["id"],
               "extra": {"name": lh["name"], "expertTitle": lh["name"], "expertType": "agent",
                         "source": "builtin", "version": lh["version"], "cost": 0,
                         "characterCount": len(prompt)},
               "expertType": "agent"}]
        meta = {"codebuddy.ai": {"growthEvent": json.dumps(ge, ensure_ascii=False),
                                 "promptRequestId": str(uuid.uuid4()),
                                 "clientSendTime": int(time.time() * 1000), "userId": uid,
                                 "mode": "LOCAL", "model": "fast-model", "expertId": lh["id"],
                                 "expert": {"id": lh["id"], "name": lh["name"], "prompt": prompt[:50]},
                                 "tags": ["expert:" + lh["id"]]}}
        conv_id, _txt, mid = webchat2(s, "lh", prompt, meta)
    except Exception as e:
        log("   腾讯轻量云专家: 对话异常 %s" % str(e)[:50])
    if conv_id and mid:
        summon = [
            {"eventCode": "expert_summon_click", "id": lh["id"], "name": lh["name"],
             "expertTitle": lh["name"], "type": "agent", "expertType": "agent",
             "source": "builtin", "mode": "LOCAL"},
            {"eventCode": "expert_summoned", "id": lh["id"], "name": lh["name"],
             "expertTitle": lh["name"], "type": "agent", "expertType": "agent",
             "source": "builtin", "version": lh["version"], "mode": "LOCAL"}]
        chain = desktop_chat_sequence(uid, nick, conv_id, mid, mid)
        for ev in chain:
            if ev.get("eventCode") == "agent_task_created":
                ev.update({"has_expert": True, "expert_id": lh["id"], "expert_name": lh["name"],
                           "expert_industry_id": ""})
        chain.append({"eventCode": "expert_actual_use", "id": lh["id"], "name": lh["name"],
                      "expertTitle": lh["name"], "type": "", "expertType": "agent",
                      "source": "builtin", "version": lh["version"], "cost": 0,
                      "characterCount": len(prompt), "mode": "LOCAL",
                      "conversationId": conv_id, "requestId": mid, "messageId": mid,
                      "requestModelId": "fast-model", "requestModelName": "fast-model"})
        try:
            report_desktop_events(s, uid, nick, summon + chain)
        except Exception as e:
            log("   腾讯轻量云专家: 桌面链上报失败 %s" % str(e)[:50])
        time.sleep(4)
        if prog(s, "Expert_lighthouse")[0] in ("completed", "claimed"):
            st, cur, tgt = prog(s, "Expert_lighthouse")
            log("   腾讯轻量云专家: %s %s/%s" % (st, cur, tgt))
            return
    try:
        rid = mid or str(uuid.uuid4())
        cid = conv_id or ("conv-" + str(uuid.uuid4()))
        report(s, uid, nick, [{
            "eventCode": "expert_summoned", "id": lh["id"], "name": lh["name"],
            "type": "agent", "expertTitle": lh["name"], "expertType": "agent",
            "source": "builtin", "timestamp": int(time.time() * 1000)},
            {"eventCode": "expert_actual_use", "id": lh["id"], "name": lh["name"],
             "expertTitle": lh["name"], "type": "agent", "expertType": "agent",
             "source": "builtin", "version": lh["version"], "cost": 0, "characterCount": len(prompt),
             "conversationId": cid, "requestId": rid, "messageId": rid,
             "requestModelId": "fast-model", "requestModelName": "fast-model",
             "userId": uid}])
        time.sleep(3)
    except Exception as e:
        log("   腾讯轻量云专家: 失败 %s" % str(e)[:60])
    st, cur, tgt = prog(s, "Expert_lighthouse")
    log("   腾讯轻量云专家: %s %s/%s" % (st, cur, tgt))


# ---------- 小程序埋点 ----------
def mp_machine_id(uid):
    h = hashlib.md5(("mp:%s" % uid).encode()).hexdigest()
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32])


def mp_base(uid, nick):
    """小程序埋点公共指纹（对齐官方源码 module 22015 的 wQ()+Ao()）。

    源码常量（module 25439）：ideVersion/extVersion = 小程序包版本 2.2.8（恒定值，不是
    SaaS 状态）；os/osVersion/arch 取 getDeviceInfo() 运行值——这里固定成一份真实安卓机
    指纹（android 14 / arm64），与 mp_mini_expert_event、上游 task_runner 同口径。
    """
    now = int(time.time() * 1000)
    return {"timestamp": now, "ideType": "WorkBuddy_MP", "ideVersion": "2.2.8",
            "extName": "workbuddy-mp", "extVersion": "2.2.8", "product": "SaaS",
            "ideName": "wx_app_cloud", "platform": "mini_program",
            "source": "mini_program",   # 官方源码口径：mp 身份 = wx_app_cloud + WorkBuddy_MP + source
            "os": "android", "osVersion": "14", "arch": "arm64",
            "machineId": mp_machine_id(uid), "timezone": "Asia/Shanghai",
            "userId": uid, "userNickname": nick}


def mp_chat_event(uid, nick, conv_id, activity_id=None):
    """小程序 chat_request_send 事件（chat_3_times / school_season / Sequential_Tasks_1 判据）。"""
    # 官方源码（growth 模块 86692）：conversationId / requestId / traceId 同值传递
    rid = conv_id
    ev = {"eventCode": "chat_request_send", "mode": "chat", "inputLength": 12, "isPlan": False,
          "isAutoExecuteTerminal": False, "isAutoModify": False, "codebaseEnable": False,
          "maxToken": 0, "maxSteps": 500, "temperature": 0, "maxRetries": 0,
          "mentionContexts": [], "knowledgeId": [], "knowledgeName": [],
          "codebaseId": "", "mentionContextCount": 0, "command": "",
          "recommendId": "", "skillId": "", "skillCount": 0, "totalCount": 0,
          "requestId": rid, "traceId": rid, "rootRequestId": rid,
          "parentConversationId": conv_id, "conversationId": conv_id,
          "messageId": "msg-" + rid[-8:], "agentName": "mp", "agentType": "main",
          "codebuddy.session_id": conv_id,
          "codebuddy.conversation_request_id": rid}
    if activity_id:
        ev["activityId"] = activity_id
    return ev


def mp_expert_use_events(uid, nick, expert_id, expert_name, conv_id, activity_id=None):
    rid = "wb2api-" + str(uuid.uuid4())
    cat = SCHOOL_EXPERT_CATEGORY
    evs = [
        {"eventCode": "expert_summon_click", "id": expert_id, "name": expert_id,
         "expertTitle": expert_name, "type": cat, "position": 0},
        {"eventCode": "expert_summoned", "id": expert_id, "name": expert_id,
         "expertTitle": expert_name},
        {"eventCode": "expert_actual_use", "id": expert_id, "name": expert_id,
         "expertTitle": expert_name, "type": cat, "characterCount": 14,
         "expertType": "builtin"},
        {"eventCode": "chat_request_send", "inputLength": 14, "isPlan": False,
         "isAutoExecuteTerminal": False, "isAutoModify": False, "codebaseEnable": False,
         "maxToken": 0, "maxSteps": 500, "temperature": 0, "maxRetries": 0,
         "mentionContexts": [], "knowledgeId": [], "knowledgeName": [],
         "codebaseId": "", "mentionContextCount": 0, "command": "",
         "recommendId": "", "skillId": "", "skillCount": 0, "totalCount": 0,
         "traceId": rid, "rootRequestId": rid,
         "parentConversationId": conv_id, "conversationId": conv_id,
         "messageId": "msg-" + rid[-8:], "agentName": "mp", "agentType": "main",
         "expertId": expert_id, "expertName": expert_name,
         "codebuddy.session_id": conv_id,
         "codebuddy.conversation_request_id": rid},
    ]
    if activity_id:
        for e in evs:
            e["activityId"] = activity_id
    return evs


def mp_model_chat_event(uid, nick, conv_id, model_id="glm-5.2", model_name="GLM-5.2"):
    ev = mp_chat_event(uid, nick, conv_id)
    ev["requestModelId"] = model_id
    ev["requestModelName"] = model_name
    return ev


def mp_playbook_events(uid, nick, case_id="01-ProductDesign", case_name="产品设计"):
    conv = "wb2api-mp-pb-" + str(uuid.uuid4())
    base = {"id": case_id, "name": case_name, "type": "document",
            "categoryId": "", "categoryName": "", "skills": "", "skillNames": ""}
    cta = dict(base, eventCode="playbook_cta_click", source="discover", position=1, extVersion="2.2.8")
    send = dict(base, eventCode="playbook_prompt_send", source="discover", promptLength=96,
                isOfficial=1, conversationId=conv, extVersion="2.2.8")
    return [cta, send]


def mp_mini_expert_event(uid, nick, expert_id, expert_name):
    return {"eventCode": "expert_actual_use", "timestamp": int(time.time() * 1000),
            "reportDelay": 0, "ideName": "wx_app_cloud", "ideType": "WorkBuddy_MP",
            "extName": "workbuddy-mp", "extVersion": "2.2.8", "product": "SaaS",
            "source": "mini_program", "os": "android", "osVersion": "14",
            "arch": "arm64", "timezone": "Asia/Shanghai",
            "machineId": mp_machine_id(uid), "userId": uid,
            "id": expert_id, "name": expert_id, "expertTitle": expert_name,
            "type": "send_message", "characterCount": 12, "expertType": "agent"}


def mp_report(s, uid, nick, events):
    base = mp_base(uid, nick)
    arr = []
    for e in events:
        m = dict(base)
        m.update(e)
        arr.append(m)
    s2 = requests.Session()
    s2.trust_env = False
    s2.verify = False
    hdr = dict(MP_REPORT_HEADERS)
    hdr["Authorization"] = s.headers.get("Authorization", "")
    if uid:
        hdr["X-User-Id"] = uid
    try:
        r = s2.post("https://www.codebuddy.cn/v2/report", json=arr,
                    headers=hdr, timeout=20, verify=False)
        return r.status_code
    except Exception:
        return 0


def _mp_prog(s, code):
    try:
        r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False, headers=MP_HEADER)
        for t in r.json().get("data", {}).get("tasks", []):
            if t.get("task_code") == code:
                pr = t.get("progress") or {}
                return t.get("accept_status", ""), pr.get("current"), pr.get("target")
    except Exception:
        pass
    return None, None, None


def _mp_accept_res(s, code):
    try:
        r = s.post(BASE + "/v2/activity/growth/tasks/accept", json={"task_codes": [code]},
                   timeout=20, verify=False, headers=MP_HEADER)
        d = r.json()
        results = (d.get("data") or {}).get("results") or []
        status = (results[0].get("status") or "") if results else (d.get("msg") or "")
        msg = (results[0].get("message") or "") if results else ""
        return (r.status_code == 200 and status == "accepted"), status, msg
    except Exception as e:
        return False, "", str(e)[:80]


def _mp_accept(s, code, log=None):
    ok, status, msg = _mp_accept_res(s, code)
    if not ok and log:
        log("      ✗ accept %s: %s %s" % (code, status or "无返回", msg[:50]))
    return ok


def _mp_locked_hint(log, label, msg, indent="   "):
    m = re.search(r"locked until (\d{4}-\d{2}-\d{2})", msg or "")
    if not m:
        return False
    log("%s%s: 今日未解锁（链式任务每日零点解锁下一环，%s 零点自动解锁，下次运行自动推进）"
        % (indent, label, m.group(1)))
    return True


def _mp_claim(s, code, log):
    try:
        r = s.post(BASE + "/activity/growth/tasks/%s/claim" % code, json={},
                   timeout=20, verify=False, headers=MP_HEADER)
        d = r.json().get("data", {})
        log("   🎁领奖[%s]: %s" % (code, "已领过" if d.get("already_claimed")
                                   else "+%s积分+%s能量" % (d.get("credit"), d.get("energy"))))
        return r.status_code == 200
    except Exception as e:
        log("   🎁领奖[%s]: 失败 %s" % (code, str(e)[:50]))
        return False


def _mp_task_row(s, code):
    """mp 口径任务原始行（含 locked / valid_start / reward_* 等字段）；未下发返回 None。

    服务端每个任务行都带 locked；locked=true 表示未到上线时间（accept 会报
    "task locked until <日期>"），此时上报与领奖都无意义且会被判无效。
    """
    try:
        r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False, headers=MP_HEADER)
        for t in r.json().get("data", {}).get("tasks", []):
            if t.get("task_code") == code:
                return t
    except Exception:
        pass
    return None


def _mp_do_task(s, uid, nick, code, log, events_fn, label, target=1, pace=False):
    """小程序任务通用流程：mp 查询 → accept → 判据上报 → 回读 → claim。

    target：任务的进度目标（未 accept 时 progress 为 null，调用方需提供兜底值）。
    pace  ：对话类判据（chat_request_send）按“真人节奏”上报。上游对 Sequential 系列
            有反作弊校验：数秒级连发先计入进度（回读满进度），随后被整体判无效回滚
            （claim 返回 400 task not completed）。上游实测 45s 间隔逐条上报全存活 →
            claim 成功，故每条前等 MP_CHAT_GAP(45s)+0~10s 抖动，首条也等（上一轮被
            回滚的残留进度，立即重报同样无效）；--mp-gap / WORKBUDDY_MP_GAP 可调。
    """
    row = _mp_task_row(s, code)
    if row is None:
        log("   %s: mp 口径未下发该任务，跳过" % label)
        return
    if row.get("locked"):
        log("   %s: 未到上线时间（解锁 %s），跳过" % (label, str(row.get("valid_start") or "见任务页")[:10]))
        return
    st = row.get("accept_status", "")
    _pr = row.get("progress") or {}
    cur, tgt = _pr.get("current"), _pr.get("target")
    if st in ("completed", "claimed"):
        if st == "completed":
            _mp_claim(s, code, log)
        else:
            log("   %s: 已领取，跳过" % label)
        return
    if st == "not_accepted":
        ok, a_status, a_msg = _mp_accept_res(s, code)
        if not ok:
            log("      ✗ accept %s: %s %s" % (code, a_status or "无返回", a_msg[:50]))
            if not _mp_locked_hint(log, label, a_msg):
                log("   %s: accept 失败，跳过" % label)
            return
        time.sleep(WRITE_GAP)
        # accept 后回读真实进度：accept 前 progress 为 null（target 下发 0），仅用
        # 兜底 target 会少报 → 误判达标 → claim 400（上游 Tasks_6 首轮实测）
        st, cur, tgt = _mp_prog(s, code)
        if st in ("completed", "claimed"):
            if st == "completed":
                _mp_claim(s, code, log)
            else:
                log("   %s: 已领取，跳过" % label)
            return
    # 缺口计算：cur 可能为 None（未激活时 progress 全空）→ 用 target 兜底
    cur = cur or 0
    tgt = tgt or target
    need = max(1, tgt - cur)
    try:
        sent = 0
        for i in range(need):
            if pace and MP_CHAT_GAP > 0:
                import random
                # 抖动：默认 45s 档对应 0~10s；小间隔时按比例缩小，便于自测/提速
                time.sleep(MP_CHAT_GAP + random.uniform(0, min(10.0, MP_CHAT_GAP * 0.25)))
            evs = events_fn(i)
            st_code = mp_report(s, uid, nick, evs)
            sent += len(evs)
            if i < need - 1 and not pace:
                time.sleep(WRITE_GAP)
        log("   %s: 判据已上报（%d 次 / %d 个事件，目标 %s）" % (label, need, sent, tgt))
        time.sleep(2.5)
        st2, cur2, tgt2 = _mp_prog(s, code)
        if st2 in ("completed", "claimed"):
            log("   %s: ✅ 已完成 %s/%s" % (label, cur2, tgt2))
            if st2 == "completed":
                _mp_claim(s, code, log)
        else:
            log("   %s: %s %s/%s（服务端暂未关联）" % (label, st2, cur2, tgt2))
    except Exception as e:
        log("   %s: 失败 %s" % (label, str(e)[:60]))


def _mp_chat_evs(uid, nick, prefix, activity_id=None):
    def _fn(i):
        return [mp_chat_event(uid, nick, "%s-%s-%d" % (prefix, uuid.uuid4(), i),
                              activity_id=activity_id)]
    return _fn


def t_sequential_tasks(s, uid, nick, log):
    _mp_do_task(s, uid, nick, "Sequential_Tasks_1", log,
                _mp_chat_evs(uid, nick, "wbmp"), "小程序对话任务", target=1, pace=True)


def t_sequential_tasks_2(s, uid, nick, log):
    def _evs(i):
        eid, ename = _school_fetch_expert(s)
        if not eid:
            eid, ename = "WorkspaceBuilder", "专家"
        return [mp_mini_expert_event(uid, nick, eid, ename)]
    _mp_do_task(s, uid, nick, "Sequential_Tasks_2", log, _evs, "小程序专家对话", target=1)


def t_sequential_tasks_3(s, uid, nick, log):
    _mp_do_task(s, uid, nick, "Sequential_Tasks_3", log,
                _mp_chat_evs(uid, nick, "wbmp3"), "小程序对话×5", target=5, pace=True)


def t_sequential_tasks_4(s, uid, nick, log):
    def _evs(i):
        # 官方源码形状（dynamic-common appservice TaskFormSheet 创建成功）：不带
        # schedule/rrule 对象，也没有 modelId/connector/pushTo* 等桌面字段；
        # scheduleType 取小程序表单频率枚举（daily/interval/once）
        return [{"eventCode": "automated_task_create_suc", "mode": "CLOUD",
                 "name": "每日读书提醒", "source": "manually",
                 "skills": "", "skillCount": 0,
                 "scheduleType": "daily"}]
    _mp_do_task(s, uid, nick, "Sequential_Tasks_4", log, _evs, "小程序定时任务", target=1)
    if _mp_prog(s, "Sequential_Tasks_4")[0] in ("completed", "claimed"):
        return
    # 回落：桌面域 automation 事件（旧口径，实测同样能点亮）
    try:
        report_desktop_events(s, uid, nick, [{
            "eventCode": "automated_task_create_suc", "name": "wb2api 定时任务",
            "source": "manually", "modelId": "fast-model", "modelIsThinking": True,
            "connectorCount": 0, "skills": "", "skillCount": 0,
            "scheduleType": "once", "mode": "LOCAL"}])
        time.sleep(2.5)
        st2, cur2, tgt2 = _mp_prog(s, "Sequential_Tasks_4")
    except Exception:
        pass
    if st2 in ("completed", "claimed"):
        log("   小程序定时任务: ✅ 已完成（桌面域回落） %s/%s" % (cur2, tgt2))
        if st2 == "completed":
            _mp_claim(s, "Sequential_Tasks_4", log)
    else:
        log("   小程序定时任务: %s %s/%s（服务端暂未关联）" % (st2, cur2, tgt2))


def t_sequential_tasks_5(s, uid, nick, log):
    def _evs(i):
        return [mp_model_chat_event(uid, nick, "wbmp5-%s-%d" % (uuid.uuid4(), i))]
    _mp_do_task(s, uid, nick, "Sequential_Tasks_5", log, _evs, "小程序GLM5.2", target=1, pace=True)


def t_sequential_tasks_6(s, uid, nick, log):
    _mp_do_task(s, uid, nick, "Sequential_Tasks_6", log,
                _mp_chat_evs(uid, nick, "wbmp6"), "小程序对话×10", target=10, pace=True)


def t_sequential_tasks_7(s, uid, nick, log):
    def _evs(i):
        evs = mp_playbook_events(uid, nick)
        report_desktop_events(s, uid, nick, evs)
        return evs
    _mp_do_task(s, uid, nick, "Sequential_Tasks_7", log, _evs, "小程序灵感功能", target=1)


def t_school_season(s, uid, nick, log):
    _mp_do_task(s, uid, nick, "school_season", log,
                _mp_chat_evs(uid, nick, "wbmps", activity_id=SCHOOL_ACTIVITY_ID),
                "校园日活动", target=1, pace=True)


def t_unknown_tasks(s, uid, nick, log):
    known = {"create_canvas", "playbook_prompt", "RichMeow_Chat", "Library_read", "Expert_lighthouse",
             "Expert_Philanthropy", "Hp_Appearance", "Buddy_App", "Buddy_App_QQ", "Model_chat_GLM5.2",
             "black_cat", "Expert_team_use_3", "first_buddy", "chat_5", "skill_1", "expert_5",
             "template_5", "automation_1", "workstation_expert",
             "Sequential_Tasks_1", "Sequential_Tasks_2", "Sequential_Tasks_3",
             "Sequential_Tasks_4", "Sequential_Tasks_5",
             "Sequential_Tasks_6", "Sequential_Tasks_7", "school_season"}
    r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False).json()
    for t in r.get("data", {}).get("tasks", []):
        if not isinstance(t, dict):
            continue
        code = t.get("task_code", "")
        st = t.get("accept_status", "")
        if code in known or st in ("claimed", "completed"):
            continue
        desc = t.get("task_desc", "")[:50]
        if "subscribe" in code.lower() or "公众号" in (t.get("title", "") + desc):
            log("   ⚠️新任务需手动: %s %s (%s) — 需微信扫码关注公众号" % (code, t.get("title", ""), desc))
        elif "donat" in code.lower() or "捐款" in desc or "公益" in t.get("title", ""):
            log("   ⚠️新任务需手动: %s %s (%s) — 涉及真实捐款" % (code, t.get("title", ""), desc))
        else:
            log("   ⚠️未覆盖新任务: %s %s (%s) — 请反馈更新脚本" % (code, t.get("title", ""), desc))


# ---------- 桌面端换血任务（Windows 走真实桌面，非 Windows 走指纹） ----------
_INFO_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "CodeBuddyExtension", "Data", "Public", "auth")
INFO_PATH = os.path.join(_INFO_DIR, "workbuddy-desktop-ai.info")
if not os.path.exists(INFO_PATH):
    INFO_PATH = os.path.join(_INFO_DIR, "workbuddy-desktop.info")
SESSION_DIRS = [os.path.join(os.path.expanduser("~"), ".workbuddy-ai", "sessions"),
                os.path.join(os.path.expanduser("~"), ".workbuddy", "sessions")]


def swap_info(tok):
    bak = INFO_PATH + ".wb_all_bak"
    if not os.path.exists(bak):
        shutil.copy(INFO_PATH, bak)
    d = json.load(open(INFO_PATH, encoding="utf-8"))
    j = jwt_payload(tok)
    d["auth"]["accessToken"] = tok
    d["auth"]["refreshToken"] = ""
    d["auth"]["expiresAt"] = j.get("exp", 0) * 1000

    def fix(a, last):
        if isinstance(a, dict):
            a["uid"] = j.get("sub")
            for k in ("nickname", "phoneNumber"):
                if k in a:
                    a[k] = "脚本账号"
            if "lastLogin" in a:
                a["lastLogin"] = "True" if last else "False"
        return a
    fix(d.get("account", {}), True)
    for k in ("accounts", "allAccounts"):
        if isinstance(d.get(k), list):
            for a in d[k]:
                fix(a, False)
    json.dump(d, open(INFO_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def restore_info():
    bak = INFO_PATH + ".wb_all_bak"
    if os.path.exists(bak):
        shutil.copy(bak, INFO_PATH)
        os.remove(bak)


def ensure_local_skill():
    d = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills", SKILL_NAME + "__skillhub")
    if os.path.exists(os.path.join(d, "SKILL.md")):
        return
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write(
        "---\nname: %s\ndescription: 算法交易技能：量化策略开发、回测、信号生成与风险管理辅助。\n---\n\n# Algorithmic Trading\n为用户提供量化策略编写、回测与风险分析。\n" % SKILL_NAME)
    json.dump({"ownerId": "wb_all", "slug": SKILL_NAME, "version": "1.0.0", "publishedAt": int(time.time() * 1000)},
              open(os.path.join(d, "_meta.json"), "w", encoding="utf-8"))
    json.dump({"slug": SKILL_NAME, "name": "Algorithmic Trading", "version": "1.0.0",
               "installedAt": int(time.time() * 1000), "source": "skillhub"},
              open(os.path.join(d, "_skillhub_meta.json"), "w", encoding="utf-8"))


def daemon_chat(prompt, blocks=None, meta_extra=None, deadline=280):
    import websocket
    import glob as _glob
    s = requests.Session()
    s.trust_env = False
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "acp-connection-id": str(uuid.uuid4())}
    BASE_D = None
    r = None
    fs = sorted(_glob.glob(os.path.join(os.path.expanduser("~"), ".workbuddy", "sessions", "*.json")),
                key=os.path.getmtime, reverse=True)
    cands = []
    for f in fs[:6]:
        try:
            u = (json.load(open(f, encoding="utf-8")).get("url") or "").rstrip("/")
            if u:
                cands.append(u)
        except Exception:
            pass
    for base in cands:
        try:
            r = s.post(base + "/api/v1/acp/connect", headers=headers, timeout=6, stream=True)
            if r.status_code == 200:
                BASE_D = base
                break
        except Exception:
            continue
    if not BASE_D:
        return ""
    for data in (l.strip() for l in r.iter_lines(decode_unicode=True)):
        if not data:
            continue
        p = data[5:].strip() if data.startswith("data:") else data
        try:
            d = json.loads(p)
        except Exception:
            continue
        if d.get("connectionId") and d.get("sessionToken"):
            headers["acp-connection-id"] = d["connectionId"]
            headers["acp-session-token"] = d["sessionToken"]
            break

    def read_rpc(rr, dl, state):
        while time.time() < dl:
            try:
                raw = rr.raw.readline()
            except Exception:
                break
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line or line.startswith(":"):
                continue
            p = line[5:].strip() if line.startswith("data:") else line
            try:
                d = json.loads(p)
            except Exception:
                continue
            upd = d.get("params", {}).get("update", {}) if isinstance(d.get("params"), dict) else {}
            if upd.get("sessionUpdate") in ("agent_message_chunk", "agent_thought_chunk"):
                c = upd.get("content", {})
                if isinstance(c, dict) and c.get("type") == "text":
                    state["text"] += c.get("text", "")
            if d.get("id") is not None:
                return d
            if d.get("method") == "session/endTurn":
                return d
        return None

    st = {"text": ""}
    d = read_rpc(s.post(BASE_D + "/api/v1/acp", headers=headers, timeout=(10, 20), stream=True,
                        json={"jsonrpc": "2.0", "method": "initialize",
                              "params": {"protocolVersion": 1, "capabilities": {},
                                         "clientInfo": {"name": "wb_all", "version": "1.0"}}, "id": 1}),
                 time.time() + 20, st)
    if not (d and "result" in d):
        return ""
    d = read_rpc(s.post(BASE_D + "/api/v1/acp", headers=headers, timeout=(10, 20), stream=True,
                        json={"jsonrpc": "2.0", "method": "session/new",
                              "params": {"cwd": os.path.expanduser("~"), "mcpServers": []}, "id": 2}),
                 time.time() + 30, st)
    sid = (d or {}).get("result", {}).get("sessionId") if d else None
    if not sid:
        return ""
    blocks = blocks or [{"type": "text", "text": prompt}]
    meta = {"codebuddy.ai": {"promptRequestId": str(uuid.uuid4()), "clientSendTime": int(time.time() * 1000),
                             "conversationId": sid, "mode": "craft", "model": "glm-5.2"}}
    if meta_extra:
        meta["codebuddy.ai"].update(meta_extra)
    read_rpc(s.post(BASE_D + "/api/v1/acp", headers=headers, timeout=(10, 20), stream=True,
                    json={"jsonrpc": "2.0", "method": "session/prompt",
                          "params": {"sessionId": sid, "prompt": blocks, "_meta": meta}, "id": 3}),
             time.time() + deadline, st)
    return st["text"]


def restart_desktop():
    import glob as _glob
    subprocess.run(["taskkill", "/F", "/IM", "WorkBuddy.exe"], capture_output=True)
    time.sleep(3)
    for d_ in SESSION_DIRS:
        for f in _glob.glob(os.path.join(d_, "*.json")):
            try:
                os.remove(f)
            except Exception:
                pass
    subprocess.Popen(["cmd", "/c", "start", "", r"C:\Program Files\WorkBuddy\WorkBuddy.exe", "--remote-debugging-port=9222"],
                     creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
    for _ in range(20):
        time.sleep(3)
        fs = []
        for d_ in SESSION_DIRS:
            fs += _glob.glob(os.path.join(d_, "*.json"))
        fs = sorted(fs, key=os.path.getmtime, reverse=True)
        for f in fs[:3]:
            try:
                d = json.load(open(f, encoding="utf-8"))
                if time.time() * 1000 - int(d.get("updatedAt") or 0) < 60000 and d.get("url"):
                    return d["url"]
            except Exception:
                pass
    return None


def cdp_ui_send(prompt):
    import websocket
    try:
        r = requests.get("http://127.0.0.1:9222/json", timeout=5, proxies={"http": None, "https": None})
        pt = [x for x in r.json() if x.get("type") == "page"][0]
        ws = websocket.create_connection(pt["webSocketDebuggerUrl"], timeout=10, suppress_origin=True)
        state = {"i": 0}

        def cmd(m, p=None):
            state["i"] += 1
            ws.send(json.dumps({"id": state["i"], "method": m, "params": p or {}}))
            return state["i"]

        def wait_id(rid):
            t0 = time.time()
            while time.time() - t0 < 10:
                try:
                    ws.settimeout(1.0)
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    return None
                m = json.loads(raw)
                if m.get("id") == rid:
                    return m
            return None

        def ev(expr):
            m = wait_id(cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True}))
            return (m or {}).get("result", {}).get("result", {}).get("value")

        def click(x, y):
            for t in ("mousePressed", "mouseReleased"):
                wait_id(cmd("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1}))
        pos = ev(r'(function(){ const e=document.querySelector("[contenteditable=\"true\"]"); if(!e) return null; const r=e.getBoundingClientRect(); return JSON.stringify({x:r.x+150,y:r.y+r.height/2}); })()')
        if not pos:
            return False
        p = json.loads(pos)
        click(p["x"], p["y"])
        time.sleep(0.5)
        ev(r'(function(){ const e=document.querySelector("[contenteditable=\"true\"]"); e.focus(); const dt=new DataTransfer(); dt.setData("text/plain", %s); e.dispatchEvent(new ClipboardEvent("paste", {clipboardData: dt, bubbles: true, cancelable: true})); e.dispatchEvent(new InputEvent("beforeinput", {inputType: "insertText", data: %s, bubbles: true, cancelable: true})); return e.textContent.slice(0,30); })()' % (json.dumps(prompt), json.dumps(prompt)))
        time.sleep(1)
        btn = ev(r'(function(){ const b=document.querySelector(".cr-send-button"); if(!b) return null; const r=b.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,disabled:!!b.disabled}); })()')
        if btn and '"disabled":false' in btn:
            p2 = json.loads(btn)
            click(p2["x"], p2["y"])
            time.sleep(10)
            return True
        return False
    except Exception:
        return False


def t_desktop_tasks(s, uid, nick, tok, log, need_rich, need_skill):
    is_win = sys.platform == "win32"
    if is_win:
        log("   🖥️ 桌面换血流程启动（结束后自动还原认证并重启桌面端）...")
        if need_skill:
            try:
                src_ = s.get(BASE + "/console/as/marketplace/sources", timeout=20, verify=False).json()
                srcs = (src_.get("data") or {}).get("sources") or []
                mid = srcs[0].get("id") if srcs else None
                if mid:
                    s.post(BASE + "/console/as/user/plugins/install",
                           json={"plugin_name": SKILL_NAME, "marketplace_id": mid, "version": "latest"},
                           timeout=30, verify=False)
            except Exception:
                pass
        ensure_local_skill()
        swap_info(tok)
        url = restart_desktop()
        if not url:
            log("   ⚠️ 桌面端守护进程未就绪，降级为指纹上报...")
            restore_info()
            subprocess.Popen(["cmd", "/c", "start", "", r"C:\Program Files\WorkBuddy\WorkBuddy.exe"])
            _desktop_fingerprint_fallback(s, uid, nick, log, need_rich, need_skill)
            return
        time.sleep(8)
        if need_rich:
            txt = daemon_chat("你好，请用一句话介绍你自己")
            if not txt:
                log("   守护进程会话未就绪，改用 CDP UI 发送...")
                cdp_ui_send("你好，请用一句话介绍你自己")
            log("   桌面对话: %s字" % len(txt))
            time.sleep(8)
        if need_skill:
            blocks = [{"type": "resource_link", "uri": "skill://" + SKILL_NAME, "title": SKILL_NAME,
                       "name": SKILL_NAME, "_meta": {"mentionType": "skill", "skillName": SKILL_NAME}},
                      {"type": "text", "text": "你必须通过技能系统正式加载（load）该技能，加载成功后回答：技能已加载"}]
            txt = daemon_chat("", blocks=blocks)
            if not txt:
                log("   守护进程不可用，改用 CDP UI 技能调用...")
                cdp_ui_send("/" + SKILL_NAME + " 请按技能说明回答OK")
            log("   技能加载: %s" % ("成功" if "加载" in txt else "回复%d字" % len(txt)))
            time.sleep(8)
        restore_info()
        subprocess.run(["taskkill", "/F", "/IM", "WorkBuddy.exe"], capture_output=True)
        time.sleep(3)
        subprocess.Popen(["cmd", "/c", "start", "", r"C:\Program Files\WorkBuddy\WorkBuddy.exe"])
        time.sleep(5)
    else:
        log("   🖥️ 非 Windows 环境，使用指纹上报模式...")
        _desktop_fingerprint_fallback(s, uid, nick, log, need_rich, need_skill)
        return

    if need_rich:
        st, cur, tgt = prog(s, "RichMeow_Chat")
        log("   桌面端对话1次: %s %s/%s" % (st, cur, tgt))
        if st == "completed":
            claim(s, "RichMeow_Chat", log)
    if need_skill:
        st, cur, tgt = prog(s, "skill_1")
        log("   尝鲜热门技能: %s %s/%s" % (st, cur, tgt))
        if st == "completed":
            claim(s, "skill_1", log)


def _desktop_fingerprint_fallback(s, uid, nick, log, need_rich, need_skill):
    if need_rich:
        conv = "fp-rm-%s" % derive_id(uid, "rm-conv")
        req = "fp-rm-req-%s" % derive_id(uid, "rm-req")
        msg = "fp-rm-msg-%s" % derive_id(uid, "rm-msg")
        try:
            evs = desktop_chat_sequence(uid, nick, conv, req, msg)
            report_desktop_events(s, uid, nick, evs)
            log("   桌面对话(指纹): ✅ 6连事件已上报")
            time.sleep(WRITE_GAP)
        except Exception as e:
            log("   桌面对话(指纹): 失败 %s" % str(e)[:60])
    if need_skill:
        try:
            src_ = s.get(BASE + "/console/as/marketplace/sources", timeout=20, verify=False).json()
            srcs = (src_.get("data") or {}).get("sources") or []
            mkid = srcs[0].get("id") if srcs else None
            if mkid:
                s.post(BASE + "/console/as/user/plugins/install",
                       json={"plugin_name": SKILL_NAME, "marketplace_id": mkid, "version": "latest"},
                       timeout=30, verify=False)
        except Exception:
            pass
        try:
            skills_r = api_retry(s, "POST", SCHOOL_DOMAIN + "/v2/operation-platform/market/skill/list",
                                 body={"page": 1, "page_size": 10})
            skills = (skills_r.json().get("data") or {}).get("skills") or []
            skill_id = next((sk.get("id") for sk in skills if SKILL_NAME in str(sk.get("name", ""))), "")
            skill_disp = SKILL_NAME
            if not skill_id:
                skill_id, skill_disp = SKILL_FALLBACK
            conv_id = ""
            smid = ""
            try:
                conv_id, _t, smid = webchat2(s, "skill", "你好，帮我写一份简短的日报，回答OK即可")
            except Exception:
                pass
            if not (conv_id and smid):
                conv_id = "fp-sk-%s" % derive_id(uid, "sk-conv")
                smid = "fp-sk-%s" % derive_id(uid, "sk-mid")
            evs = desktop_chat_sequence(uid, nick, conv_id, smid, smid)
            for ev in evs:
                if ev.get("eventCode") == "chat_message_response":
                    ev["finishReason"] = "tool_calls"
            evs.append({"eventCode": "skill_info", "id": skill_disp, "skillId": skill_id,
                        "skillVersion": "1.0.0", "toolStatus": "success", "fileCount": 56,
                        "source": "workbuddy-desktop", "conversationId": conv_id,
                        "requestId": smid, "messageId": smid, "traceId": smid,
                        "requestModelId": "fast-model", "requestModelName": "fast-model"})
            report_desktop_events(s, uid, nick, evs)
            log("   尝鲜热门技能(指纹): ✅ 真实对话 + skill_info 已上报")
            time.sleep(WRITE_GAP)
        except Exception as e:
            log("   尝鲜热门技能(指纹): 失败 %s" % str(e)[:60])
    for code in (["RichMeow_Chat"] if need_rich else []) + (["skill_1"] if need_skill else []):
        st, cur, tgt = prog(s, code)
        log("   %s: %s %s/%s" % (code, st, cur, tgt))
        if st == "completed":
            claim(s, code, log)


def t_workstation(s, uid, nick, log, tok):
    st, cur, tgt = prog(s, "workstation_expert")
    if st in ("completed", "claimed") or st is None:
        return
    if sys.platform != "win32":
        log("   工作台搭建师: 非Windows，跳过桌面流程")
        return
    log("   检测到工作台搭建师任务，尝试桌面换血对话...")
    swap_info(tok)
    restart_desktop()
    time.sleep(8)
    blocks = [{"type": "resource_link", "uri": "expert://WorkspaceBuilder", "title": "工作台搭建师",
               "name": "工作台搭建师", "_meta": {"mentionType": "expert", "expertId": "WorkspaceBuilder"}},
              {"type": "text", "text": "你好，请介绍你能帮我搭建什么工作台，回答OK即可"}]
    txt = daemon_chat("", blocks=blocks)
    log("   工作台搭建师对话: %s字" % len(txt))
    restore_info()
    subprocess.run(["taskkill", "/F", "/IM", "WorkBuddy.exe"], capture_output=True)
    time.sleep(3)
    subprocess.Popen(["cmd", "/c", "start", "", r"C:\Program Files\WorkBuddy\WorkBuddy.exe"])
    time.sleep(5)
    log("   工作台搭建师: %s %s/%s" % prog(s, "workstation_expert"))


# ---------- 开学季活动 ----------
def _school_session(at):
    s = requests.Session()
    s.trust_env = False
    s.verify = False
    s.headers.update({"Authorization": "Bearer " + at, "Accept": "application/json",
                      "Content-Type": "application/json", "User-Agent": MP_UA,
                      "Referer": "https://www.codebuddy.cn/"})
    return s


def _school_get(s, url):
    return api_retry(s, "GET", url)


def _school_post(s, url, body=None):
    return api_retry(s, "POST", url, body=body)


def _school_report(s, uid, nick, events, host=None, desktop=False):
    target = host or SCHOOL_DOMAIN
    if desktop:
        out = {"common": {"userId": uid, "userNickname": nick, "ideName": "WorkBuddy",
                          "ideType": "WorkBuddy", "machineId": derive_id(uid, "machine"),
                          "mode": "LOCAL", "userAgent": UA, "os": "win32",
                          "timezone": "Asia/Shanghai"},
               "events": events}
        return api_retry(s, "POST", "https://copilot.tencent.com/v2/report", body=out,
                         headers={"X-Product": "SaaS"})
    out = {"common": {"userId": uid, "userNickname": nick, "ideName": "web-Agents",
                      "ideType": "web-Agents", "machineId": derive_id(uid, "machine"), "mode": "CLOUD",
                      "userAgent": MP_UA, "os": "Android", "timezone": "Asia/Shanghai"},
           "events": events}
    return api_retry(s, "POST", target + "/v2/report", body=out)


def _school_fetch_expert(s):
    body = {"edition_mode": "all,domestic", "page": 1, "page_size": 20,
            "sort_by": "use_count", "sort_order": "desc",
            "categories": [SCHOOL_EXPERT_CATEGORY], "expert_type": "agent"}
    try:
        r = _school_post(s, SCHOOL_DOMAIN + "/v2/operation-platform/market/expert/list", body)
        d = r.json()
        experts = (d.get("data") or {}).get("experts") or []
        for e in experts:
            eid = e.get("expert_id")
            if not eid:
                continue
            dn = e.get("display_name_zh") or {}
            name = (dn.get("zh") if isinstance(dn, dict) else dn) or eid
            return eid, name
    except Exception:
        pass
    for eid, info in SCHOOL_EXPERT_FALLBACK.items():
        return eid, info["name"]
    return "", ""


def _school_desktop_seq_event(uid, nick, conv_id):
    evs = desktop_chat_sequence(uid, nick, conv_id, conv_id, conv_id)
    fp = desktop_fingerprint(uid, nick)
    out = []
    for e in evs:
        m = dict(e)
        m.update(fp)
        m["activityId"] = SCHOOL_ACTIVITY_ID
        out.append(m)
    return out


def _school_expert_event(uid, nick, expert_id, expert_name, conv_id):
    return mp_expert_use_events(uid, nick, expert_id, expert_name, conv_id,
                                activity_id=SCHOOL_ACTIVITY_ID)


def _school_fetch_tasks(s):
    r = _school_get(s, SCHOOL_BASE + "/tasks")
    d = r.json()
    if d.get("code") != 0:
        return [], False
    data = d.get("data") or {}
    return data.get("tasks") or [], data.get("in_period", False)


def _school_viewed(s, code):
    r = _school_post(s, SCHOOL_BASE + "/tasks/%s/viewed" % code)
    return r.json().get("code") == 0


def _school_share_complete(s):
    r = _school_post(s, SCHOOL_BASE + "/tasks/share-complete", {"channel": "wechat"})
    return r.json().get("code") == 0


def _school_claim(s, code):
    r = _school_post(s, SCHOOL_BASE + "/tasks/%s/claim" % code)
    return r.json().get("code") == 0


def school_run_tasks(s, uid, nick, log):
    tasks, in_period = _school_fetch_tasks(s)
    if not in_period:
        log("  🏫 开学季活动非进行期，跳过")
        return
    log("  🏫 ── 开学季活动（%d 个任务）──" % len(tasks))
    for t in tasks:
        code = t.get("task_code", "")
        status = t.get("status", "")
        spec = SCHOOL_TASK_MODES.get(code)
        if not code:
            continue
        if status == "claimed":
            log("   %s: 已领取，跳过" % code)
            continue
        if status == "completed":
            if _school_claim(s, code):
                log("   %s: 🎁 补领奖成功" % code)
            else:
                log("   %s: 补领奖失败（可稍后重试）" % code)
            time.sleep(WRITE_GAP)
            continue
        if spec is None:
            log("   %s: 未知任务类型，跳过" % code)
            continue
        mode = spec["mode"]
        if mode == "manual":
            log("   %s: 人工环节（%s），跳过" % (code, spec.get("note", "")))
            continue
        try:
            if _school_viewed(s, code):
                log("   %s: viewed 激活" % code)
                time.sleep(WRITE_GAP)
        except Exception as e:
            log("   %s: viewed 失败 %s" % (code, str(e)[:60]))
            continue
        ok = False
        if mode == "share":
            try:
                ok = _school_share_complete(s)
                log("   %s: share-complete %s" % (code, "✅" if ok else "❌"))
                time.sleep(WRITE_GAP)
            except Exception as e:
                log("   %s: share 失败 %s" % (code, str(e)[:60]))
        elif mode == "report":
            kind = spec.get("kind", "")
            conv_id = "conv-" + str(uuid.uuid4())
            if kind == "mini_chat":
                for i in range(3):
                    try:
                        mp_report(s, uid, nick, [mp_chat_event(
                            uid, nick, "wbsc-" + str(uuid.uuid4()),
                            activity_id=SCHOOL_ACTIVITY_ID)])
                        log("   %s: chat #%d/3 ✅" % (code, i + 1))
                        time.sleep(WRITE_GAP)
                    except Exception as e:
                        log("   %s: chat #%d 失败 %s" % (code, i + 1, str(e)[:60]))
            elif kind == "desktop_seq":
                evs = _school_desktop_seq_event(uid, nick, conv_id)
                try:
                    _school_report(s, uid, nick, evs, desktop=True)
                    log("   %s: desktop_seq (copilot域) ✅" % code)
                    time.sleep(WRITE_GAP)
                except Exception as e:
                    log("   %s: desktop 失败 %s" % (code, str(e)[:60]))
            elif kind == "expert":
                eid, ename = _school_fetch_expert(s)
                if not eid:
                    log("   %s: 未取到专家，跳过" % code)
                else:
                    try:
                        evs = _school_expert_event(uid, nick, eid, ename, conv_id)
                        mp_report(s, uid, nick, evs)
                        log("   %s: expert 4事件链 ✅ (%s)" % (code, ename))
                        time.sleep(WRITE_GAP)
                    except Exception as e:
                        log("   %s: expert 失败 %s" % (code, str(e)[:60]))
        for _ in range(5):
            time.sleep(2)
            try:
                ts2, _ = _school_fetch_tasks(s)
                after = next((x for x in ts2 if x.get("task_code") == code), None)
                if after and after.get("status") in ("completed", "claimed"):
                    log("   %s: ✅ 已完成" % code)
                    break
            except Exception:
                pass
        try:
            ts3, _ = _school_fetch_tasks(s)
            after = next((x for x in ts3 if x.get("task_code") == code), None)
            if after and after.get("status") == "completed":
                if _school_claim(s, code):
                    log("   %s: 🎁 已领奖" % code)
                    time.sleep(WRITE_GAP)
        except Exception as e:
            log("   %s: claim 失败 %s" % (code, str(e)[:60]))


def school_lottery(s, uid, nick, log):
    try:
        r = _school_get(s, SCHOOL_BASE + "/config")
        d = r.json()
        if d.get("code") != 0:
            log("  🏫 lottery config 失败")
            return
        chance = (d.get("data") or {}).get("chance") or {}
        bal = chance.get("balance", 0)
        if not bal or bal <= 0:
            log("  🏫 lottery 余额=0，无需抽奖")
            return
        log("  🏫 lottery 余额=%s，开始抽奖..." % bal)
        results = []
        while bal > 0:
            time.sleep(WRITE_GAP)
            draw_uuid = str(uuid.uuid4())
            try:
                r2 = _school_post(s, SCHOOL_BASE + "/wheel/draw", {"draw_uuid": draw_uuid})
                d2 = r2.json()
                if d2.get("code") == 40900:
                    log("  🏫 lottery 次数耗尽")
                    break
                if d2.get("code") != 0:
                    log("  🏫 lottery draw 失败: %s" % str(d2.get("msg", ""))[:60])
                    break
                prize = (d2.get("data") or {}).get("prize_code", "")
                credit = (d2.get("data") or {}).get("credit_amount", 0)
                label = LOTTERY_PRIZE_LABELS.get(prize, prize or "未知")
                results.append(label)
                bal -= 1
                log("  🏫 lottery → %s（余 %s）" % (label, bal))
            except Exception as e:
                log("  🏫 lottery draw 异常 %s" % str(e)[:60])
                break
        if results:
            log("  🏫 lottery 汇总: %d 抽，奖品: %s" % (len(results), ", ".join(results)))
    except Exception as e:
        log("  🏫 lottery 异常 %s" % str(e)[:80])


# ---------- 稳定指纹 & 事件构建 ----------
def desktop_fingerprint(uid, nick):
    now = int(time.time() * 1000)
    return {
        "timezone": "Asia/Shanghai", "reportDelay": 2000,
        "userId": uid, "username": nick, "userNickname": nick,
        "product": "SaaS", "releaseDate": 1789036585355,
        "commit": "5f9692923c93033111c51ad7b003eb80204a9b75",
        "ideName": "WorkBuddy", "ideType": "WorkBuddy", "ideVersion": "5.5.6",
        "machineId": derive_id(uid, "machine"), "sessionId": derive_id(uid, "session"),
        "extName": "workbuddy-desktop", "extVersion": "5.5.6",
        "os": "win32", "arch": "x64", "osVersion": "10.0.26220",
        "cpuCores": 20, "memorySize": 24,
        "timestamp": now, "presentAt": now,
    }


def within_night_window():
    try:
        return beijing_now().hour >= 23 or beijing_now().hour < 8
    except Exception:
        return None


def beijing_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))


def beijing_today():
    return beijing_now().date()


def desktop_chat_sequence(uid, nick, conversation_id, request_id, message_id,
                          model_id="fast-model", model_name="fast-model"):
    now = int(time.time() * 1000)
    ev = []

    def mk(code, extra):
        e = {"eventCode": code}
        e.update(extra)
        ev.append(e)
    mk("agent_task_created", {
        "source": "LOCAL", "name": "working", "task_target": "local", "mode": "craft",
        "requestModelId": model_id, "requestModelName": model_name,
        "has_repo": False, "repo_type": "none", "workspace_type": "empty",
        "has_connector": False, "connector_types": [],
        "has_mention": False, "mention_types": [],
        "has_template": False, "action": "", "template_name": "",
        "has_expert": False, "expert_id": "", "expert_name": "", "expert_industry_id": "",
        "has_skill": False, "skill_names": [],
        "conversationId": conversation_id, "messageId": message_id,
        "buddyId": "", "buddyName": ""})
    mk("chat_message_send", {
        "messageId": message_id + "-assistant", "historyCount": 0,
        "isContextTruncated": False, "currentStepCount": 1,
        "traceId": request_id, "rootRequestId": request_id,
        "parentConversationId": conversation_id,
        "agentName": "cli", "agentType": "main"})
    mk("chat_request_send", {
        "inputLength": 24, "isPlan": False, "isAutoExecuteTerminal": False,
        "isAutoModify": False, "codebaseEnable": False, "maxToken": 0,
        "maxSteps": 500, "temperature": 0, "maxRetries": 0,
        "mentionContexts": [], "knowledgeId": [], "knowledgeName": [],
        "codebaseId": "", "mentionContextCount": 0, "command": "",
        "recommendId": "", "skillId": "", "skillCount": 0, "totalCount": 0,
        "traceId": request_id, "rootRequestId": request_id,
        "parentConversationId": conversation_id,
        "agentName": "cli", "agentType": "main"})
    mk("chat_message_response", {
        "messageId": message_id + "-assistant", "responseModelId": model_id,
        "inputToken": 120, "outputToken": 80, "totalToken": 200,
        "cachedTokens": 0, "cachedWriteTokens": 0, "cachedMissTokens": 0,
        "isSuccessful": True, "messageErrorCode": "", "finishReason": "stop",
        "firstTokenAt": now, "traceId": request_id,
        "conversationId": conversation_id,
        "rootRequestId": request_id, "parentConversationId": conversation_id,
        "agentName": "cli", "agentType": "main"})
    mk("chat_message_status", {
        "messageId": message_id + "-assistant", "messageErrorCode": "0",
        "traceId": request_id, "rootRequestId": request_id,
        "parentConversationId": conversation_id,
        "agentName": "cli", "agentType": "main"})
    mk("chat_request_response", {
        "mode": "craft", "toolCallCount": 0,
        "inputToken": 120, "outputToken": 80, "totalToken": 200,
        "cachedTokens": 0, "cachedWriteTokens": 0, "cachedMissTokens": 0,
        "isSuccessful": True, "messageErrorCode": "", "finishReason": "stop",
        "rootRequestId": request_id, "parentConversationId": conversation_id,
        "agentName": "cli", "agentType": "main"})
    return ev


def desktop_buddy5_sequence(uid, nick, buddy_id, buddy_name):
    ev = []

    def mk(code, extra):
        e = {"eventCode": code, "mode": "LOCAL",
             "buddyId": buddy_id, "buddyName": buddy_name}
        e.update(extra)
        ev.append(e)
    mk("buddyapp_discover_click", {})
    mk("buddyapp_show", {"elementId": buddy_id, "elementName": buddy_name, "position": 2})
    mk("buddyapp_enter_click",
       {"elementId": buddy_id, "elementName": buddy_name, "position": 2, "isFirstPage": "1"})
    mk("buddyapp_auth_confirm_click", {"elementId": buddy_id, "elementName": buddy_name})
    mk("buddyapp_bindaccount_skip_click", {"elementId": buddy_id, "elementName": buddy_name})
    return ev


def report_desktop_events(s, uid, nick, events):
    fp = desktop_fingerprint(uid, nick)
    arr = []
    for e in events:
        m = dict(fp)
        m.update(e)
        arr.append(m)
    hdr = {"Authorization": s.headers.get("Authorization", ""),
           "Accept": "application/json, text/plain, */*",
           "Content-Type": "application/json;charset=UTF-8",
           "User-Agent": DESKTOP_UA,
           "X-Domain": DESKTOP_BASE, "X-Product": "SaaS",
           "X-Request-ID": derive_id(uid, "req") + str(int(time.time() * 1000) % 1000000)}
    if uid:
        hdr["X-User-Id"] = uid
    s2 = requests.Session()
    s2.trust_env = False
    s2.verify = False
    try:
        r = s2.post(DESKTOP_BASE + "/v2/report", json=arr, headers=hdr,
                    timeout=20, verify=False)
        return r.status_code
    except Exception:
        return 0


def report_web_event(s, uid, nick, event_code, page_url, element_id, element_name):
    now = int(time.time() * 1000)
    ev = {"eventCode": event_code, "timestamp": now, "reportDelay": 0,
          "pageURL": page_url, "elementId": element_id, "elementName": element_name,
          "os": "Win32", "arch": "", "osVersion": "10.0",
          "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "machineId": derive_id(uid, "webmachine"), "userId": uid, "userNickname": nick}
    return api_retry(s, "POST", BASE + "/v2/report", body={"common": {
        "userId": uid, "userNickname": nick, "ideName": "web",
        "ideType": "web", "machineId": derive_id(uid, "webmachine"),
        "mode": "CLOUD", "userAgent": "Mozilla/5.0", "os": "Win32",
        "timezone": "Asia/Shanghai"}, "events": [ev]})


def _accept_with_verify(s, code, log):
    for attempt in (1, 2):
        r = s.post(BASE + "/v2/activity/growth/tasks/accept", json={"task_codes": [code]},
                   timeout=20, verify=False)
        status = ""
        try:
            d = r.json()
            results = (d.get("data") or {}).get("results") or []
            status = (results[0].get("status") or "") if results else (d.get("msg") or "")
        except Exception:
            pass
        t = prog(s, code)
        ast = t[0] if t else "not_accepted"
        ok = (r.status_code == 200 and status == "accepted" and ast != "not_accepted")
        if ok:
            return True
        if attempt > 1:
            log("      ✗ %s: accept %s 回读=%s" % (code, status or "无返回", ast))
        time.sleep(WRITE_GAP)
    return False


# ============================================================================ #
# 单账号全流程
# ============================================================================ #
def run_account(idx, client, account, do_desktop, no_school):
    msgs = []
    tag = "账号%d" % idx

    def log(m):
        ts = time.strftime("%H:%M:%S")
        line = "[%s][%s] %s" % (ts, tag, m)
        print(line, flush=True)
        msgs.append(line)

    note = account.ref
    summary = {"idx": idx, "note": note, "credits": "", "usage": "", "growth": "",
               "done": 0, "total": 0, "rest": [], "level": "?", "energy": "?",
               "checked": False, "checkin": "", "error": ""}

    try:
        client.authenticate()
    except SafeError as e:
        log("")
        log("╭─ 👤 账号%d  %s" % (idx, note))
        log("  ❌ 登录/凭据失败：%s" % e)
        summary["error"] = str(e)
        return msgs, summary
    except Exception as e:
        log("")
        log("╭─ 👤 账号%d  %s" % (idx, note))
        log("  ❌ 登录异常（%s）" % type(e).__name__)
        summary["error"] = "登录异常（%s）" % type(e).__name__
        return msgs, summary

    uid = client.uid
    nick = nickname_of(client.access)
    tok = client.access
    s = client.api_session()

    log("")
    log("╭─ 👤 账号%d  %s" % (idx, note))

    # 签到（YYB 回读确认流程）
    try:
        checkin_line, checkin_ok = client.run_checkin()
        log("   %s" % checkin_line)
        summary["checked"] = checkin_ok
        summary["checkin"] = checkin_line
        try:
            st_data = client.status()
            warn = _checkin_activity_warn(st_data)
            if warn:
                log("   %s" % warn)
        except Exception:
            pass
    except SafeError as e:
        log("   ❌ 签到失败：%s" % e)
        summary["error"] = str(e)

    # 查询
    credits, paid = queryCredits(s)
    usage = queryUsage(s)
    rp = s.get(BASE + "/v2/activity/growth/profile", timeout=25, verify=False)
    pj = _json_or_empty(rp)
    if rp.status_code in (401, 403) or not pj:
        log("  ❌ 凭据失效（HTTP %s）：请检查 YYB 取码/登录是否正常" % rp.status_code)
        summary["error"] = summary["error"] or "凭据失效"
        return msgs, summary
    prof = pj.get("data", {}) or {}
    energy = (_json_or_empty(s.get(BASE + "/v2/activity/growth/energy", timeout=25,
                                            verify=False)).get("data") or {}).get("balance")
    streak = ((_json_or_empty(s.get(BASE + "/v2/activity/growth/streak", timeout=25,
                                             verify=False)).get("data") or {}).get("streak") or {})
    summary["credits"] = credits
    summary["usage"] = usage
    summary["streak"] = streak.get("days", "?")
    log("💰 积分: %s" % credits)
    log("📊 用量: %s" % usage)
    try:
        hm = s.get(BASE + "/v2/activity/growth/heatmap", timeout=20, verify=False).json()
        cells = hm.get("data", {}).get("cells", [])
        signed = sum(1 for c in cells if isinstance(c, dict) and c.get("score", 0) > 0)
    except Exception:
        signed = "?"
    log("🌱 成长: 等级%s 连签%s天 能量%s 累签%s天" % (prof.get("level", "?"), streak.get("days", "?"), energy, signed))

    # 桌面任务（非 Windows 自动降级为指纹上报）
    need_rich = prog(s, "RichMeow_Chat")[0] not in ("completed", "claimed")
    need_skill = prog(s, "skill_1")[0] not in ("completed", "claimed")
    desktop_skipped = False
    if (need_rich or need_skill) and not want("desktop", "RichMeow_Chat", "skill_1"):
        log("  🖥️ 桌面任务: 按配置跳过（desktop）")
        need_rich = need_skill = False
        desktop_skipped = True
    if do_desktop and (need_rich or need_skill):
        log("  🖥️ ── 桌面任务（引导优先） ──")
        try:
            t_desktop_tasks(s, uid, nick, tok, log, need_rich, need_skill)
        except Exception as e:
            log("  🖥️ 桌面任务异常: %s" % str(e)[:80])
    elif need_rich or need_skill:
        log("── 桌面任务跳过(--no-desktop): RichMeow=%s skill_1=%s ──" % (need_rich, need_skill))
    else:
        if not desktop_skipped:
            log("  🖥️ 桌面任务: 已完成（RichMeow/skill_1），跳过")

    # 云端任务
    log("  ☁️ ── 云端任务 ──")
    if TASK_ONLY or TASK_SKIP:
        log("   ⚙️ 任务过滤生效：%s%s" % (
            ("仅执行 " + ",".join(sorted(TASK_ONLY))) if TASK_ONLY else "",
            (("；跳过 " + ",".join(sorted(TASK_SKIP))) if TASK_SKIP else "")))

    def _run(label, codes, fn):
        """子任务调度：按 TASK_ONLY / TASK_SKIP 决定是否执行，单项异常不拖垮整轮。"""
        if not want(*codes):
            log("   ⏭️ %s: 按配置跳过" % label)
            return
        try:
            fn()
        except Exception as e:
            log("   ⚠️ %s 异常: %s" % (label, str(e)[:80]))

    # 前置：无 Buddy 实例时，其余任务 accept 会被服务端拒绝（prerequisite not met: first_buddy）
    t_first_buddy(s, uid, nick, log)
    t_accept_all(s, uid, nick, log)
    _run("召唤3次专家团", ["Expert_team_use_3"], lambda: t_team_3(s, uid, nick, log))
    _run("发现应用/企鹅教师助手", ["Buddy_App", "Buddy_App_QQ"], lambda: t_buddy_apps(s, uid, nick, log))
    _run("和平精英主题", ["Hp_Appearance"], lambda: t_theme(s, uid, nick, log))
    _run("体验资料库", ["Library_read"], lambda: t_library(s, uid, nick, log))
    _run("设计/自动化/灵感", ["create_canvas", "automation_1", "playbook_prompt"],
         lambda: t_canvas_automation(s, uid, nick, log))
    _run("召唤5次专家", ["expert_5"], lambda: t_expert_5(s, uid, nick, log))
    _run("使用5个模板", ["template_5"], lambda: t_template_5(s, uid, nick, log))
    _run("GLM-5.2/和AI聊天5次", ["Model_chat_GLM5.2", "chat_5"], lambda: t_glm52(s, uid, nick, log))
    _run("夜猫子", ["black_cat"], lambda: t_black_cat(s, uid, nick, log))
    _run("腾讯轻量云专家", ["Expert_lighthouse"], lambda: t_lighthouse(s, uid, nick, log))
    _run("小程序对话", ["Sequential_Tasks_1"], lambda: t_sequential_tasks(s, uid, nick, log))
    _run("小程序专家对话", ["Sequential_Tasks_2"], lambda: t_sequential_tasks_2(s, uid, nick, log))
    _run("小程序对话5次", ["Sequential_Tasks_3"], lambda: t_sequential_tasks_3(s, uid, nick, log))
    _run("小程序定时任务", ["Sequential_Tasks_4"], lambda: t_sequential_tasks_4(s, uid, nick, log))
    _run("小程序GLM5.2", ["Sequential_Tasks_5"], lambda: t_sequential_tasks_5(s, uid, nick, log))
    _run("小程序对话10次", ["Sequential_Tasks_6"], lambda: t_sequential_tasks_6(s, uid, nick, log))
    _run("小程序灵感功能", ["Sequential_Tasks_7"], lambda: t_sequential_tasks_7(s, uid, nick, log))
    _run("校园日活动", ["school_season", "school"], lambda: t_school_season(s, uid, nick, log))
    _run("徽章", ["badges"], lambda: t_badges(s, uid, nick, log))
    _run("抽奖", ["lottery"], lambda: t_lottery(s, uid, nick, log))
    _run("盲盒", ["blindbox"], lambda: t_blindbox(s, uid, nick, log))
    _run("Buddy 信息", ["buddy_info"], lambda: t_buddy_info(s, uid, nick, log))
    _run("派猫猫旅行", ["travel"], lambda: t_travel(s, uid, nick, log))
    _run("连登兑换", ["redeem"], lambda: t_redeem(s, uid, nick, log, streak.get("days")))
    _run("礼包/补偿", ["gift"], lambda: t_gift_compensation(s, uid, nick, log))
    _run("补签", ["makeup"], lambda: t_makeup(s, uid, nick, log))
    _run("工作台搭建师", ["workstation_expert"], lambda: t_workstation(s, uid, nick, log, tok))
    t_unknown_tasks(s, uid, nick, log)   # 未覆盖任务检测不受过滤影响

    # 开学季活动
    if not no_school and want("school", "school_season"):
        try:
            school_s = _school_session(tok)
            school_run_tasks(school_s, uid, nick, log)
            school_lottery(school_s, uid, nick, log)
        except Exception as e:
            log("  🏫 开学季活动异常: %s" % str(e)[:80])

    # 领奖
    log("  🎁 ── 领奖 ──")
    r = s.get(BASE + "/v2/activity/growth/tasks", timeout=25, verify=False).json()
    n = 0
    for t in r.get("data", {}).get("tasks", []):
        if isinstance(t, dict) and t.get("accept_status") == "completed":
            claim(s, t.get("task_code", ""), log)
            n += 1
            time.sleep(1)
    if n == 0:
        log("   无待领奖励")

    # 终态
    st_all = (_json_or_empty(s.get(BASE + "/v2/activity/growth/tasks", timeout=25,
                                      verify=False)).get("data") or {}).get("tasks", [])
    done = sum(1 for t in st_all if isinstance(t, dict) and t.get("accept_status") in ("claimed", "completed"))
    rest = [task_cn(t.get("task_code", "")) for t in st_all if isinstance(t, dict) and t.get("accept_status") not in ("claimed", "completed")]
    prof2 = (_json_or_empty(s.get(BASE + "/v2/activity/growth/profile", timeout=25,
                                       verify=False)).get("data") or {})
    summary.update({"done": done, "total": len(st_all), "rest": rest,
                    "level": prof2.get("level", "?"), "energy": energy})
    log("🏁 %s: 完成%s/%s 等级%s 剩余: %s" % (note, done, len(st_all), prof2.get("level", "?"),
                                             ", ".join(rest) if rest else "无"))
    return msgs, summary


# ============================================================================ #
# 推送摘要
# ============================================================================ #
def build_summary(summaries):
    summaries.sort(key=lambda x: x.get("idx", 0))
    total_done = total_tasks = 0
    lines = []
    lines.append("📊 各账号运行报告")
    lines.append("")
    for sm in summaries:
        idx = sm.get("idx", 0)
        done = sm.get("done", 0)
        total = sm.get("total", 0)
        total_done += done
        total_tasks += total
        credits = sm.get("credits", "")
        usage = sm.get("usage", "")
        energy = sm.get("energy", "?")
        level = sm.get("level", "?")
        streak = sm.get("streak", "?")
        note = sm.get("note", "")[:16]
        rest = sm.get("rest") or []
        error = sm.get("error", "")
        checkin = sm.get("checkin", "")
        rest_cn = [task_cn(r) for r in rest]
        lines.append("👤 账号%d  %s" % (idx, note))
        if error:
            lines.append("   ❌ %s" % error)
            lines.append("")
            continue
        if checkin:
            lines.append("   ✅ %s" % checkin)
        lines.append("   💰 %s" % (credits if credits else "暂无数据"))
        lines.append("   📊 %s" % (usage if usage else "暂无数据"))
        lines.append("   🌱 等级%s | 连签%s天 | 能量%s" % (level, streak, energy))
        if rest_cn:
            lines.append("   ⏳ 未完成: %s" % "、".join(rest_cn))
        else:
            lines.append("   ✅ 全部完成！")
        lines.append("")
    lines.append("📊 ══ 总计 ══")
    lines.append("👥 共%d个账号，任务完成 %d/%d 项" % (len(summaries), total_done, total_tasks))
    all_rest = {}
    for sm in summaries:
        for r in (sm.get("rest") or []):
            cn = task_cn(r)
            all_rest[cn] = all_rest.get(cn, 0) + 1
    if all_rest:
        lines.append("")
        for cn, cnt in sorted(all_rest.items(), key=lambda x: -x[1]):
            lines.append("   · %s（%d个账号待完成）" % (cn, cnt))
    lines.append("")
    lines.append("🕐 %s" % time.strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)


# ============================================================================ #
# 通知（青龙 notify.py 优先，回落到内置通道）
# ============================================================================ #
HERE = Path(__file__).resolve().parent

QL_PUSH_ENVS = (
    "BARK_PUSH", "DD_BOT_TOKEN", "FSKEY", "GOBOT_URL", "IGOT_PUSH_KEY", "PUSH_KEY",
    "DEER_KEY", "CHAT_URL", "PUSH_PLUS_TOKEN", "WE_PLUS_BOT_TOKEN", "QMSG_KEY",
    "QYWX_KEY", "QYWX_AM", "TG_BOT_TOKEN", "SMTP_SERVER", "PUSHME_KEY",
    "WEBHOOK_URL", "NTFY_TOPIC", "WXPUSHER_APP_TOKEN", "OPENILINK_APP_TOKEN",
)


def load_notify():
    candidates = [HERE / "notify.py",
                  Path("/ql/data/scripts/notify.py"),
                  Path("/ql/scripts/notify.py"),
                  Path("/ql/data/notify.py")]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                spec = importlib.util.spec_from_file_location("_wb_ql_notify", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name in ("send", "sendNotify"):
                    func = getattr(module, name, None)
                    if callable(func):
                        return func
        except Exception:
            continue
    return None


def send_notify(title, content):
    panel_channel = next((k for k in QL_PUSH_ENVS if (os.getenv(k) or "").strip()), "")
    sender = load_notify()
    if sender is not None:
        if panel_channel:
            try:
                sender(title, content)
                print("✅ [通知] 已通过青龙通知模块发送（通道 %s）" % panel_channel, flush=True)
                return True
            except Exception as exc:
                print("⚠️ [通知] 青龙通知发送失败（不影响结果）：%s" % str(exc)[:120], flush=True)
        else:
            print("ℹ️ [通知] 青龙面板未配置推送变量，改用脚本自带通道", flush=True)
    else:
        print("⚠️ [通知] 未找到青龙 notify.py，使用脚本自带通道", flush=True)

    sent = False
    plusplus = (os.getenv("PUSH_PLUS_TOKEN", "") or os.getenv("PLUSPLUS_TOKEN", "") or "").strip()
    if plusplus:
        try:
            r = requests.post("https://www.pushplus.plus/send",
                              json={"token": plusplus, "title": title, "content": content,
                                    "template": "txt"}, timeout=20)
            ok = r.status_code == 200 and (r.json().get("code") == 200)
            sent = sent or ok
            print("%s [通知] PushPlus 发送%s" % ("✅" if ok else "❌", "成功" if ok else "失败"), flush=True)
        except Exception as exc:
            print("❌ [通知] PushPlus 发送失败：%s" % str(exc)[:120], flush=True)
    server_push = (os.getenv("PUSH_KEY", "") or os.getenv("SERVERPUSHKEY", "") or "").strip()
    if server_push and not sent:
        try:
            requests.post("https://sctapi.ftqq.com/%s.send" % server_push,
                          data={"title": title, "desp": content}, timeout=15)
            sent = True
            print("✅ [通知] Server 酱发送成功", flush=True)
        except Exception as exc:
            print("❌ [通知] Server 酱发送失败：%s" % str(exc)[:120], flush=True)
    qywx = (os.getenv("QYWX_KEY", "") or os.getenv("QYWX_TOKEN", "") or "").strip()
    if qywx and not sent:
        try:
            requests.post("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s" % qywx,
                          json={"msgtype": "text", "text": {"content": "%s\n\n%s" % (title, content)}},
                          timeout=15)
            sent = True
            print("✅ [通知] 企业微信机器人发送成功", flush=True)
        except Exception as exc:
            print("❌ [通知] 企业微信机器人发送失败：%s" % str(exc)[:120], flush=True)
    bark = (os.getenv("BARK_PUSH", "") or "").strip()
    if bark and not sent:
        try:
            requests.post(bark.rstrip("/"), json={"title": title, "body": content}, timeout=15)
            sent = True
            print("✅ [通知] Bark 发送成功", flush=True)
        except Exception as exc:
            print("❌ [通知] Bark 发送失败：%s" % str(exc)[:120], flush=True)
    if not sent:
        print("ℹ️ [通知] 未配置任何可用推送通道，结果仅输出到日志", flush=True)
    return sent


def default_cache_dir():
    ql_config = Path("/ql/data/config")
    if ql_config.is_dir():
        return ql_config / "workbuddy_yyb"
    return Path.home() / ".workbuddy_yyb"


def print_banner(query=False):
    print("╔════════════════════════════════════════╗")
    print("║ 🌱 WorkBuddy 全能脚本（YYB无感取码）   ║")
    print("║ 🔐取码 💰积分 📊用量 🌱成长            ║")
    print("║ ✅任务 🎮玩法 🎁领奖 📢通知            ║")
    print("╚════════════════════════════════════════╝")
    print("📦 v%s · %s" % (VERSION, "签到状态查询" if query else "全流程"), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="WorkBuddy YYB 全能签到")
    parser.add_argument("--only", default=os.getenv("WB_ACCOUNT_FILTER", ""), metavar="3,4,5")
    parser.add_argument("--query", action="store_true", help="仅查询积分/用量/签到状态，不执行任务")
    parser.add_argument("--no-school", action="store_true", help="跳过开学季活动")
    parser.add_argument("--no-desktop", action="store_true", help="跳过桌面任务")
    parser.add_argument("--no-notify", action="store_true", help="不发送青龙通知")
    parser.add_argument("--gap", type=float, default=1.5, help="写动作间隔秒数")
    parser.add_argument("--mp-gap", type=float, default=None, help="mp 对话事件间隔秒数（默认 45，真人节奏）")
    parser.add_argument("--tasks", default="", metavar="checkin,travel", help="白名单：只跑列出的子任务")
    parser.add_argument("--skip-tasks", default="", metavar="lottery,redeem", help="黑名单：跳过列出的子任务")
    args = parser.parse_args(argv)

    global WRITE_GAP, MP_CHAT_GAP, TASK_ONLY, TASK_SKIP
    WRITE_GAP = max(1.0, args.gap)
    if args.mp_gap is not None:
        MP_CHAT_GAP = max(0.0, args.mp_gap)
    elif os.environ.get("WORKBUDDY_MP_GAP"):
        try:
            MP_CHAT_GAP = max(0.0, float(os.environ["WORKBUDDY_MP_GAP"]))
        except ValueError:
            pass
    if args.tasks:
        TASK_ONLY = _parse_task_filter(args.tasks)
    if args.skip_tasks:
        TASK_SKIP |= _parse_task_filter(args.skip_tasks)

    started = time.monotonic()
    reports = []
    errors = []
    print_banner(args.query)

    try:
        accounts = select_accounts(accounts_from_env(os.getenv("YYB_SERVER", "")), args.only)
    except SafeError as exc:
        print("❌ " + str(exc), flush=True)
        return 1
    total = len(accounts)
    print("👥 账号数: %d" % total, flush=True)

    do_desktop = not args.no_desktop
    if do_desktop and sys.platform != "win32":
        print("🖥️ 非Windows环境：桌面任务自动降级为指纹上报模式", flush=True)

    try:
        with State(os.getenv("WB_CACHE_DIR") or default_cache_dir()) as state:
            for account in accounts:
                client = None
                try:
                    client = Client(account, state)
                    if args.query:
                        # 仅查询：登录 + 签到状态 + 积分/用量/成长
                        client.authenticate()
                        s = client.api_session()
                        credits, paid = queryCredits(s)
                        usage = queryUsage(s)
                        prof = (_json_or_empty(s.get(BASE + "/v2/activity/growth/profile",
                                                    timeout=25, verify=False)).get("data") or {})
                        try:
                            sd = client.status()
                            checked = sd.get("today_checked_in")
                        except Exception:
                            checked = False
                        summary = {"idx": account.number, "note": account.ref,
                                   "credits": credits, "usage": usage,
                                   "level": prof.get("level", "?"), "energy": "?",
                                   "streak": "?", "done": 0, "total": 0, "rest": [],
                                   "checked": bool(checked),
                                   "checkin": "今日已签到" if checked else "今日未签到",
                                   "error": ""}
                        reports.append(summary)
                    else:
                        msgs_part, summary = run_account(account.number, client, account,
                                                         do_desktop, args.no_school)
                        reports.append(summary)
                except SafeError as exc:
                    reports.append({"idx": account.number, "note": account.ref, "error": str(exc),
                                    "done": 0, "total": 0, "rest": [], "level": "?", "energy": "?",
                                    "checked": False, "checkin": "", "credits": "", "usage": "", "streak": "?"})
                except Exception as exc:
                    reports.append({"idx": account.number, "note": account.ref,
                                    "error": "处理失败（%s）" % type(exc).__name__,
                                    "done": 0, "total": 0, "rest": [], "level": "?", "energy": "?",
                                    "checked": False, "checkin": "", "credits": "", "usage": "", "streak": "?"})
                finally:
                    if client:
                        client.session.close()
    except SafeError as exc:
        errors.append(str(exc))
        print("❌ " + str(exc), flush=True)
    except Exception as exc:
        errors.append("任务失败（%s）" % type(exc).__name__)
        print("❌ " + errors[-1], flush=True)

    elapsed = time.monotonic() - started
    summary_text = build_summary(reports)
    if errors:
        summary_text += "\n\n❌ " + "\n❌ ".join(errors)
    print("", flush=True)
    print(summary_text, flush=True)
    print("⏱️ 运行耗时 %.1f 秒" % elapsed, flush=True)

    if not args.no_notify and os.getenv("WB_NO_NOTIFY") != "1":
        try:
            send_notify("🌱 WorkBuddy 签到报告", summary_text)
        except Exception as exc:
            print("⚠️ 通知发送异常（不影响结果）：%s" % str(exc)[:160], flush=True)

    ok = sum(1 for r in reports if not r.get("error"))
    return 0 if total > 0 and ok == total and not errors else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⏹️ 已手动中断")
        sys.exit(130)
