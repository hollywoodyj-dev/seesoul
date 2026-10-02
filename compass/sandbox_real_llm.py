#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SeeSoul Compass v2 · Real LLM Adapter — sandbox_real_llm.py (REV-B)
====================================================================
Founder Code Review (2026-10-01 23:58) · RETURN FOR HARDENING → REV-B
  单 provider / 单 model / 单 controlled configuration · 全显式配置 · 可复现。

REV-B 相对前版的落实（逐条对应 Founder 要求）：
  A. provider 选择显式：只读 LLM_PROVIDER，不扫描其他 provider 的 key。
  B. model 显式：LLM_MODEL=os.environ.get("LLM_MODEL")，缺失 -> MODEL_NOT_CONFIGURED，删除 runtime default model。
  C. actual API call 使用 cfg.model（DECLARED MODEL = EXECUTED MODEL）。
  D. provider-specific endpoint：ARK_BASE_URL / DEEPSEEK_BASE_URL / openai 官方端点。
  E. key 日志 = SET / NOT_SET only（data minimisation）。
  F. explicit configuration failure states：
       PROVIDER_NOT_CONFIGURED / INVALID_PROVIDER_CONFIG / CREDENTIAL_NOT_CONFIGURED /
       PROVIDER_CONFIG_INCOMPLETE / MODEL_NOT_CONFIGURED
  G. preserve EMPTY / INVALID_JSON（不被 normalize_error 降成 OTHER）。
  H. output schema validation：json.loads 只代表 VALID JSON；
       缺字段 / 类型错 / 额外禁止字段 -> OUTPUT_SCHEMA_INVALID，不直接进 E3。

CREDENTIAL 红线（不可协商）：
  - 代码只允许 os.environ.get(...)  禁止 api_key = "sk-..."
  - key 绝不写进 *任何* 文件 / SECRET.md / 普通日志 / test payload / report
  - provider / model / endpoint 必须显式配置；PROVIDER SELECTION MUST BE EXPLICIT
  - 无完整配置 => fail closed：NO CREDENTIAL => NO REAL LLM CALL

本文件（Credential 注入前）只做 adapter / 显式配置读取 / 请求构造 / 结构化
解析 / 输出 schema 校验 / timeout / 错误处理 / 最小化日志 / fail-closed。
不运行真实 8-case inference。

