import requests

from .supabase_client import get_client_or_raise


def _headers(key, prefer_return=False):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"
    return headers


def _request(method, endpoint, *, params=None, json_body=None, prefer_return=False):
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
    resp.raise_for_status()
    if resp.text:
        return resp.json()
    return []


def init_db():
    """Schema is managed in Supabase."""
    return True


def load_companies():
    companies_rows = _request(
        "GET",
        "companies",
        params={"select": "id,name", "order": "name.asc"},
    )

    inspections_rows = _request(
        "GET",
        "inspections",
        params={"select": "id,company_id,done_date,next_date,notes", "order": "id.desc"},
    )

    latest_by_company = {}
    for row in inspections_rows:
        cid = row.get("company_id")
        if cid is not None and cid not in latest_by_company:
            latest_by_company[cid] = row

    result = []
    for c in companies_rows:
        latest = latest_by_company.get(c.get("id"), {})
        result.append(
            {
                "id": c.get("id"),
                "name": c.get("name") or "",
                "done": latest.get("done_date"),
                "next": latest.get("next_date"),
                "notes": latest.get("notes"),
            }
        )

    return result


def add_company(name):
    rows = _request(
        "POST",
        "companies",
        json_body={"name": name},
        prefer_return=True,
    )
    row = rows[0] if rows else None
    if not row or "id" not in row:
        raise RuntimeError("Failed to create company in online database.")
    return row["id"]


def update_company(cid, name):
    _request(
        "PATCH",
        "companies",
        params={"id": f"eq.{cid}"},
        json_body={"name": name},
    )


def add_inspection(cid, done_s, next_s, notes):
    _request(
        "POST",
        "inspections",
        json_body={
            "company_id": cid,
            "done_date": done_s,
            "next_date": next_s,
            "notes": notes,
        },
    )


def load_inspection_history(cid):
    rows = _request(
        "GET",
        "inspections",
        params={
            "select": "done_date,next_date,notes,id",
            "company_id": f"eq.{cid}",
            "order": "done_date.desc,id.desc",
        },
    )

    return [
        {
            "done": r.get("done_date"),
            "next": r.get("next_date"),
            "notes": r.get("notes"),
        }
        for r in rows
    ]


def delete_company(cid):
    _request(
        "DELETE",
        "inspections",
        params={"company_id": f"eq.{cid}"},
    )
    _request(
        "DELETE",
        "companies",
        params={"id": f"eq.{cid}"},
    )
