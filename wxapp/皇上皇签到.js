/*
------------------------------------------
@Description: 皇上皇会员商城签到（微信 code 登录 + 会话缓存兜底）
cron: 15 8 * * *
------------------------------------------
环境变量：hshhyscck
变量值：wx_server 中的 openid/账号标识，多账号用 & 或换行分隔

wx_server_url：code 服务地址，与 wb.js 一致
wx_auth：code 服务鉴权，与 wb.js 一致
HSH_COMPANY_ID：可选，覆盖签到请求的 company_id
HSH_CACHE_FILE：可选，覆盖缓存文件路径
注意：缓存包含 Bearer token，请限制缓存文件的访问权限
------------------------------------------
*/

const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");

const ENV_NAME = "hshhyscck";
const MINI_APP_ID = "wx92342ca7a7cc7313";
const PAGE_VERSION = "101";
const MP_VERSION = "v2605.28.26";
const GROUP_ID = "86043f0548d443f8a96d6b642c466215";
const API_ORIGIN = (process.env.HSH_API_ORIGIN || "https://hshposprd-mgr.gzhsh.com").replace(/\/$/, "");
const CACHE_FILE = process.env.HSH_CACHE_FILE || path.join(__dirname, "hshh_sign_cache.json");
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF";

const API = {
    wxSession: "/api//reabam-wx/weixin/mini_program/get_encrypted_session_info",
    login: "/api//reabam-manage-login/user/login",
    member: "/api/core-retail/appc/member/mine/set",
    signList: "/api/core-retail/appc/mem/act/signinlist",
    sign: "/api/core-retail/appc/mem/act/signin",
};

function log(message = "") {
    console.log(`${new Date().toLocaleString("zh-CN", { hour12: false })} ${message}`);
}

function parseAccounts() {
    const value = process.env[ENV_NAME] || process.env.HSHHYSCCK || "";
    return Array.from(new Set(value.split(/[&\r\n]+/).map((item) => item.trim()).filter(Boolean)));
}

function readCache() {
    try {
        if (!fs.existsSync(CACHE_FILE)) return {};
        const text = fs.readFileSync(CACHE_FILE, "utf8").replace(/^\uFEFF/, "");
        const data = JSON.parse(text);
        return data && typeof data === "object" && !Array.isArray(data) ? data : {};
    } catch (error) {
        log(`读取缓存失败，本次忽略缓存: ${error.message || error}`);
        return {};
    }
}

function writeCache(cache) {
    const tempFile = `${CACHE_FILE}.${process.pid}.tmp`;
    try {
        fs.mkdirSync(path.dirname(CACHE_FILE), { recursive: true });
        fs.writeFileSync(tempFile, JSON.stringify(cache, null, 2), { encoding: "utf8", mode: 0o600 });
        fs.renameSync(tempFile, CACHE_FILE);
        return true;
    } catch (error) {
        try {
            if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
        } catch (_) {
            // 临时文件清理失败不影响主流程。
        }
        log(`写入缓存失败: ${error.message || error}`);
        return false;
    }
}

function responseText(value) {
    if (typeof value === "string") return value;
    try {
        return JSON.stringify(value || {});
    } catch (_) {
        return String(value || "");
    }
}

function isBusinessSuccess(result) {
    return String(result?.code) === "200" && result?.success !== false;
}

