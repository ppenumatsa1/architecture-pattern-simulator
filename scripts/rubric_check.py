import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8080"


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            payload = response.read().decode() or "{}"
            return response.getcode(), json.loads(payload)
    except urllib.error.HTTPError as error:
        payload = error.read().decode() or "{}"
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {"error": payload}
        return error.code, parsed


def pick(data: dict, *keys: str):
    for key in keys:
        if key in data:
            return data[key]
    return None


def poll(path: str, key: str, expected: str, timeout: int = 60) -> tuple[bool, dict]:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        code, data = req("GET", path)
        if isinstance(data, dict):
            last = data
        if code == 200 and isinstance(data, dict):
            value = data
            for part in key.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            if value == expected:
                return True, data
        time.sleep(1)
    return False, last


def main() -> None:
    auto_payload = {
        "policyType": "auto",
        "notes": "rubric-auto",
        "amount": 10000,
        "age": 35,
        "income": 75000,
        "creditScore": 740,
        "debtToIncome": 0.2,
        "latePaymentsLast12Months": 0,
        "hasBankruptcy": False,
        "fraudFlag": False,
    }
    review_payload = {
        "policyType": "home",
        "notes": "rubric-review",
        "amount": 30000,
        "age": 35,
        "income": 75000,
        "creditScore": 720,
        "debtToIncome": 0.2,
        "latePaymentsLast12Months": 1,
        "hasBankruptcy": False,
        "fraudFlag": False,
    }
    reject_payload = {
        "policyType": "life",
        "notes": "rubric-reject",
        "amount": 90000,
        "age": 41,
        "income": 52000,
        "creditScore": 520,
        "debtToIncome": 0.62,
        "latePaymentsLast12Months": 4,
        "hasBankruptcy": True,
        "fraudFlag": False,
    }

    cases: list[tuple[str, str, bool, str | None, str]] = []

    _, mono_auto = req(
        "POST",
        "/api/monolith/submissions",
        {"applicantId": "rubric-mono-auto", "payload": auto_payload},
    )
    mono_auto_id = str(pick(mono_auto, "submission_id", "submissionId"))
    ok, mono_auto_data = poll(
        f"/api/monolith/submissions/{mono_auto_id}", "state", "approved"
    )
    cases.append(
        ("monolith-auto", mono_auto_id, ok, mono_auto_data.get("state"), "approved")
    )

    _, mono_review = req(
        "POST",
        "/api/monolith/submissions",
        {"applicantId": "rubric-mono-review", "payload": review_payload},
    )
    mono_review_id = str(pick(mono_review, "submission_id", "submissionId"))
    ok, mono_review_data = poll(
        f"/api/monolith/submissions/{mono_review_id}", "state", "under_review"
    )
    cases.append(
        (
            "monolith-review",
            mono_review_id,
            ok,
            mono_review_data.get("state"),
            "under_review",
        )
    )

    _, mono_reject = req(
        "POST",
        "/api/monolith/submissions",
        {"applicantId": "rubric-mono-reject", "payload": reject_payload},
    )
    mono_reject_id = str(pick(mono_reject, "submission_id", "submissionId"))
    ok, mono_reject_data = poll(
        f"/api/monolith/submissions/{mono_reject_id}", "state", "rejected"
    )
    cases.append(
        (
            "monolith-reject",
            mono_reject_id,
            ok,
            mono_reject_data.get("state"),
            "rejected",
        )
    )

    _, micro_auto = req(
        "POST",
        "/api/microservices/submissions",
        {"applicant_id": "rubric-micro-auto", "payload": auto_payload},
    )
    micro_auto_id = str(pick(micro_auto, "submission_id", "submissionId"))
    ok, micro_auto_data = poll(
        f"/api/microservices/submissions/{micro_auto_id}/status", "status", "approved"
    )
    cases.append(
        ("micro-auto", micro_auto_id, ok, micro_auto_data.get("status"), "approved")
    )

    _, micro_review = req(
        "POST",
        "/api/microservices/submissions",
        {"applicant_id": "rubric-micro-review", "payload": review_payload},
    )
    micro_review_id = str(pick(micro_review, "submission_id", "submissionId"))
    ok, micro_review_data = poll(
        f"/api/microservices/submissions/{micro_review_id}/status",
        "status",
        "under_review",
    )
    cases.append(
        (
            "micro-review",
            micro_review_id,
            ok,
            micro_review_data.get("status"),
            "under_review",
        )
    )

    _, micro_reject = req(
        "POST",
        "/api/microservices/submissions",
        {"applicant_id": "rubric-micro-reject", "payload": reject_payload},
    )
    micro_reject_id = str(pick(micro_reject, "submission_id", "submissionId"))
    ok, micro_reject_data = poll(
        f"/api/microservices/submissions/{micro_reject_id}/status", "status", "rejected"
    )
    cases.append(
        (
            "micro-reject",
            micro_reject_id,
            ok,
            micro_reject_data.get("status"),
            "rejected",
        )
    )

    _, cqrs_auto = req(
        "POST",
        "/api/event-sourcing/commands/create-submission",
        {"applicantId": "rubric-cqrs-auto", "payload": auto_payload},
    )
    cqrs_auto_id = str(pick(cqrs_auto, "submission_id", "submissionId"))
    ok, cqrs_auto_data = poll(
        f"/api/event-sourcing/projections/{cqrs_auto_id}", "status", "approved"
    )
    cases.append(
        ("cqrs-auto", cqrs_auto_id, ok, cqrs_auto_data.get("status"), "approved")
    )

    _, cqrs_review = req(
        "POST",
        "/api/event-sourcing/commands/create-submission",
        {"applicantId": "rubric-cqrs-review", "payload": review_payload},
    )
    cqrs_review_id = str(pick(cqrs_review, "submission_id", "submissionId"))
    ok, cqrs_review_data = poll(
        f"/api/event-sourcing/projections/{cqrs_review_id}", "status", "under_review"
    )
    cases.append(
        (
            "cqrs-review",
            cqrs_review_id,
            ok,
            cqrs_review_data.get("status"),
            "under_review",
        )
    )

    _, cqrs_reject = req(
        "POST",
        "/api/event-sourcing/commands/create-submission",
        {"applicantId": "rubric-cqrs-reject", "payload": reject_payload},
    )
    cqrs_reject_id = str(pick(cqrs_reject, "submission_id", "submissionId"))
    ok, cqrs_reject_data = poll(
        f"/api/event-sourcing/projections/{cqrs_reject_id}", "status", "rejected"
    )
    cases.append(
        (
            "cqrs-reject",
            cqrs_reject_id,
            ok,
            cqrs_reject_data.get("status"),
            "rejected",
        )
    )

    results = []
    for name, submission_id, status_ok, status, expected in cases:
        results.append(
            {
                "case": name,
                "submission_id": submission_id,
                "status_ok": status_ok,
                "status": status,
                "expected": expected,
            }
        )

    _, mono_dash = req("GET", "/api/monolith/submissions?limit=100&offset=0")
    _, micro_dash = req(
        "GET", "/api/microservices/dashboard/submissions?limit=100&offset=0"
    )
    _, cqrs_dash = req(
        "GET", "/api/event-sourcing/dashboard/submissions?limit=100&offset=0"
    )

    mono_ids = (
        {str(item.get("submission_id")) for item in mono_dash.get("items", [])}
        if isinstance(mono_dash, dict)
        else set()
    )
    micro_ids = (
        {str(item.get("submissionId")) for item in micro_dash}
        if isinstance(micro_dash, list)
        else set()
    )
    cqrs_ids = (
        {str(item.get("submissionId")) for item in cqrs_dash}
        if isinstance(cqrs_dash, list)
        else set()
    )

    print(
        json.dumps(
            {
                "cases": results,
                "dashboard_hits": {
                    "monolith": sorted(
                        list(
                            {mono_auto_id, mono_review_id, mono_reject_id}.intersection(
                                mono_ids
                            )
                        )
                    ),
                    "micro": sorted(
                        list(
                            {
                                micro_auto_id,
                                micro_review_id,
                                micro_reject_id,
                            }.intersection(micro_ids)
                        )
                    ),
                    "cqrs": sorted(
                        list(
                            {cqrs_auto_id, cqrs_review_id, cqrs_reject_id}.intersection(
                                cqrs_ids
                            )
                        )
                    ),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
