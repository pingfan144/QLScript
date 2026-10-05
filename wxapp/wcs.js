const axios = require("axios");

// YYB 面板默认地址：
// wx_auth 填了 YYB 的 API Key（yyb_ 开头）但 wx_server_url 还是 smallcat 局域网地址时，
// 自动纠正到 YYB 公网地址，避免拿 API Key 去打 smallcat。
const YYB_DEFAULT_BASE = "https://yyb.fuckinghigh.eu.org";

class WeChatCodeServer {
    constructor(options) {
        this.serverUrl = options.url;
        this.appid = options.appid;
        this.auth = options.auth;

        // ── 后端自动识别 ──
        //   wx_auth 填 YYB 面板 API Key（yyb_ 开头）或 url 里带 yyb 字样 → 走 YYB 面板取码
        //   否则维持原 wx_server（smallcat）的 POST /wx/code
        // 两种后端对脚本透明：变量名不变（wx_server_url / wx_auth），只换值即可切换。
        const auth = String(this.auth || "");
        const url = String(this.serverUrl || "");
        this.yybMode = /^yyb_[0-9a-zA-Z]{8,}$/.test(auth) || /yyb/i.test(url);
        this.yybBase = /yyb/i.test(url) ? url.replace(/\/+$/, "") : YYB_DEFAULT_BASE;
        if (this.yybMode) {
            console.log(`wx取码后端: YYB面板 (${this.yybBase})`);
        }
    }

    getCode(openid) {
        if (this.yybMode) return this.yybGetCode(openid);
        console.log('等待获取code:');
        return new Promise((resolve, reject) => {
            axios.post(this.serverUrl + '/wx/code', { appid: this.appid, openid }, {
                headers: {
                    'auth': this.auth
                },
                timeout: 30 * 1000
            }).then(res => {
                console.log('获取code成功:');
                resolve(res);
            }).catch(err => {
                reject(err);
            });
        });
    }

    /* ────────── YYB 面板后端 ──────────
       GET /yyb/api/code?appid=<目标小程序appid>&openid=<面板账号openid>
       鉴权: X-API-Key 请求头（wx_auth 变量填 API Key）
       面板原始响应:
         成功 {"success":true,"account":"陈颖","appid":"wx...","code":"081...","msg":"成功"}
         失败 {"success":false,"msg":"未知 openid xxx"}
       这里包一层 wx_server 风格的信封，兼容全部既有脚本解析:
         成功 -> { data:{ status:true, code, account, appid, msg } }
         失败 -> { data:{ status:false, message, msg } }
       脚本侧 `data?.data?.code || data?.code` 与 `data.status === false` 两种写法均兼容。
       HTTP 异常（Key 无效/超时等）保持 reject，error.message 带面板原始 msg。 */
    async yybGetCode(openid) {
        const params = { appid: this.appid };
        if (openid) params.openid = openid;
        let res;
        try {
            res = await axios.get(this.yybBase + "/yyb/api/code", {
                params,
                headers: { "X-API-Key": this.auth },
                // 面板侧可能需要刷新账号 token，链路比 smallcat 长，放宽到 60s
                timeout: 60 * 1000,
            });
        } catch (err) {
            const srvMsg = err.response && err.response.data && (err.response.data.msg || err.response.data.message);
            if (srvMsg) {
                const e = new Error(`YYB取码失败: ${srvMsg}`);
                e.response = err.response;
                throw e;
            }
            throw err;
        }
        const d = res.data || {};
        if (d.success && d.code) {
            console.log(`获取code成功: 账号[${d.account || openid}] appid=${d.appid || this.appid}`);
            return {
                data: {
                    status: true,
                    code: d.code,
                    account: d.account || "",
                    appid: d.appid || this.appid,
                    msg: d.msg || "成功",
                },
            };
        }
        console.log(`获取code失败: ${d.msg || "未知错误"}`);
        return {
            data: {
                status: false,
                message: d.msg || "取码失败",
                msg: d.msg || "取码失败",
            },
        };
    }

    /* ── 取用户信息（等价 wx_server /wx/getuserinfo）──
       smallcat: POST /wx/getuserinfo -> {status, data:{code, data:"<userinfo json 串>"}}
       YYB: code 与 userinfo 分属两个接口，这里串起来拼成同构信封:
            GET /yyb/api/code                      -> {success, code}
            POST /yyb/api/invoke-cloud             -> {success, data:{data:"<userinfo json 串>"}}
                 raw_api_data = {"api_name":"webapi_getuserinfo","with_credentials":true}
       返回 { data:{ status, data:{ code, data } } }，与 wx_server 结构逐字段对齐。 */
    async getUserInfo(openid) {
        if (!this.yybMode) {
            const res = await axios.post(this.serverUrl + '/wx/getuserinfo', { appid: this.appid, openid }, {
                headers: { 'auth': this.auth },
                timeout: 45 * 1000,
            });
            return { data: res.data };
        }
        const codeRes = await this.yybGetCode(openid);
        const code = codeRes.data && codeRes.data.code;
        if (!code) return codeRes; // 失败信封直接透传（status:false）
        try {
            const res = await axios.post(this.yybBase + "/yyb/api/invoke-cloud", {
                appid: this.appid,
                openid: openid || undefined,
                raw_api_data: JSON.stringify({ api_name: "webapi_getuserinfo", with_credentials: true }),
            }, {
                headers: { "X-API-Key": this.auth },
                timeout: 60 * 1000,
            });
            const d = res.data || {};
            const info = d.data || {};
            if (d.success && (info.data !== undefined || info.encryptedData)) {
                // 把 invoke-cloud 的原始字段全部带上（code/data/encryptedData/iv/signature/cloud_id），
                // code 用 wx.login 的取码结果覆盖 —— 与 wx_server /wx/getuserinfo 的返回逐字段对齐
                return { data: { status: true, data: { ...info, code } } };
            }
            // 云函数没取到 userinfo（部分小程序未开云开发等）：降级返回 code + 空用户信息
            console.log(`YYB userinfo 缺失(${d.msg || "无数据"})，降级为仅 code`);
            return { data: { status: true, data: { code, data: "{}" } } };
        } catch (err) {
            // invoke-cloud 网络层失败同样降级：code 是登录刚需，userinfo 只是锦上添花
            const srvMsg = err.response && err.response.data && (err.response.data.msg || err.response.data.message);
            console.log(`YYB userinfo 调用失败(${srvMsg || err.message || err})，降级为仅 code`);
            return { data: { status: true, data: { code, data: "{}" } } };
        }
    }

