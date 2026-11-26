import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from session_groups import configured_jobs, group_runs, recurring_job


@pytest.mark.parametrize(("first_user", "job"), [
    ("Run jobs/report.md", "Weekly report"),
    ("Run jobs/report.md\nfor this week", "Weekly report"),
    ("Run jobs/report.md.bak for this week", None),
    ("Explain how to Run jobs/report.md", None),
    ("", None),
])
def test_job_requires_the_configured_opening(first_user, job):
    rules = [{"name": "Weekly report", "opening": "Run jobs/report.md"}]
    assert recurring_job(first_user, rules) == job


@pytest.mark.parametrize(("field", "value"), [
    ("opening", ""), ("opening", "   "), ("name", None), ("name", 12),
])
def test_invalid_job_rule_reports_the_field(field, value):
    rule = {"name": "Weekly report", "opening": "Run jobs/report.md", field: value}
    with pytest.raises(ValueError, match=f"recurring_jobs.*{field}"):
        configured_jobs({"recurring_jobs": [rule]})


def test_bad_rule_is_reported_even_when_an_earlier_rule_matches():
    with pytest.raises(ValueError, match=r"recurring_jobs\[1\]"):
        configured_jobs({"recurring_jobs": [{"name": "Daily", "opening": "Start daily job"}, None]})


def test_group_preserves_member_files_recency_and_project_boundaries():
    latest = {"id": "first", "path": "/logs/first", "job": "Report", "tool": "claude",
              "cwd": "/work/team", "title": "Recurring work", "last_active": "today"}
    ordinary = dict(latest, id="ordinary", job=None)
    other_tool = dict(latest, tool="codex")
    other_project = dict(latest, id="other-project", cwd="/archive/team")
    other_job = dict(latest, id="other-job", job="Daily backup")
    older = dict(latest, id="older", path="/logs/older", last_active="yesterday")
    restored = dict(older, path="/logs/restored/older")
    earliest = dict(latest, id="earliest", path="/logs/earliest", last_active="last week")
    missing_project = dict(latest, id="unknown", cwd="")
    another_unknown = dict(missing_project, id="unknown-2")
    rows = [latest, ordinary, other_tool, other_project, other_job, older, restored,
            missing_project, another_unknown, earliest]

    group, *individual = group_runs(rows)
    assert group == dict(latest, title="Report · 2 runs", members=[latest, earliest])
    assert individual == [ordinary, other_tool, other_project, other_job, older, restored,
                          missing_project, another_unknown]
    assert latest["title"] == "Recurring work" and "members" not in latest