function isAuthError(error) {
    if ([401, 403].includes(Number(error?.httpStatus))) return true;
    const businessCode = String(error?.responseData?.code ?? error?.responseData?.status ?? "");
    if (["401", "403", "-401", "-403"].includes(businessCode)) return true;
    const text = `${error?.message || ""} ${responseText(error?.responseData)}`;
    return /(?:unauthorized|forbidden|invalid\s*(?:access\s*)?token|expired\s*(?:access\s*)?token|token.{0,12}(?:invalid|expired|\u65e0\u6548|\u5931\u6548|\u8fc7\u671f|\u4e0d\u5b58\u5728)|authorization.{0,12}(?:invalid|expired|\u65e0\u6548|\u5931\u6548|\u8fc7\u671f)|\u672a\u767b\u5f55|\u8bf7\u5148\u767b\u5f55|\u767b\u5f55\u72b6\u6001.{0,8}(?:\u5931\u6548|\u8fc7\u671f)|\u6388\u6743.{0,8}(?:\u5931\u6548|\u8fc7\u671f)|\u51ed\u8bc1.{0,8}(?:\u5931\u6548|\u8fc7\u671f))/i.test(text);
}

function makeRequestError(message, status, data) {
    const error = new Error(message);
    error.httpStatus = status;
    error.responseData = data;
    return error;
}

function postJson(url, body, headers = {}, timeout = 20000) {
    const target = new URL(url);
    const payload = JSON.stringify(body || {});
    const transport = target.protocol === "http:" ? http : https;

    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (value) => {
            if (settled) return;
            settled = true;
            resolve(value);
        };
        const fail = (error) => {
            if (settled) return;
            settled = true;
            reject(error);
        };
        const request = transport.request({
            protocol: target.protocol,
            hostname: target.hostname,
            port: target.port || undefined,
            path: `${target.pathname}${target.search}`,
            method: "POST",
            headers: {
                ...headers,
                "Content-Type": headers["Content-Type"] || headers["content-type"] || "application/json",
                "Content-Length": Buffer.byteLength(payload),
            },
        }, (response) => {
            const chunks = [];
            response.on("data", (chunk) => chunks.push(chunk));
            response.on("aborted", () => fail(new Error("响应中途断开")));
            response.on("error", fail);
            response.on("end", () => {
                if (settled) return;
                const text = Buffer.concat(chunks).toString("utf8");
                let data = text;
                try {
                    data = text ? JSON.parse(text) : {};
                } catch (_) {
                    // 非 JSON 响应保留原文，便于输出真实错误。
                }
                finish({ status: response.statusCode || 0, data, headers: response.headers });
            });
        });

        request.setTimeout(timeout, () => request.destroy(new Error(`请求超时 ${timeout}ms`)));
        request.on("error", fail);
        request.end(payload);
    });
}

function getJson(url, headers = {}, timeout = 20000) {
    const target = new URL(url);
    const transport = target.protocol === "http:" ? http : https;

    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (value) => {
            if (settled) return;
            settled = true;
            resolve(value);
        };
        const fail = (error) => {
            if (settled) return;
            settled = true;
            reject(error);
        };
        const request = transport.request({
            protocol: target.protocol,
            hostname: target.hostname,
            port: target.port || undefined,
            path: `${target.pathname}${target.search}`,
            method: "GET",
            headers,
        }, (response) => {
            const chunks = [];
            response.on("data", (chunk) => chunks.push(chunk));
            response.on("aborted", () => fail(new Error("响应中途断开")));
            response.on("error", fail);
            response.on("end", () => {
                if (settled) return;
                const text = Buffer.concat(chunks).toString("utf8");
                let data = text;
                try {
                    data = text ? JSON.parse(text) : {};
                } catch (_) {
                    // 非 JSON 响应保留原文。
                }
                finish({ status: response.statusCode || 0, data, headers: response.headers });
            });
        });

        request.setTimeout(timeout, () => request.destroy(new Error(`请求超时 ${timeout}ms`)));
        request.on("error", fail);
        request.end();
    });
}

class AccountTask {
    constructor(accountKey, index) {
        this.accountKey = accountKey;
        this.index = index;
        this.tokenId = "";
        this.openid = "";
        this.companyId = process.env.HSH_COMPANY_ID || "";
        this.loginCompanyId = "";
        this.memberId = "";
        this.phone = "";
        this.usedCache = false;
    }

    prefix(message) {
        log(`账号[${this.index}] ${message}`);
    }

