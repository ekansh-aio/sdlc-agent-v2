"""
HealthCheckFunction — HTTP trigger

Hit GET /api/HealthCheck to get a JSON report of all external dependencies.

Returns:
  200  — all checks passed (overall: "ok")
  207  — some checks passed with warnings (overall: "warn")
  503  — one or more checks failed (overall: "fail")

Safe to call at any time. Never modifies data.
"""

import json
import logging
import azure.functions as func
from common.health_check import run_all_checks


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("HealthCheckFunction triggered")

    try:
        report = run_all_checks()
    except Exception as e:
        logging.error(f"Health check runner crashed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"overall": "fail", "error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    status_map = {"ok": 200, "warn": 207, "fail": 503}
    http_status = status_map.get(report["overall"], 503)

    return func.HttpResponse(
        json.dumps(report, indent=2),
        status_code=http_status,
        mimetype="application/json",
    )
