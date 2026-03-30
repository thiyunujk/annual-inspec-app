from .supabase_client import get_client_or_raise


def init_db():
    """Online DB is managed in Supabase; no local init required."""
    return True


def load_companies():
    client = get_client_or_raise()

    companies_res = (
        client.table("companies")
        .select("id,name")
        .order("name")
        .execute()
    )
    companies_rows = companies_res.data or []

    inspections_res = (
        client.table("inspections")
        .select("id,company_id,done_date,next_date,notes")
        .order("id", desc=True)
        .execute()
    )
    inspections_rows = inspections_res.data or []

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
    client = get_client_or_raise()
    res = (
        client.table("companies")
        .insert({"name": name})
        .execute()
    )
    row = (res.data or [None])[0]
    if not row or "id" not in row:
        raise RuntimeError("Failed to create company in online database.")
    return row["id"]


def update_company(cid, name):
    client = get_client_or_raise()
    (
        client.table("companies")
        .update({"name": name})
        .eq("id", cid)
        .execute()
    )


def add_inspection(cid, done_s, next_s, notes):
    client = get_client_or_raise()
    (
        client.table("inspections")
        .insert(
            {
                "company_id": cid,
                "done_date": done_s,
                "next_date": next_s,
                "notes": notes,
            }
        )
        .execute()
    )


def load_inspection_history(cid):
    client = get_client_or_raise()
    res = (
        client.table("inspections")
        .select("done_date,next_date,notes,id")
        .eq("company_id", cid)
        .order("done_date", desc=True)
        .order("id", desc=True)
        .execute()
    )

    rows = res.data or []
    return [
        {
            "done": r.get("done_date"),
            "next": r.get("next_date"),
            "notes": r.get("notes"),
        }
        for r in rows
    ]


def delete_company(cid):
    client = get_client_or_raise()
    (
        client.table("inspections")
        .delete()
        .eq("company_id", cid)
        .execute()
    )
    (
        client.table("companies")
        .delete()
        .eq("id", cid)
        .execute()
    )
