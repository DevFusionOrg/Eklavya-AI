import csv
import io
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import confidence_buckets, stage_durations, state_from_form_data
from app.auth.dependencies import require_roles
from app.db.models import (
    Application,
    ApplicationStatusHistory,
    Deficiency,
    ExtractedField,
    ReviewAction,
    Scheme,
    SchemeVersion,
    User,
)
from app.db.session import get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])
ANALYTICS_ROLES = ("ADMIN", "SCRUTINY_OFFICER", "VERIFYING_OFFICER")


async def build_summary(session: AsyncSession) -> dict[str, Any]:
    applications = list((await session.scalars(select(Application))).all())
    histories = list(
        (
            await session.scalars(
                select(ApplicationStatusHistory).order_by(
                    ApplicationStatusHistory.application_id,
                    ApplicationStatusHistory.created_at,
                )
            )
        ).all()
    )
    deficiencies = list((await session.scalars(select(Deficiency))).all())
    actions = list((await session.scalars(select(ReviewAction))).all())
    fields = list((await session.scalars(select(ExtractedField))).all())
    scheme_rows = list(
        (
            await session.execute(
                select(Application.id, Scheme.code, Application.status)
                .join(SchemeVersion, SchemeVersion.id == Application.scheme_version_id)
                .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
            )
        ).all()
    )

    histories_by_application: defaultdict[uuid.UUID, list[Any]] = defaultdict(list)
    for item in histories:
        histories_by_application[item.application_id].append(item)
    status_counts = Counter(item.status for item in applications)
    funnel = [
        {"stage": stage, "count": status_counts.get(stage, 0)}
        for stage in (
            "DRAFT",
            "SUBMITTED",
            "AUTO_VALIDATION",
            "UNDER_SCRUTINY",
            "OFFICER_VERIFIED",
            "SELECTED",
            "APPROVED",
            "AWARDED",
        )
    ]
    duration_values: defaultdict[str, list[float]] = defaultdict(list)
    for history in histories_by_application.values():
        for stage, days in stage_durations(history).items():
            duration_values[stage].append(days)
    average_stage_time = {
        stage: round(sum(values) / len(values), 2)
        for stage, values in duration_values.items()
    }
    cause_counts = Counter(item.code for item in deficiencies)
    repeated = sum(item.correction_round > 0 for item in applications)
    overrides = Counter(
        item.override_source for item in actions if item.override_source != "NONE"
    )
    override_total = sum(1 for item in actions if item.override_source != "NONE")
    confidence_values = [
        float(item.confidence) for item in fields if item.confidence is not None
    ]
    scheme_performance: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for _, scheme, status in scheme_rows:
        scheme_performance[scheme][status] += 1
    state_distribution = Counter(
        state_from_form_data(item.form_data) for item in applications
    )
    return {
        "generated_at": datetime.now(UTC),
        "definitions": {
            "funnel": "Current application count grouped by lifecycle stage.",
            "average_time_per_stage_days": "Mean elapsed days between consecutive status-history events for each entered stage; open stages are excluded.",
            "deficiency_causes": "Count of deficiency records grouped by code, including resolved records.",
            "repeat_deficiency_rate": "Applications with correction_round greater than zero divided by all applications.",
            "override_rate": "Review actions with an AI or RULES override divided by all review actions.",
            "ocr_confidence": "Extracted-field confidence grouped as LOW below 0.75, MEDIUM from 0.75 through 0.89, HIGH at least 0.90.",
            "scheme_performance": "Application counts by scheme and current lifecycle status.",
            "state_distribution": "Applicant form state, then address.state, with missing values grouped as UNKNOWN.",
        },
        "funnel": funnel,
        "average_time_per_stage_days": average_stage_time,
        "deficiency_causes": [
            {"code": code, "count": count} for code, count in cause_counts.most_common()
        ],
        "repeat_deficiency_rate": {
            "numerator": repeated,
            "denominator": len(applications),
            "rate": round(repeated / len(applications), 4) if applications else 0,
        },
        "override_rate": {
            "numerator": override_total,
            "denominator": len(actions),
            "rate": round(override_total / len(actions), 4) if actions else 0,
            "by_source": dict(overrides),
        },
        "ocr_confidence": confidence_buckets(confidence_values),
        "scheme_performance": [
            {"scheme": scheme, "statuses": dict(counts)}
            for scheme, counts in sorted(scheme_performance.items())
        ],
        "state_distribution": [
            {"state": state, "count": count}
            for state, count in Counter(state_distribution).most_common()
        ],
        "totals": {
            "applications": len(applications),
            "deficiencies": len(deficiencies),
            "review_actions": len(actions),
            "ocr_fields": len(confidence_values),
        },
    }


@router.get("/summary")
async def analytics_summary(
    _: Annotated[User, Depends(require_roles(*ANALYTICS_ROLES))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    return await build_summary(session)


@router.get("/export")
async def analytics_export(
    _: Annotated[User, Depends(require_roles(*ANALYTICS_ROLES))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    format: Literal["csv", "pdf"] = Query(default="csv"),
) -> Response:
    summary = await build_summary(session)
    rows = [
        {"metric": "applications", "value": summary["totals"]["applications"]},
        {
            "metric": "repeat_deficiency_rate",
            "value": summary["repeat_deficiency_rate"]["rate"],
        },
        {"metric": "override_rate", "value": summary["override_rate"]["rate"]},
        *[
            {"metric": f"funnel.{item['stage']}", "value": item["count"]}
            for item in summary["funnel"]
        ],
        *[
            {"metric": f"deficiency.{item['code']}", "value": item["count"]}
            for item in summary["deficiency_causes"]
        ],
        *[
            {"metric": f"state.{item['state']}", "value": item["count"]}
            for item in summary["state_distribution"]
        ],
    ]
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=output.getvalue().encode(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics.csv"},
        )
    lines = ["Eklavya.AI Analytics Report"]
    lines.extend(f"{row['metric']}: {row['value']}" for row in rows)
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
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=analytics.pdf"},
    )
