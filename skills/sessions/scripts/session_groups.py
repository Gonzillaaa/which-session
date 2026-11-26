"""Recognize configured jobs and fold their runs within one agent and project."""
from collections import Counter


class JobConfigError(ValueError):
    """An invalid recurring job definition in settings.json."""


def configured_jobs(settings):
    if "recurring_jobs" not in settings or not isinstance(settings["recurring_jobs"], list):
        raise JobConfigError("settings.json: recurring_jobs must be an array")
    rules = settings["recurring_jobs"]
    for index, rule in enumerate(rules):
        for field in ("name", "opening"):
            if not isinstance(rule, dict) or field not in rule or not isinstance(rule[field], str) or not rule[field].strip():
                raise JobConfigError(f"settings.json: recurring_jobs[{index}].{field} must be a nonempty string")
    return rules


def recurring_job(first_user, rules):
    for rule in rules:
        opening = rule["opening"]
        if first_user.startswith(opening):
            boundary = first_user[len(opening):len(opening) + 1]
            if not boundary or boundary.isspace():
                return rule["name"]
    return None


def group_runs(rows):
    """Accept newest-first rows. Each group's first member determines its position."""
    copies = Counter((row["tool"], row["id"]) for row in rows)
    ordered = []
    jobs = {}
    for row in rows:
        if not row["job"] or not row["cwd"] or copies[row["tool"], row["id"]] > 1:
            ordered.append([row])
            continue
        key = (row["job"], row["tool"], row["cwd"])
        if key not in jobs:
            jobs[key] = []
            ordered.append(jobs[key])
        jobs[key].append(row)

    entries = []
    for members in ordered:
        latest = members[0]
        if len(members) > 1:
            title = f"{latest['job']} · {len(members)} runs"
            entries.append(dict(latest, title=title, members=members))
        else:
            entries.append(latest)
    return entries