    commonBody(extra = {}) {
        return {
            openId: this.openid,
            wxSn: MINI_APP_ID,
            groupId: GROUP_ID,
            ...extra,
        };
    }

    getHeaders({ auth = true, companyId } = {}) {
        const headers = {
            "User-Agent": USER_AGENT,
            Referer: `https://servicewechat.com/${MINI_APP_ID}/${PAGE_VERSION}/page-frame.html`,
            Accept: "*/*",
            "Content-Type": "application/json",
            mpversion: MP_VERSION,
            group_id: GROUP_ID,
            company_id: companyId !== undefined ? companyId : (this.companyId || ""),
            xweb_xhr: "1",
        };
        if (this.openid) headers.openid = this.openid;
        if (auth && this.tokenId) headers.Authorization = `Bearer ${this.tokenId}`;
        return headers;
    }

    async request(apiPath, body, options = {}) {
        let response;
        try {
            response = await postJson(
                `${API_ORIGIN}${apiPath}`,
                body,
                this.getHeaders(options),
                options.timeout || 20000,
            );
        } catch (error) {
            throw makeRequestError(`网络请求失败: ${error.message || error}`, 0, null);
        }

        if (response.status < 200 || response.status >= 300) {
            throw makeRequestError(`HTTP ${response.status}: ${responseText(response.data)}`, response.status, response.data);
        }
        if (!options.allowAnyCode && !isBusinessSuccess(response.data)) {
            throw makeRequestError(response.data?.msg || response.data?.message || responseText(response.data), response.status, response.data);
        }
        return response.data;
    }

    getCachedSession() {
        return readCache()[this.accountKey] || null;
    }

    applySession(session = {}) {
        this.tokenId = session.tokenId || session.token || "";
        this.openid = session.openid || session.openId || "";
        this.companyId = process.env.HSH_COMPANY_ID || session.companyId || session.bindCompanyId || "";
        this.loginCompanyId = session.loginCompanyId || "";
        this.memberId = session.memberId || session.fid || "";
        this.phone = session.phone || "";
    }

    saveSession(extra = {}) {
        if (!this.tokenId || !this.openid) return false;
        const cache = readCache();
        cache[this.accountKey] = {
            tokenId: this.tokenId,
            openid: this.openid,
            companyId: this.companyId,
            loginCompanyId: this.loginCompanyId,
            wxSn: MINI_APP_ID,
            groupId: GROUP_ID,
            mpversion: MP_VERSION,
            updatedAt: new Date().toISOString(),
            ...extra,
        };
        return writeCache(cache);
    }

    removeCachedSession() {
        const cache = readCache();
        if (cache[this.accountKey]) {
            delete cache[this.accountKey];
            writeCache(cache);
        }
    }

    async getLoginCode() {
        const auth = process.env.wx_auth || "";
        const serverUrl = (process.env.wx_server_url || "http://192.168.31.196:8787").replace(/\/$/, "");

        // YYB 面板模式：wx_auth 填 yyb_ 开头的 API Key，走 YYB 取码接口
        if (/^yyb_/.test(auth)) {
            const base = /yyb/i.test(serverUrl) ? serverUrl : "https://yyb.fuckinghigh.eu.org";
            const qs = `appid=${encodeURIComponent(MINI_APP_ID)}&openid=${encodeURIComponent(this.accountKey)}`;
            let response;
            try {
                response = await getJson(`${base}/yyb/api/code?${qs}`, { "X-API-Key": auth }, 60000);
            } catch (error) {
                throw new Error(`YYB 获取 code 失败: ${error.message || error}`);
            }
            if (response.status < 200 || response.status >= 300) {
                throw new Error(`YYB HTTP ${response.status}: ${responseText(response.data)}`);
            }
            if (!response.data?.success || !response.data?.code) {
                throw new Error(`YYB 未返回 code: ${responseText(response.data)}`);
            }
            return response.data.code;
        }

        let response;
        try {
            response = await postJson(
                `${serverUrl}/wx/code`,
                { appid: MINI_APP_ID, openid: this.accountKey },
                { auth: process.env.wx_auth || "" },
                30000,
            );
        } catch (error) {
            throw new Error(`wx_server 获取 code 失败: ${error.message || error}`);
        }

        if (response.status < 200 || response.status >= 300) {
            throw new Error(`wx_server HTTP ${response.status}: ${responseText(response.data)}`);
        }
        const code = response.data?.code || response.data?.data?.code;
        if (!code) throw new Error(`wx_server 未返回 code: ${responseText(response.data)}`);
        return code;
    }

