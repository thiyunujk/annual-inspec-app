import logging
from typing import Any, Dict, Optional

import requests

from .supabase_client import get_client_or_raise

logger = logging.getLogger(__name__)


def _success(data: Any = None) -> Dict[str, Any]:
    return {"success": True, "data": data}


def _error(error: str, details: str = "", status_code: Optional[int] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"success": False, "error": error, "details": details}
    if status_code is not None:
        result["status_code"] = status_code
    return result


def _headers(key: str, prefer_return: bool = False) -> Dict[str, str]:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"
    return headers


def _extract_error_details(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return (
                payload.get("message")
                or payload.get("error_description")
                or payload.get("details")
                or payload.get("hint")
                or str(payload)
            )
        return str(payload)
    except Exception:
        return response.text[:300]


def _status_error(status_code: int, details: str) -> Dict[str, Any]:
    if status_code == 401:
        return _error("Unauthorized (401)", details, status_code)
    if status_code == 403:
        return _error("Forbidden (403)", details, status_code)
    if status_code == 404:
        return _error("Not Found (404)", details, status_code)
    if status_code >= 500:
        return _error(f"Server Error ({status_code})", details, status_code)
    return _error(f"Request Failed ({status_code})", details, status_code)


def _request(
    method: str,
    endpoint: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    prefer_return: bool = False,
) -> Dict[str, Any]:
    try:
        client = get_client_or_raise()
        base = client["url"] + "/rest/v1"
        url = f"{base}/{endpoint}"

        resp = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            headers=_headers(client["key"], prefer_return=prefer_return),
            timeout=20,
        )

        if resp.status_code >= 400:
            details = _extract_error_details(resp)
            logger.error("Supabase API error %s %s: %s", method, endpoint, details)
            return _status_error(resp.status_code, details)

        if not resp.text:
            return _success([])

        try:
            payload = resp.json()
        except Exception as exc:
            logger.exception("Invalid JSON response from Supabase for %s %s", method, endpoint)
            return _error("Invalid Response", str(exc))

        return _success(payload)

    except requests.Timeout as exc:
        logger.exception("Timeout calling Supabase %s %s", method, endpoint)
        return _error("Network error", f"Timeout: {exc}")
    except requests.ConnectionError as exc:
        logger.exception("Connection error calling Supabase %s %s", method, endpoint)
        return _error("Network error", f"Connection failed: {exc}")
    except requests.RequestException as exc:
        logger.exception("Request exception calling Supabase %s %s", method, endpoint)
        return _error("Network error", str(exc))
    except Exception as exc:
        logger.exception("Unexpected repository error for %s %s", method, endpoint)
        return _error("Repository error", str(exc))


def init_db() -> Dict[str, Any]:
    return _success(True)


def load_companies() -> Dict[str, Any]:
    companies_res = _request(
        "GET",
        "companies",
        params={"select": "id,name", "order": "name.asc"},
    )
    if not companies_res.get("success"):
        return companies_res

    inspections_res = _request(
        "GET",
        "inspections",
        params={"select": "id,company_id,done_date,next_date,notes", "order": "id.desc"},
    )
    if not inspections_res.get("success"):
        return inspections_res

    companies_rows = companies_res.get("data")
    inspections_rows = inspections_res.get("data")

    if not isinstance(companies_rows, list) or not isinstance(inspections_rows, list):
        logger.error("Invalid data shape from Supabase: companies=%s inspections=%s", type(companies_rows), type(inspections_rows))
        return _error("Invalid Response", "Expected list response from Supabase")

    latest_by_company = {}
    for row in inspections_rows:
        if not isinstance(row, dict):
            continue
        cid = row.get("company_id")
        if cid is not None and cid not in latest_by_company:
            latest_by_company[cid] = row

    result = []
    for company in companies_rows:
        if not isinstance(company, dict):
            continue
        latest = latest_by_company.get(company.get("id"), {})
        result.append(
            {
                "id": company.get("id"),
                "name": company.get("name") or "",
                "done": latest.get("done_date") if isinstance(latest, dict) else None,
                "next": latest.get("next_date") if isinstance(latest, dict) else None,
                "notes": latest.get("notes") if isinstance(latest, dict) else None,
            }
        )

    return _success(result)


def add_company(name: str) -> Dict[str, Any]:
    res = _request(
        "POST",
        "companies",
        json_body={"name": name},
        prefer_return=True,
    )
    if not res.get("success"):
        return res

    rows = res.get("data")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict) or "id" not in rows[0]:
        logger.error("Unexpected add_company response: %s", rows)
        return _error("Invalid Response", "Missing inserted company id")

    return _success(rows[0]["id"])


def update_company(cid: int, name: str) -> Dict[str, Any]:
    return _request(
        "PATCH",
        "companies",
        params={"id": f"eq.{cid}"},
        json_body={"name": name},
    )


def add_inspection(cid: int, done_s: str, next_s: str, notes: str) -> Dict[str, Any]:
    return _request(
        "POST",
        "inspections",
        json_body={
            "company_id": cid,
            "done_date": done_s,
            "next_date": next_s,
            "notes": notes,
        },
    )


def load_inspection_history(cid: int) -> Dict[str, Any]:
    res = _request(
        "GET",
        "inspections",
        params={
            "select": "done_date,next_date,notes,id",
            "company_id": f"eq.{cid}",
            "order": "done_date.desc,id.desc",
        },
    )
    if not res.get("success"):
        return res

    rows = res.get("data")
    if not isinstance(rows, list):
        logger.error("Unexpected inspection history response: %s", rows)
        return _error("Invalid Response", "Expected list for inspection history")

    history = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        history.append(
            {
                "done": row.get("done_date"),
                "next": row.get("next_date"),
                "notes": row.get("notes"),
            }
        )

    return _success(history)


def delete_company(cid: int) -> Dict[str, Any]:
    del_inspections = _request(
        "DELETE",
        "inspections",
        params={"company_id": f"eq.{cid}"},
    )
    if not del_inspections.get("success"):
        return del_inspections

    del_company = _request(
        "DELETE",
        "companies",
        params={"id": f"eq.{cid}"},
    )
    if not del_company.get("success"):
        return del_company

    return _success(True)


def test_connection() -> Dict[str, Any]:
    res = _request(
        "GET",
        "companies",
        params={"select": "id", "limit": 1},
    )
    if not res.get("success"):
        return res
    return _success(True)