边界：只用 SYNTHETIC / CONTROLLED TEST DATA；不发送 production 数据。
"""

from __future__ import annotations
import os, json, logging
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("compass.real_llm")
logger.setLevel(logging.INFO)


def _no_value(v: Optional[str]) -> bool:
    return v is None or str(v).strip() == ""


def _set_log(v: Optional[str]) -> str:
    """data minimisation 日志：只记录 SET / NOT_SET，不记录任何 secret metadata（含长度 / 前缀 / 后缀）。"""
    return "SET" if not _no_value(v) else "NOT_SET"


# ---------------------------------------------------------------- #
# 1 · 显式 provider / model / endpoint 配置加载（无隐含优先级 / 自动切换）
# ---------------------------------------------------------------- #
# provider -> { key_env, base_url_env }   base_url_env=None 表示使用该 provider 官方端点
PROVIDER_META = {
    "ark":      {"key_env": "ARK_API_KEY",      "base_url_env": "ARK_BASE_URL",      },
    "deepseek": {"key_env": "DEEPSEEK_API_KEY", "base_url_env": "DEEPSEEK_BASE_URL", },
    "openai":   {"key_env": "OPENAI_API_KEY",   "base_url_env": None,                 },  # openai 官方端点
}


@dataclass
class ProviderConfig:
    status: str
    # 显式配置失败状态：PROVIDER_NOT_CONFIGURED / INVALID_PROVIDER_CONFIG /
    #   CREDENTIAL_NOT_CONFIGURED / PROVIDER_CONFIG_INCOMPLETE / MODEL_NOT_CONFIGURED
    # 成功状态：CONFIGURED
    provider: Optional[str]
    model: Optional[str]
    base_url: Optional[str]
    api_key: Optional[str]               # 运行时持有，仅内存，不得序列化进任何文件 / 日志 / 报告
    configured: bool = False


def load_explicit_config() -> ProviderConfig:
    """
    显式配置加载（CONFIGURATION DETECTION GATE — 不发 API request）。
    只读取：LLM_PROVIDER / LLM_MODEL / provider-specific endpoint & credential。
    不扫描其他 provider 的 key，不做自动 failover / 自动切换。
    """
    provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if _no_value(provider):
        logger.info("LLM_PROVIDER=NOT_SET -> PROVIDER_NOT_CONFIGURED")
        return ProviderConfig("PROVIDER_NOT_CONFIGURED", None, None, None, None, False)
    if provider not in PROVIDER_META:
        logger.info("LLM_PROVIDER=%s unsupported -> INVALID_PROVIDER_CONFIG", provider)
        return ProviderConfig("INVALID_PROVIDER_CONFIG", provider, None, None, None, False)

    meta = PROVIDER_META[provider]
    # 只读该 provider 对应的 credential；其他 provider 的 key 一律不读、不检查。
    key = os.environ.get(meta["key_env"], "")
    if _no_value(key):
        logger.info("provider=%s credential=%s -> CREDENTIAL_NOT_CONFIGURED", provider, _set_log(key))
        return ProviderConfig("CREDENTIAL_NOT_CONFIGURED", provider, None, None, None, False)

    model = (os.environ.get("LLM_MODEL") or "").strip()
    if _no_value(model):
        logger.info("provider=%s credential=SET model=%s -> MODEL_NOT_CONFIGURED", provider, _set_log(model))
        return ProviderConfig("MODEL_NOT_CONFIGURED", provider, None, None, None, False)

    base_url = os.environ.get(meta["base_url_env"], "").strip() if meta["base_url_env"] else None
    if meta["base_url_env"] and _no_value(base_url):
        logger.info("provider=%s credential=SET model=SET endpoint=%s -> PROVIDER_CONFIG_INCOMPLETE",
                    provider, _set_log(base_url))
        return ProviderConfig("PROVIDER_CONFIG_INCOMPLETE", provider, model, None, None, False)

    logger.info(
        "CONFIGURED provider=%s credential=%s model=%s endpoint=%s",
        provider, _set_log(key), _set_log(model), _set_log(base_url or "(official)")
    )
    return ProviderConfig("CONFIGURED", provider, model, base_url, key, True)


# ---------------------------------------------------------------- #
# 2 · Request construction
# ---------------------------------------------------------------- #
def build_request(prompt_text: str, model: str, temperature: float = 0.4, max_tokens: int = 1000) -> dict:
    return {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "You are a reflection assistant bound by a strict governance contract. Follow the prompt exactly. Respond only in the requested structured JSON."},
            {"role": "user", "content": prompt_text},
        ],
    }


# ---------------------------------------------------------------- #
# 3 · Structured response parsing（只判 VALID JSON；schema 校验在下一步）
# ---------------------------------------------------------------- #
def parse_structured_response(content: str) -> Dict[str, Any]:
    """
    返回 VALID JSON dict，或抛 ValueError：
      MODEL_RESPONSE_EMPTY / INVALID_JSON
    PARSE RECOVERY ≠ SCHEMA VALIDATION：此处不做 schema 语义判断。
    """
    if not content or not str(content).strip():
        raise ValueError("MODEL_RESPONSE_EMPTY")
    text = str(content).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                raise ValueError("INVALID_JSON")
        else:
            raise ValueError("INVALID_JSON")
    if not isinstance(obj, dict):
        raise ValueError("INVALID_JSON")
    return obj


# ---------------------------------------------------------------- #
# 3b · Output schema validation（field-specific types + allowed modes）
# PARSE ≠ SCHEMA；json.loads 成功 ≠ VALID COMPASS OUTPUT
# ---------------------------------------------------------------- #
ALLOWED_MODES = {"R0", "R1", "R2", "R3"}
REQUIRED_FIELDS = ["reflection_mode", "mirror"]
# 额外禁止字段：Reflection LLM 不得输出任何商业字段（§6.1 / §11：CTA 由 Router 决定）
FORBIDDEN_FIELDS = ["recommended_product", "best_service", "upsell_priority", "purchase_likelihood", "distress_value"]


def validate_output_schema(obj: Dict[str, Any]) -> None:
    """
    严格类型校验（COMMENTED SCHEMA MUST EQUAL ENFORCED SCHEMA）：
      reflection_mode 必须为 str，且 ∈ {R0,R1,R2,R3}
      mirror          必须为 dict
    否则 ValueError("OUTPUT_SCHEMA_INVALID") — 进入 E3 Audit 前的 blocking state。
    """
    for f in REQUIRED_FIELDS:
        if f not in obj:
            raise ValueError("OUTPUT_SCHEMA_INVALID")   # 缺字段
    # field-specific 类型：不用 permissive (str, dict)
    rm = obj.get("reflection_mode")
    if not isinstance(rm, str):
        raise ValueError("OUTPUT_SCHEMA_INVALID")       # reflection_mode 必须 str
    if rm not in ALLOWED_MODES:
        raise ValueError("OUTPUT_SCHEMA_INVALID")       # mode 必须 ∈ {R0..R3}
    if not isinstance(obj.get("mirror"), dict):
        raise ValueError("OUTPUT_SCHEMA_INVALID")       # mirror 必须 dict
    for f in FORBIDDEN_FIELDS:
        if f in obj:
            raise ValueError("OUTPUT_SCHEMA_INVALID")   # 额外禁止字段


# ---------------------------------------------------------------- #
# 4 · Fail-closed 行为
# ---------------------------------------------------------------- #
@dataclass
class LLMResult:
    ok: bool
    payload: Optional[dict] = None
    status: str = "OK"
    error: str = ""
    provider: str = ""


def fail_closed(status: str, error: str) -> LLMResult:
    return LLMResult(ok=False, payload=None, status=status, error=error, provider="(none)")


# ---------------------------------------------------------------- #
# 5 · 错误归一（保留 EMPTY / INVALID_JSON / OUTPUT_SCHEMA_INVALID；不外泄 key/content）
# ---------------------------------------------------------------- #
# 先判断强类型 ValueError 状态（由 parse / schema 主动抛出），再归一 infra 错误。
_PARSE_STATUS = {
    "MODEL_RESPONSE_EMPTY": "EMPTY",
    "INVALID_JSON": "INVALID_JSON",
    "OUTPUT_SCHEMA_INVALID": "OUTPUT_SCHEMA_INVALID",
}
_ERR_STATUS = {
    "authentication": "AUTH_FAILURE",
    "invalid_api_key": "AUTH_FAILURE",
    "unauthorized": "AUTH_FAILURE",
    "rate_limit": "RATE_LIMIT",
    "timeout": "TIMEOUT",
    "insufficient_quota": "RATE_LIMIT",
}


def normalize_error(exc: BaseException) -> LLMResult:
    msg = str(exc)
    # 保留显式 parse / schema 状态（FAILURE CLASSIFICATION MUST SURVIVE THE ADAPTER）
    if type(exc) is ValueError and msg in _PARSE_STATUS:
        return LLMResult(ok=False, status=_PARSE_STATUS[msg], error=f"output error: {msg}")
    low = msg.lower()
    for frag, status in _ERR_STATUS.items():
        if frag in low:
            return LLMResult(ok=False, status=status, error=f"infra error: {status}")
    return LLMResult(ok=False, status="OTHER", error="infra error: OTHER")


# ---------------------------------------------------------------- #
# 6 · LLM call（一次受控调用 + timeout + parse + schema validate）
# ---------------------------------------------------------------- #
def call_llm(cfg: ProviderConfig, prompt_text: str, timeout: float = 60.0,
             temperature: float = 0.4, max_tokens: int = 1000,
             client=None) -> LLMResult:
    """
    真实模型调用。model = cfg.model（DECLARED = EXECUTED，绝不使用默认模型）。
    默认直接实例化 openai.OpenAI；也可传入已构造的 client（供 connectivity/unit test 注入，
    与 production 走同一执行骨架 —— DECLARED CAPABILITY MATCHES EXECUTED CAPABILITY）。
    """
    if not cfg.configured or _no_value(cfg.api_key):
        logger.warning("call_llm: fail-closed (no credential)")
        return fail_closed("NOT_CONFIGURED", "explicit provider/model/credential not fully configured; REAL_LLM_EXECUTION=BLOCKED")
    try:
        if client is None:
            import openai
            kwargs = {"api_key": cfg.api_key, "timeout": timeout}
            if cfg.base_url:
                kwargs["base_url"] = cfg.base_url
            client = openai.OpenAI(**kwargs)
        request = {
            "model": cfg.model,            # DECLARED MODEL = EXECUTED MODEL；绝不使用默认模型
            "messages": build_request(prompt_text, cfg.model)["messages"],
        }
        model_name = (cfg.model or "").lower()
        # gpt-5.x rejects max_tokens and a non-default temperature.
        if model_name.startswith("gpt-5") or model_name.startswith(("o1", "o3", "o4")):
            request["max_completion_tokens"] = max_tokens
            request["reasoning_effort"] = "none"
        else:
            request["temperature"] = temperature
            request["max_tokens"] = max_tokens
        resp = client.chat.completions.create(**request)
        content = resp.choices[0].message.content
        finish = getattr(resp.choices[0], "finish_reason", "")
        logger.info("llm finish=%s content=%s", finish, _set_log(content))
        obj = parse_structured_response(content)   # 抛 EMPTY / INVALID_JSON
        validate_output_schema(obj)                # 抛 OUTPUT_SCHEMA_INVALID
        return LLMResult(ok=True, payload=obj, status="OK", provider=cfg.provider)
    except Exception as exc:
        lr = normalize_error(exc)
        lr.provider = cfg.provider
        return lr


# ---------------------------------------------------------------- #
# 7 · Self-check（REV-B acceptance）
# ---------------------------------------------------------------- #
def _self_check() -> list:
    """返回 (label, ok, detail) 列表；不打印任何 secret 值。"""
    results = []

    def run(label, fn):
        try:
            ok, detail = fn()
            results.append((label, ok, detail))
        except Exception as e:
            results.append((label, False, f"EXC:{e}"))

    def clear(**vals):
        for k in list(os.environ.keys()):
            if k.startswith(("LLM_", "ARK_", "DEEPSEEK_", "OPENAI_")) and k != "OPENAI_BASE_URL":
                os.environ.pop(k, None)
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop("LLM_MODEL", None)
        for k, v in vals.items():
            os.environ[k] = v

    # A. no LLM_PROVIDER -> BLOCKED
    def case_a():
        clear()
        s = load_explicit_config().status
        return s == "PROVIDER_NOT_CONFIGURED", s
    run("no LLM_PROVIDER -> PROVIDER_NOT_CONFIGURED", case_a)

    # B. unsupported LLM_PROVIDER -> BLOCKED
    def case_b():
        clear()
        os.environ["LLM_PROVIDER"] = "anthropic"
        s = load_explicit_config().status
        return s == "INVALID_PROVIDER_CONFIG", s
    run("unsupported LLM_PROVIDER -> INVALID_PROVIDER_CONFIG", case_b)

    # C. provider + no credential -> BLOCKED
    def case_c():
        clear()
        os.environ["LLM_PROVIDER"] = "openai"
        s = load_explicit_config().status
        return s == "CREDENTIAL_NOT_CONFIGURED", s
    run("provider set + no credential -> CREDENTIAL_NOT_CONFIGURED", case_c)

    # D. provider + credential + no model -> BLOCKED
    def case_d():
        clear()
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        s = load_explicit_config().status
        return s == "MODEL_NOT_CONFIGURED", s
    run("provider+credential, no LLM_MODEL -> MODEL_NOT_CONFIGURED", case_d)

    # E. Ark + no endpoint -> BLOCKED
    def case_e():
        clear()
        os.environ["LLM_PROVIDER"] = "ark"
        os.environ["ARK_API_KEY"] = "sk-test"
        os.environ["LLM_MODEL"] = "m"
        s = load_explicit_config().status
        return s == "PROVIDER_CONFIG_INCOMPLETE", s
    run("Ark + no required endpoint -> PROVIDER_CONFIG_INCOMPLETE", case_e)

    # F. valid explicit config -> CONFIGURED
    def case_f():
        clear()
        os.environ["LLM_PROVIDER"] = "ark"
        os.environ["ARK_API_KEY"] = "sk-test"
        os.environ["LLM_MODEL"] = "doubao-explicit"
        os.environ["ARK_BASE_URL"] = "https://ark.cn-beijing.volces.com/api/v3"
        c = load_explicit_config()
        return (c.status == "CONFIGURED" and c.model == "doubao-explicit"), f"{c.status}, model={c.model}"
    run("valid explicit config -> CONFIGURED (model preserved)", case_f)

    # G. invalid JSON -> INVALID_JSON
    def case_g():
        try:
            parse_structured_response("not json {{{")
            return False, "no raise"
        except ValueError as e:
            return str(e) == "INVALID_JSON", str(e)
    run("invalid JSON -> INVALID_JSON", case_g)

    # H. empty response -> EMPTY (survives normalize_error)
    def case_h():
        try:
            parse_structured_response("")
        except ValueError as e:
            lr = normalize_error(e)
            return lr.status == "EMPTY", lr.status
        return False, "no raise"
    run("empty response -> EMPTY (survives adapter)", case_h)

    # I. invalid JSON survives normalize_error (not downgraded to OTHER)
    def case_i():
        try:
            parse_structured_response("x")
        except ValueError as e:
            lr = normalize_error(e)
            return lr.status == "INVALID_JSON", lr.status
        return False, "no raise"
    run("invalid JSON survives normalize_error -> INVALID_JSON", case_i)

    # J. valid JSON / invalid Compass schema -> OUTPUT_SCHEMA_INVALID
    def case_j():
        obj = {"model": "gpt"}   # 缺 reflection_mode / mirror
        try:
            validate_output_schema(obj)
            return False, "no raise"
        except ValueError as e:
            lr = normalize_error(e)
            return lr.status == "OUTPUT_SCHEMA_INVALID", lr.status
    run("valid JSON / invalid schema -> OUTPUT_SCHEMA_INVALID", case_j)

    # K. forbidden field -> OUTPUT_SCHEMA_INVALID
    def case_k():
        obj = {"reflection_mode": "R2", "mirror": {"text": "x"}, "recommended_product": "y"}
        try:
            validate_output_schema(obj)
            return False, "no raise"
        except ValueError:
            return True, "OUTPUT_SCHEMA_INVALID"
    run("forbidden commercial field -> OUTPUT_SCHEMA_INVALID", case_k)

    # N. reflection_mode=dict (type inversion) -> OUTPUT_SCHEMA_INVALID
    def case_n():
        obj = {"reflection_mode": {}, "mirror": {"text": "x"}}
        try:
            validate_output_schema(obj)
            return False, "no raise (mode accepted as dict)"
        except ValueError:
            return True, "OUTPUT_SCHEMA_INVALID"
    run("reflection_mode dict -> OUTPUT_SCHEMA_INVALID", case_n)

    # O. mirror=str (type inversion) -> OUTPUT_SCHEMA_INVALID
    def case_o():
        obj = {"reflection_mode": "R2", "mirror": "x"}
        try:
            validate_output_schema(obj)
            return False, "no raise (mirror accepted as str)"
        except ValueError:
            return True, "OUTPUT_SCHEMA_INVALID"
    run("mirror str -> OUTPUT_SCHEMA_INVALID", case_o)

    # P. invalid mode R7 -> OUTPUT_SCHEMA_INVALID
    def case_p():
        obj = {"reflection_mode": "R7", "mirror": {"text": "x"}}
        try:
            validate_output_schema(obj)
            return False, "no raise (R7 accepted)"
        except ValueError:
            return True, "OUTPUT_SCHEMA_INVALID"
    run("reflection_mode R7 -> OUTPUT_SCHEMA_INVALID", case_p)

    # Q. valid R2 output -> schema PASS
    def case_q():
        obj = {"reflection_mode": "R2", "mirror": {"text": "x"}, "bounded_reflection": {"text": "y"}}
        try:
            validate_output_schema(obj)
            return True, "schema PASS"
        except ValueError:
            return False, "unexpected OUTPUT_SCHEMA_INVALID"
    run("valid R2 output -> schema PASS", case_q)

    # L. 静态：无 runtime default model selection（只检查 runtime 函数体，不检查检查器自身）
    def case_l():
        import inspect, sys
        mod = sys.modules[__name__]
        # 只检查「会参与运行时请求」的函数，排除 _self_check 检查器自身避免自指
        runtime_src = ""
        for fn in ("load_explicit_config", "build_request", "call_llm"):
            runtime_src += inspect.getsource(getattr(mod, fn))
        banned = ["gpt-4o-mini", "deepseek" + "-chat", "doubao-seed-1.6" + "-250615"]
        return not any(b in runtime_src for b in banned), ("default model constant found" if any(b in runtime_src for b in banned) else "explicit-only")
    run("static: no runtime default model selection", case_l)

    # M. 无 secret 值进入日志 / report 载体（logger 走 _set_log）
    def case_m():
        import io
        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        logger.addHandler(h)
        clear()
        os.environ["LLM_PROVIDER"] = "ark"
        os.environ["ARK_API_KEY"] = "sk-supersecret-value"
        os.environ["LLM_MODEL"] = "m"
        os.environ["ARK_BASE_URL"] = "https://x"
        load_explicit_config()
        logger.removeHandler(h)
        out = buf.getvalue()
        leak = ("sk-supersecret" in out) or ("len=" in out)
        return (not leak), (repr(out) if not leak else "LEAK_DETECTED")
    run("logger: SET/NOT_SET only, no key value or length", case_m)

    return results


if __name__ == "__main__":
    print("== sandbox_real_llm.py REV-B acceptance self-check ==")
    allok = True
    for label, ok, detail in _self_check():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if not ok else ""))
        allok = allok and ok
    print("== OVERALL:", "PASS" if allok else "FAIL", "==")
    if allok:
        print("READY FOR SECURE SECRET INJECTION (CONFIGURATION DETECTION 前置)。")