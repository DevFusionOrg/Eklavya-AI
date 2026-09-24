"""Deterministic selection-list orchestration and export helpers."""

import csv
import io
import zipfile
from typing import Any
from xml.sax.saxutils import escape

from app.rules.selection import score_candidate


def rank_candidates(
    candidates: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    ranked = [
        {**candidate, "selection": score_candidate(candidate, config)}
        for candidate in candidates
    ]
    ranked.sort(
        key=lambda item: (
            -item["selection"]["score"],
            *(str(item.get(field, "")) for field in config.get("tie_breakers", [])),
            str(item.get("id", "")),
        )
    )
    limit = int(config.get("limit", len(ranked)))
    quotas = config.get("quotas", [])
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for item in ranked:
        if not item["selection"]["eligible"]:
            deferred.append(item)
            continue
        quota_ok = all(
            sum(
                1 for chosen in selected if chosen.get(quota["field"]) == quota["value"]
            )
            < int(quota["limit"])
            or item.get(quota["field"]) != quota["value"]
            for quota in quotas
        )
        if quota_ok and len(selected) < limit:
            selected.append(item)
        else:
            deferred.append(item)
    ranked = selected + deferred
    selected_ids = {item["id"] for item in selected}
    return [
        {
            **candidate,
            "rank": index,
            "list_status": (
                "SELECTED"
                if candidate["id"] in selected_ids
                else (
                    "WAITLISTED"
                    if candidate["selection"]["eligible"]
                    else "NOT_SELECTED"
                )
            ),
        }
        for index, candidate in enumerate(ranked, start=1)
    ]


def export_csv(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["rank", "application_id", "list_status", "score", "breakdown"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "rank": row.get("rank"),
                "application_id": row.get("application_id"),
                "list_status": row.get("list_status"),
                "score": row.get("score"),
                "breakdown": row.get("breakdown", {}),
            }
        )
    return output.getvalue().encode("utf-8")


def export_xlsx(rows: list[dict[str, Any]]) -> bytes:
    headers = ["rank", "application_id", "list_status", "score", "breakdown"]
    cells = []
    for row_index, row in enumerate([dict(zip(headers, headers)), *rows], start=1):
        values = [
            row.get(header, "") if row_index > 1 else header for header in headers
        ]
        cells.append(
            f"<row r='{row_index}'>"
            + "".join(
                f"<c t='inlineStr'><is><t>{escape(str(value))}</t></is></c>"
                for value in values
            )
            + "</row>"
        )
    worksheet = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
        f"<sheetData>{''.join(cells)}</sheetData></worksheet>"
    )
    content_types = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Override PartName='/xl/worksheets/sheet1.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'/>"
        "</Types>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buffer.getvalue()


def export_pdf(rows: list[dict[str, Any]]) -> bytes:
    lines = ["Eklavya.AI Selection List"]
    lines.extend(
        f"{row.get('rank')} {row.get('application_id')} {row.get('list_status')} {row.get('score')}"
        for row in rows
    )
    text = "\\n".join(lines).replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 50 750 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    output = io.BytesIO(b"%PDF-1.4\n")
    output.seek(0, io.SEEK_END)
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.write(
        b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    )
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return output.getvalue()
