/*
------------------------------------------
@Description: 小铛家 - 微信小程序静默登录 + 每日签到
cron: 32 8 * * *
------------------------------------------
变量名：xiaodangjia
变量值：wx_server 里的 openid/账号标识，多账号用 & 或换行分隔（可加 #备注）

依赖变量：
wx_server_url  默认 http://49.232.164.167:8787
wx_auth        smallcat 鉴权值
------------------------------------------
契约（appid wx7f5bc6f204abc629，host lm.api.sujh.net，Appid头 xiaodangjia）：
  登录  GET  /app/login/wechatLogin?encryptedData=&iv=&code=  -> 顶层 token
         encryptedData/iv 必须来自 smallcat /wx/getphonenumber 的 data.raw，
         code 必须是同一次全新 POST /wx/code 的结果
  积分  GET  /app/score/index?platform=1  -> data:{signIn:0|1, score}
  模板  GET  /app/msgTemplate/list?platform=1&type=6  -> rows:[{templateId}]
  签到  POST /app/score/sign  body {tmplIds:[...], platform:1}  -> code:200 操作成功

  token 用法：Authorization: <裸JWT>（不带 Bearer）；所有请求带 Appid: xiaodangjia
  防重说明：后端按来源 IP 做「同设备已签到」每日防重；本脚本按 openid 派生唯一
           X-Forwarded-For / X-Real-IP，避免同一服务器出口 IP 下多账号被误判同设备。
------------------------------------------
*/

const { Env } = require("../tools/env.js");
const $ = new Env("小铛家");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const WeChatServer = require("./wcs.js");

const ckName = "xiaodangjia";
const MINI_APP_ID = "wx7f5bc6f204abc629";
const BASE = "https://lm.api.sujh.net";
const APP_HEAD = "xiaodangjia";
const TOKEN_CACHE_FILE = path.join(__dirname, "xiaodangjia_token_cache.json");

const USER_AGENT =
    "Mozilla/5.0 (Linux; Android 12; M2012K11AC Build/SKQ1.220303.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) " +
    "Version/4.0 Chrome/134.0.6998.136 Mobile Safari/537.36 MicroMessenger/8.0.48.2580(0x28003036) MiniProgramEnv/android";

// 订阅消息模板兜底（/app/msgTemplate/list?platform=1&type=6 实测值）
const DEFAULT_TMPL_IDS = [
    "nhkbv6By62bsflJku6IndDncDqjmvor_x0V_2dzRoW4",
    "WztbpFu-saGJBQl_PDWCbMVV5brU3mAY4O2Y0tMN9wI",
    "rgg3A6s4bqmguHkeg7eSiBlKdwn-8dTUxQchrdIQQdQ",
];

const wechat = new WeChatServer({
    url: process.env.wx_server_url || "http://49.232.164.167:8787",
    appid: MINI_APP_ID,
    auth: process.env.wx_auth || "",
});

function readCache() {
    try {
        if (!fs.existsSync(TOKEN_CACHE_FILE)) return {};
        return JSON.parse(fs.readFileSync(TOKEN_CACHE_FILE, "utf8")) || {};
    } catch (e) {
        return {};
    }
}

function writeCache(cache) {
    try {
        fs.writeFileSync(TOKEN_CACHE_FILE, JSON.stringify(cache, null, 2), "utf8");
    } catch (e) {
        $.log(`写入token缓存失败: ${e.message || e}`);
    }
}

function parseAccount(raw = "") {
    const [id, remark] = String(raw).split("#").map((s) => (s || "").trim());
    return { openid: id, remark: remark || "" };
}

function short(v, n = 200) {
    const t = typeof v === "string" ? v : JSON.stringify(v);
    return !t ? "" : t.length > n ? `${t.slice(0, n)}...` : t;
}

/** 按 openid 派生唯一来源 IP，规避后端同 IP「同设备」每日防重 */
function deriveIp(openid) {
    const h = crypto.createHash("md5").update(String(openid || "")).digest();
    const a = 64 + (h[0] % 64);      // 64..127
    const b = 1 + (h[1] % 254);      // 1..254
    const c = 1 + (h[2] % 254);      // 1..254
    return `223.${a}.${b}.${c}`;
}

const isOk = (res) => Number(res?.code) === 200;
const msgOf = (res) => res?.msg || res?.message || short(res);
const isAlreadyDone = (t) => /已签|已经签|签到过|重复|同设备|已完成|already/i.test(String(t || ""));

class Task {
    constructor(raw) {
        this.index = $.userIdx++;
        this.account = parseAccount(raw);
        this.openid = this.account.openid;
        this.token = "";
        this.fakeIp = deriveIp(this.openid);
    }

    log(text) {
        $.log(`账号[${this.index}]${this.account.remark ? `[${this.account.remark}]` : ""} ${text}`);
    }

