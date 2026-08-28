"""finance-data 业务底座客户端（P1：客户档案；P2 扩展业务工具）。"""
from __future__ import annotations

import httpx

from app.config import settings


class FinanceDataError(Exception):
    """finance-data 业务错误（code 非 0）。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class CustomerProfileError(FinanceDataError):
    """客户档案不可用（不存在/状态异常）。"""


async def fetch_customer_profile(customer_no: str, request_id: str = "") -> dict:
    """拉取客户档案；业务失败抛 FinanceDataError。"""
    url = f"{settings.finance_base_url.rstrip('/')}/api/v1/customers/{customer_no}"
    headers = {
        "Authorization": f"Bearer {customer_no}",
        "X-Channel-Code": settings.finance_channel_code,
        "X-Request-Id": request_id,
        "X-Operator-No": settings.finance_operator_no,
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, headers=headers)
    body = resp.json()
    if body.get("code") != 0:
        raise CustomerProfileError(code=body.get("code", -1), message=body.get("message", "customer unavailable"))
    data = body.get("data") or {}
    profile = data.get("customer_profile") or {}
    return {
        "customer_no": customer_no,
        "customer_name": profile.get("customer_name"),
        "customer_status": data.get("customer_status"),
        "risk_level": (data.get("risk_level") or {}).get("risk_level_code"),
    }


async def _get_json(path: str, customer_no: str, request_id: str = "") -> dict:
    """GET finance-data 接口并解析统一响应。"""
    url = f"{settings.finance_base_url.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {customer_no}",
        "X-Channel-Code": settings.finance_channel_code,
        "X-Request-Id": request_id,
        "X-Operator-No": settings.finance_operator_no,
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, headers=headers)
    body = resp.json()
    if body.get("code") != 0:
        raise FinanceDataError(code=body.get("code", -1), message=body.get("message", "finance-data error"))
    return body.get("data") or {}


_LOAN_CATEGORY = {
    "LOAN_CASH": "现金/消费贷",
    "LOAN_CONSUMER": "消费贷款",
    "LOAN_BUSINESS": "经营贷款",
    "LOAN_MORTGAGE": "住房贷款",
    "LOAN_GUARANTEE": "担保贷款",
}


def _loan_category(code: str) -> str:
    for prefix, label in _LOAN_CATEGORY.items():
        if code.startswith(prefix):
            return label
    return "贷款产品"



async def search_products(query: str, customer_no: str, request_id: str = "") -> str:
    """按意图在理财/贷款产品目录中匹配，返回实时产品信息。"""
    is_wealth = any(t in query for t in ("理财", "基金", "存款", "现金", "稳健", "固收"))
    is_loan = any(t in query for t in ("贷款", "消费贷", "经营贷", "房贷", "住房"))
    lines: list[str] = []

    if is_wealth:
        try:
            data = await _get_json("/api/v1/wealth/products", customer_no, request_id)
            wealth = []
            for it in (data.get("list") or []):
                name = it.get("product_name") or ""
                risk = it.get("risk_level") or ""
                if not name:
                    continue
                if "现金" in query and "现金" not in name:
                    continue
                if "稳健" in query and risk != "P2":
                    continue
                rate = float(it.get("expected_yield_rate") or 0) * 100
                wealth.append(f"理财：{name}（风险等级{risk}，预期年化约 {rate:.2f}%）")
            lines.extend(wealth[:5])
        except Exception:
            pass

    if is_loan:
        try:
            data = await _get_json("/api/v1/loan/products", customer_no, request_id)
            loan = []
            for it in (data.get("list") or []):
                code = it.get("product_code") or ""
                rr = it.get("rate_range") or {}
                tr = it.get("term_range") or {}
                rmin = float(rr.get("min") or 0) * 100
                rmax = float(rr.get("max") or 0) * 100
                if "消费" in query and "CONSUMER" not in code and "CASH" not in code:
                    continue
                if "经营" in query and "BUSINESS" not in code:
                    continue
                if ("房贷" in query or "住房" in query) and "MORTGAGE" not in code:
                    continue
                label = _loan_category(code)
                loan.append(f"贷款：{label}（{code}，年化 {rmin:.2f}%-{rmax:.2f}%，期限 {tr.get('min','?')}-{tr.get('max','?')} 个月）")
            lines.extend(loan[:5])
        except Exception:
            pass

    return "\n".join(lines)



async def _post_json(path: str, body: dict, customer_no: str, request_id: str = "") -> dict:
    """POST finance-data 接口并解析统一响应（写接口需携带 request_no 幂等）。"""
    url = f"{settings.finance_base_url.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {customer_no}",
        "X-Channel-Code": settings.finance_channel_code,
        "X-Request-Id": request_id,
        "X-Operator-No": settings.finance_operator_no,
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(url, json=body, headers=headers)
    data = resp.json()
    if data.get("code") != 0:
        raise FinanceDataError(code=data.get("code", -1), message=data.get("message", "finance-data error"))
    return data.get("data") or {}


async def get_account(account_no: str | None, customer_no: str, request_id: str = "") -> dict | None:
    try:
        return await _get_json(f"/api/v1/accounts/{account_no}", customer_no, request_id)
    except FinanceDataError:
        return None


async def get_transactions(account_no: str | None, customer_no: str, page_size: int = 5, request_id: str = "") -> list:
    try:
        data = await _get_json(
            f"/api/v1/accounts/{account_no}/transactions?page_size={page_size}", customer_no, request_id
        )
        return data.get("list") or []
    except FinanceDataError:
        return []


async def get_credit_limit(customer_no: str, request_id: str = "") -> dict | None:
    """返回首个可用授信额度（贷款申请前置依赖）。"""
    try:
        data = await _get_json(f"/api/v1/customers/{customer_no}/credit-limits", customer_no, request_id)
        usable = [
            x for x in (data.get("list") or [])
            if float(x.get("available_limit_amount") or 0) > 0
        ]
        return usable[0] if usable else None
    except FinanceDataError:
        return None


async def submit_loan_application(body: dict, customer_no: str, request_id: str = "") -> dict:
    return await _post_json("/api/v1/loan/applications", body, customer_no, request_id)


async def create_support_ticket(body: dict, customer_no: str, request_id: str = "") -> dict:
    return await _post_json("/api/v1/support/tickets", body, customer_no, request_id)