    async loginByWxCode() {
        this.tokenId = "";
        this.openid = "";
        this.companyId = process.env.HSH_COMPANY_ID || "";
        this.loginCompanyId = "";
        this.memberId = "";
        this.phone = "";

        const code = await this.getLoginCode();
        const wxSession = await this.request(API.wxSession, {
            authorizationCode: code,
            wxSn: MINI_APP_ID,
            appAuthCode: code,
            groupId: GROUP_ID,
        }, { auth: false, companyId: "" });

        const sessionData = wxSession.data || {};
        if (!sessionData.openid || !sessionData.encryptedSessionKey) {
            throw new Error(`code 换会话参数失败: ${responseText(wxSession)}`);
        }

        this.openid = sessionData.openid;
        this.memberId = sessionData.memberId || "";
        this.phone = sessionData.phone || "";

        const login = await this.request(API.login, {
            memberAuthorization: {
                encryptedSessionKey: sessionData.encryptedSessionKey,
                openId: this.openid,
            },
            clientType: `microsoft-${MINI_APP_ID}`,
            loginType: "mealMall",
            openId: this.openid,
            wxSn: MINI_APP_ID,
            groupId: GROUP_ID,
        }, { auth: false, companyId: "" });

        const loginData = login.data || {};
        if (!loginData.tokenId) throw new Error(`登录未返回 tokenId: ${responseText(login)}`);
        this.tokenId = loginData.tokenId;
        this.loginCompanyId = loginData.companyId || "";
        this.memberId = loginData.fid || this.memberId;
        this.companyId = process.env.HSH_COMPANY_ID || this.loginCompanyId || "";

        await this.refreshCompanyId();
        this.prefix(`登录成功${this.phone ? `，手机尾号 ${this.phone.slice(-4)}` : ""}`);
    }

    async refreshCompanyId() {
        try {
            const result = await this.request(API.member, this.commonBody(), { companyId: "" });
            const bindCompanyId = result.data?.bindCompanyId;
            if (bindCompanyId) this.companyId = process.env.HSH_COMPANY_ID || bindCompanyId;
            this.memberId = result.data?.memberId || this.memberId;
            this.phone = result.data?.phone || this.phone;
        } catch (error) {
            if (isAuthError(error)) throw error;
            this.prefix(`门店信息刷新失败，继续使用已有 company_id: ${error.message || error}`);
        }
    }

    async getSignList() {
        return await this.request(API.signList, this.commonBody());
    }

    isSignedToday(signInfo) {
        const data = signInfo?.data || {};
        const today = Array.isArray(data.list) ? data.list.find((item) => Number(item.isToday) === 1) : null;
        return Number(data.todaySignined) === 1 || Number(today?.isSignin) === 1;
    }