    async request(apiPath, { method = "GET", params = null, body = null, withAuth = true, withFakeIp = false } = {}) {
        const headers = {
            "Content-Type": "application/json",
            Accept: "*/*",
            "User-Agent": USER_AGENT,
            Referer: `https://servicewechat.com/${MINI_APP_ID}/0/page-frame.html`,
            Appid: APP_HEAD,
        };
        if (withAuth && this.token) headers.Authorization = this.token;
        if (withFakeIp) {
            headers["X-Forwarded-For"] = this.fakeIp;
            headers["X-Real-IP"] = this.fakeIp;
        }
        const res = await axios.request({
            method,
            url: `${BASE}${apiPath}`,
            params: params || undefined,
            data: method === "GET" ? undefined : body || {},
            headers,
            timeout: 20000,
            validateStatus: () => true,
        });
        if (res.status !== 200) {
            // 业务结论常躺在 4xx/5xx 的 JSON 体里，交给下游按业务码判
            if (res.data && typeof res.data === "object") return res.data;
            throw new Error(`${apiPath} HTTP ${res.status}: ${short(res.data)}`);
        }
        return res.data;
    }

    async getCode() {
        const res = await wechat.getCode(this.openid);
        const data = res?.data ?? {};
        if (data && data.status === false) {
            throw new Error(`取code失败: ${data.message || short(data)}`);
        }
        const code = data?.data?.code || data?.code;
        if (!code || typeof code !== "string") throw new Error(`未返回 code: ${short(data)}`);
        return code;
    }

    async login() {
        // 每次登录取全新 code + 手机号 encryptedData/iv（smallcat /wx/getphonenumber 的 data.raw）
        const code = await this.getCode();
        const phone = await wechat.getPhoneNumber(this.openid);
        const raw = phone?.data?.data?.raw ?? {};
        const encryptedData = raw.encryptedData ?? raw.encrypted_data ?? "";
        const iv = raw.iv ?? raw.IV ?? "";
        if (!encryptedData || !iv) throw new Error(`未取到手机号 encryptedData/iv: ${short(raw)}`);
        const res = await this.request("/app/login/wechatLogin", {
            params: { encryptedData, iv, code },
            withAuth: false,
        });
        if (!isOk(res)) throw new Error(`登录失败: ${msgOf(res)}`);
        const token = String(res.token || "");
        if (!token) throw new Error(`登录响应缺 token: ${short(res)}`);
        this.token = token;
        const cache = readCache();
        cache[this.openid] = { token, updatedAt: new Date().toISOString() };
        writeCache(cache);
        this.log("登录成功");
    }

    async ensureLogin() {
        const cached = readCache()[this.openid] || {};
        if (!this.token && cached.token) {
            this.token = cached.token;
            const check = await this.request("/app/score/index", { params: { platform: 1 } });
            if (isOk(check)) {
                this.log("使用缓存token");
                return;
            }
            this.log("缓存token失效，重新登录");
            this.token = "";
        }
        if (!this.token) await this.login();
    }

    async getScoreInfo() {
        const res = await this.request("/app/score/index", { params: { platform: 1 } });
        if (!isOk(res)) return null;
        const d = res.data || {};
        return { signIn: Number(d.signIn ?? -1), score: d.score };
    }

    async getTmplIds() {
        const res = await this.request("/app/msgTemplate/list", { params: { platform: 1, type: 6 } });
        const rows = res?.rows;
        if (Array.isArray(rows) && rows.length) {
            const ids = rows.map((r) => r.templateId).filter(Boolean);
            if (ids.length) return ids;
        }
        return DEFAULT_TMPL_IDS.slice();
    }

    async sign() {
        const before = await this.getScoreInfo();
        if (before && before.signIn === 1) {
            this.log(`✅ 今日已签到（积分 ${before.score ?? "-"}）`);
            return;
        }
        const tmplIds = await this.getTmplIds();
        // 签到请求带按 openid 派生的 X-Forwarded-For，规避后端同 IP「同设备」防重
        const res = await this.request("/app/score/sign", {
            method: "POST",
            body: { tmplIds, platform: 1 },
            withFakeIp: true,
        });
        if (isOk(res)) {
            const after = await this.getScoreInfo();
            this.log(`✅ 签到成功${after && after.score !== undefined ? `，当前积分 ${after.score}` : ""}`);
            return;
        }
        if (isAlreadyDone(msgOf(res))) return this.log(`✅ 今日已签到（${msgOf(res)}）`);
        this.log(`❌ 签到失败: ${short(res, 300)}`);
    }

    async run() {
        if (!this.openid) {
            this.log("跳过：变量值里没有 openid");
            return;
        }
        try {
            await this.ensureLogin();
            await this.sign();
        } catch (e) {
            this.log(`执行失败: ${e.message || e}`);
        }
    }
}

!(async () => {
    $.checkEnv(ckName);
    if (!$.userCount) {
        $.log(`未找到变量 ${ckName}`);
        return;
    }
    for (let i = 0; i < $.userList.length; i++) {
        await new Task($.userList[i]).run();
        if (i < $.userList.length - 1) await $.wait(1500, 3000);
    }
})()
    .catch((e) => $.log(e.message || e))
    .finally(() => $.done());