    /* ── 取手机号授权 code（等价 wx_server /wx/getphonenumber）──
       smallcat: POST /wx/getphonenumber -> {status, code/data.code = 手机号授权 code}
       YYB: POST /yyb/api/get-phone-number {appid, openid}
            -> {success, data:{ wx_phone:{ data:"{\"code\":\"...\"}", mobile }, custom_phone_list:[...] }}
            提取 wx_phone.data JSON 里的 code 作为手机号授权 code */
    async getPhoneNumber(openid) {
        if (!this.yybMode) {
            const res = await axios.post(this.serverUrl + '/wx/getphonenumber', { appid: this.appid, openid }, {
                headers: { 'auth': this.auth },
                timeout: 45 * 1000,
            });
            return { data: res.data };
        }
        try {
            const res = await axios.post(this.yybBase + "/yyb/api/get-phone-number", {
                appid: this.appid,
                openid: openid || undefined,
            }, {
                headers: { "X-API-Key": this.auth },
                timeout: 60 * 1000,
            });
            const d = res.data || {};
            if (!d.success) {
                return { data: { status: false, message: d.msg || "获取手机号失败", msg: d.msg || "获取手机号失败" } };
            }
            const wxPhone = (d.data && d.data.wx_phone) || {};
            let phoneCode = "";
            try {
                phoneCode = (JSON.parse(wxPhone.data || "{}").code) || "";
            } catch (e) {}
            if (!phoneCode && Array.isArray(d.data && d.data.custom_phone_list) && d.data.custom_phone_list.length) {
                try {
                    phoneCode = (JSON.parse(d.data.custom_phone_list[0].data || "{}").code) || "";
                } catch (e) {}
            }
            if (!phoneCode) {
                return { data: { status: false, message: "YYB手机号响应里未找到授权code", msg: "YYB手机号响应里未找到授权code" } };
            }
            // 对齐 wx_server /wx/getphonenumber 的返回：code + raw(encryptedData/iv 等原始字段)
            // 海天等脚本会取 data.data.raw.encryptedData / data.data.raw.iv 做手机号解密登录
            return {
                data: {
                    status: true,
                    code: phoneCode,
                    phone: wxPhone.mobile || "",
                    encryptedData: wxPhone.encryptedData || "",
                    iv: wxPhone.iv || "",
                    raw: wxPhone,
                },
            };
        } catch (err) {
            const srvMsg = err.response && err.response.data && (err.response.data.msg || err.response.data.message);
            throw new Error(`YYB获取手机号失败: ${srvMsg || err.message || err}`);
        }
    }

    /* ── 刷新账号（等价 wx_server /wx/refresh，camel 等脚本取码失败后的补救）──
       YYB: POST /yyb/api/accounts/refresh {openid}，失败不抛错（与原脚本「刷新失败不阻断」语义一致） */
    async refreshAccount(openid) {
        if (!this.yybMode) {
            return axios.post(this.serverUrl + '/wx/refresh', { appid: this.appid, openid }, {
                headers: { 'auth': this.auth },
                timeout: 30 * 1000,
            });
        }
        try {
            return await axios.post(this.yybBase + "/yyb/api/accounts/refresh", openid ? { openid } : {}, {
                headers: { "X-API-Key": this.auth },
                timeout: 60 * 1000,
            });
        } catch (e) {
            return null; // 刷新失败不阻断
        }
    }

    cloudInit(openid) {
        console.log('等待云函数初始化:');
        return new Promise((resolve, reject) => {
            axios.post(this.serverUrl + '/wx/call/init', { appid: this.appid, openid }, {
                headers: {
                    'auth': this.auth
                },
                timeout: 30 * 1000
            }).then(res => {
                console.log('云函数初始化成功:');
                resolve(res);
            }).catch(err => {
                reject(err);
            });
        });
    }
    cloudCall(openid) {
        console.log('等待云函数调用:');
        return new Promise((resolve, reject) => {
            axios.post(this.serverUrl + '/wx/cloud/call', { appid: this.appid, openid }, {
                headers: {
                    'auth': this.auth
                },
                timeout: 30 * 1000
            }).then(res => {
                console.log('云函数调用成功:');
                resolve(res);
            }).catch(err => {
                reject(err);
            });
        });
    }
}
module.exports = WeChatCodeServer;