    async doSign(signInfo) {
        const beforePoint = Number(signInfo?.data?.point);
        if (this.isSignedToday(signInfo)) {
            this.prefix(`今日已签到，当前积分 ${Number.isFinite(beforePoint) ? beforePoint : "未知"}`);
            this.saveSession({ lastVerifiedAt: new Date().toISOString() });
            return true;
        }

        const result = await this.request(API.sign, this.commonBody(), { allowAnyCode: true });
        if (!isBusinessSuccess(result)) {
            const message = result?.msg || result?.message || responseText(result);
            if (/已签到|重复签到|今日已签/i.test(message)) {
                this.prefix("今日已签到");
                this.saveSession({ lastVerifiedAt: new Date().toISOString() });
                return true;
            }
            const error = makeRequestError(message, 200, result);
            throw error;
        }

        const reward = result.data?.giftSource;
        let afterInfo = null;
        try {
            afterInfo = await this.getSignList();
        } catch (error) {
            this.prefix(`签到请求成功，但复查失败: ${error.message || error}`);
        }

        const afterPoint = Number(afterInfo?.data?.point);
        const pointText = Number.isFinite(afterPoint) ? `，当前积分 ${afterPoint}` : "";
        const verifiedIncrease = Number.isFinite(beforePoint) && Number.isFinite(afterPoint) && afterPoint > beforePoint
            ? afterPoint - beforePoint
            : NaN;
        const rewardValue = Number(reward);
        const increase = Number.isFinite(verifiedIncrease) ? verifiedIncrease : rewardValue;
        this.prefix(`签到成功，获得 ${Number.isFinite(increase) ? increase : reward || "未知"} 积分${pointText}`);
        this.saveSession({ lastSignAt: new Date().toISOString(), lastVerifiedAt: new Date().toISOString() });
        return true;
    }

    async run() {
        const cached = this.getCachedSession();
        let signInfo = null;

        if (cached?.tokenId && (cached.openid || cached.openId)) {
            this.applySession(cached);
            this.usedCache = true;
            try {
                if (!this.companyId && !process.env.HSH_COMPANY_ID) {
                    await this.refreshCompanyId();
                }
                signInfo = await this.getSignList();
                this.prefix("缓存会话可用，无需重新获取 code");
            } catch (error) {
                if (!isAuthError(error)) {
                    this.prefix(`缓存校验遇到非认证错误，已保留缓存: ${error.message || error}`);
                    return false;
                }
                this.prefix("缓存会话已失效，尝试通过微信 code 重新登录");
                this.tokenId = "";
                signInfo = null;
            }
        }

        if (!signInfo) {
            try {
                await this.loginByWxCode();
                signInfo = await this.getSignList();
                const saved = this.saveSession({
                    loginAt: new Date().toISOString(),
                    lastVerifiedAt: new Date().toISOString(),
                });
                this.prefix(saved ? "新会话已写入缓存" : "新会话验证成功，但缓存写入失败");
            } catch (error) {
                if (cached) {
                    // 新登录失败时不删除原缓存，避免 code 服务或业务网络抖动造成不可恢复。
                    this.applySession(cached);
                    this.prefix(`获取 code/登录失败，原缓存已保留: ${error.message || error}`);
                } else {
                    this.prefix(`获取 code/登录失败，且无可用缓存: ${error.message || error}`);
                }
                return false;
            }
        }

        try {
            return await this.doSign(signInfo);
        } catch (error) {
            this.prefix(`签到失败: ${error.message || error}`);
            if (isAuthError(error)) {
                this.removeCachedSession();
                this.prefix("检测到明确的登录失效，已清理该账号缓存");
            }
            return false;
        }
    }
}

async function main() {
    const accounts = parseAccounts();
    if (!accounts.length) {
        log(`未找到环境变量 ${ENV_NAME}`);
        process.exitCode = 1;
        return;
    }

    log(`皇上皇会员商城签到开始，共 ${accounts.length} 个账号`);
    let failed = 0;
    for (let index = 0; index < accounts.length; index += 1) {
        if (!(await new AccountTask(accounts[index], index + 1).run())) failed += 1;
    }
    log(`皇上皇会员商城签到结束，成功 ${accounts.length - failed} 个，失败 ${failed} 个`);
    if (failed) process.exitCode = 1;
}

main().catch((error) => {
    log(`脚本异常: ${error.stack || error.message || error}`);
    process.exitCode = 1;
});
