"""Integration tests for the /datasets and /datasets/{id}/rows endpoints."""
import io
import pytest


# ── Dataset CRUD ──────────────────────────────────────────────────────────────

async def test_list_datasets_empty(client):
    r = await client.get("/datasets")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_dataset(client):
    r = await client.post("/datasets", json={"name": "My DS", "description": "test"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "My DS"
    assert data["row_count"] == 0
    assert "id" in data
    assert "created_at" in data


async def test_list_datasets_after_create(client):
    await client.post("/datasets", json={"name": "DS1"})
    await client.post("/datasets", json={"name": "DS2"})
    r = await client.get("/datasets")
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert "DS1" in names
    assert "DS2" in names


async def test_get_dataset_by_id(client):
    create = await client.post("/datasets", json={"name": "Lookup DS"})
    ds_id = create.json()["id"]

    r = await client.get(f"/datasets/{ds_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Lookup DS"


async def test_get_dataset_not_found(client):
    r = await client.get("/datasets/9999")
    assert r.status_code == 404


async def test_delete_dataset(client):
    create = await client.post("/datasets", json={"name": "To Delete"})
    ds_id = create.json()["id"]

    r = await client.delete(f"/datasets/{ds_id}")
    assert r.status_code == 204

    r2 = await client.get(f"/datasets/{ds_id}")
    assert r2.status_code == 404


# ── Row upload (CSV) ──────────────────────────────────────────────────────────

async def test_upload_csv_rows(client):
    ds_id = (await client.post("/datasets", json={"name": "CSV DS"})).json()["id"]

    csv_content = (
        "input,expected_output,context,tags,difficulty\n"
        "What is AI?,Artificial intelligence,Some context,ml,easy\n"
        "What is ML?,Machine learning,,ml,medium\n"
    )
    r = await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 2


async def test_upload_csv_updates_row_count(client):
    ds_id = (await client.post("/datasets", json={"name": "Count DS"})).json()["id"]

    csv_content = "input,expected_output\nQ1,A1\nQ2,A2\nQ3,A3\n"
    await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    r = await client.get(f"/datasets/{ds_id}")
    assert r.json()["row_count"] == 3


async def test_upload_json_rows(client):
    ds_id = (await client.post("/datasets", json={"name": "JSON DS"})).json()["id"]

    import json
    rows = [
        {"input": "Q1", "expected_output": "A1", "tags": "factual"},
        {"input": "Q2", "expected_output": "A2"},
    ]
    r = await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.json", io.BytesIO(json.dumps(rows).encode()), "application/json")},
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 2


async def test_upload_to_nonexistent_dataset(client):
    csv_content = "input\nQ1\n"
    r = await client.post(
        "/datasets/9999/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert r.status_code == 404


# ── Row listing (pagination, tag filter) ──────────────────────────────────────

async def test_list_rows_paginated(client):
    ds_id = (await client.post("/datasets", json={"name": "Page DS"})).json()["id"]
    csv_lines = "input,expected_output\n" + "\n".join(f"Q{i},A{i}" for i in range(10))
    await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_lines.encode()), "text/csv")},
    )

    r = await client.get(f"/datasets/{ds_id}/rows?page=1&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 10
    assert len(body["items"]) == 5

    r2 = await client.get(f"/datasets/{ds_id}/rows?page=2&limit=5")
    assert len(r2.json()["items"]) == 5


async def test_list_rows_tag_filter(client):
    ds_id = (await client.post("/datasets", json={"name": "Tag DS"})).json()["id"]
    csv_content = (
        "input,expected_output,tags\n"
        "Q1,A1,factual\n"
        "Q2,A2,conceptual\n"
        "Q3,A3,factual\n"
    )
    await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    r = await client.get(f"/datasets/{ds_id}/rows?tags=factual")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert all("factual" in (item["tags"] or "") for item in body["items"])


async def test_delete_row(client):
    ds_id = (await client.post("/datasets", json={"name": "Del DS"})).json()["id"]
    csv_content = "input,expected_output\nToDelete,A\n"
    await client.post(
        f"/datasets/{ds_id}/rows/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    rows = (await client.get(f"/datasets/{ds_id}/rows")).json()["items"]
    row_id = rows[0]["id"]

    r = await client.delete(f"/datasets/{ds_id}/rows/{row_id}")
    assert r.status_code == 204

    updated = (await client.get(f"/datasets/{ds_id}/rows")).json()
    assert updated["total"] == 0
