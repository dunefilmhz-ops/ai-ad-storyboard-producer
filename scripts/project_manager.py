#!/usr/bin/env python3
"""Create and validate AI-ad production projects without calling generation APIs."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 2
SHOT_STATUSES = {"draft", "keyframe-review", "keyframe-approved", "video-review", "approved", "revision", "blocked"}
GATE_STATUSES = {"pending", "approved", "waived", "blocked"}
ASSET_STATUSES = {"draft", "review", "approved", "rejected", "deprecated"}
DECISION_STATUSES = {"open", "locked", "deferred"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def project_dirs() -> list[str]:
    return [
        "00_brief",
        "01_assets/characters",
        "01_assets/environments",
        "01_assets/props",
        "02_storyboard/shots",
        "03_keyframes",
        "04_video",
        "05_edit/contact-sheets",
        "06_delivery",
        "dashboard",
    ]


def init_project(args) -> int:
    root = Path(args.output).expanduser().resolve()
    if root.exists() and any(root.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to initialize non-empty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for relative in project_dirs():
        (root / relative).mkdir(parents=True, exist_ok=True)

    config = {
        "schema_version": SCHEMA_VERSION,
        "project_id": args.project_id or root.name,
        "title": args.title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "specs": {
            "aspect_ratio": args.aspect_ratio,
            "resolution": args.resolution,
            "fps": args.fps,
            "target_duration_seconds": args.duration,
            "language": args.language,
        },
        "toolchain": {
            "keyframe_model": args.keyframe_model,
            "video_model": args.video_model,
            "api_automation": "disabled",
        },
        "gates": {
            "intake": "pending",
            "storyboard": "pending",
            "continuity": "pending",
            "keyframe": "pending",
            "motion": "pending",
            "delivery": "pending",
        },
        "departments": {
            "brief": "pending",
            "art": "pending",
            "storyboard": "pending",
            "cinematography": "pending",
            "lighting": "pending",
            "motion": "pending",
            "edit": "pending",
            "sound": "pending",
            "delivery": "pending"
        },
        "source_authority_notes": [],
        "workflow_history": [],
    }
    write_json(root / "project-config.json", config)
    write_json(root / "02_storyboard" / "continuity-state.json", {
        "schema_version": SCHEMA_VERSION,
        "characters": {},
        "costume_stages": {},
        "props": {},
        "environments": {},
        "effects": {},
    })
    write_json(root / "00_brief" / "decision-log.json", {
        "schema_version": SCHEMA_VERSION,
        "decisions": []
    })
    write_json(root / "01_assets" / "asset-registry.json", {
        "schema_version": SCHEMA_VERSION,
        "assets": []
    })
    write_json(root / "dashboard" / "review-state.json", {
        "schema_version": SCHEMA_VERSION,
        "generated_at": None,
        "shots": [],
        "summary": {},
    })
    print(root)
    return 0


def shot_template(args) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "shot_id": args.shot_id,
        "client_shot_id": args.client_shot_id,
        "story_requirement": args.summary,
        "production_adjustment": "",
        "creative_rationale": {
            "story_function": "",
            "why_this_framing": "",
            "why_this_camera_motion": "",
            "why_this_light": "",
            "edit_intent": ""
        },
        "alternatives": [],
        "route": "gpt-keyframe-to-video",
        "model_profile": args.model_profile,
        "timing": {
            "client_reference_seconds": args.client_seconds,
            "generation_seconds": args.generation_seconds,
            "edit_use_seconds": args.edit_seconds,
        },
        "action_units": [],
        "risk_tags": [],
        "continuity": {
            "start": {
                "framing": "",
                "camera_height": "",
                "character_positions": {},
                "facing_and_gaze": {},
                "poses": {},
                "motion_vectors": {},
                "props": {},
                "environment_landmarks": [],
                "lighting": "",
            },
            "end": {
                "framing": "",
                "camera_height": "",
                "character_positions": {},
                "facing_and_gaze": {},
                "poses": {},
                "motion_vectors": {},
                "props": {},
                "environment_landmarks": [],
                "lighting": "",
            },
        },
        "assets": {
            "asset_refs": [],
            "keyframe": "",
            "video": "",
            "prompt_versions": [],
        },
        "review": {
            "status": "draft",
            "focus": [],
            "issues": [],
            "notes": "",
            "approved_version": None,
            "dimensions": {
                "story": "pending",
                "identity": "pending",
                "composition": "pending",
                "hands_and_contact": "pending",
                "action": "pending",
                "continuity": "pending",
                "lighting": "pending",
                "text_and_ui": "pending",
                "technical": "pending"
            },
            "updated_at": now_iso(),
        },
        "history": [],
    }


def add_shot(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    shot_dir = root / "02_storyboard" / "shots" / args.shot_id
    if shot_dir.exists() and not args.force:
        raise SystemExit(f"Shot already exists: {args.shot_id}")
    shot_dir.mkdir(parents=True, exist_ok=True)
    write_json(shot_dir / "shot.json", shot_template(args))
    (shot_dir / "prompts").mkdir(exist_ok=True)
    (root / "03_keyframes" / args.shot_id).mkdir(parents=True, exist_ok=True)
    (root / "04_video" / args.shot_id).mkdir(parents=True, exist_ok=True)
    print(shot_dir / "shot.json")
    return 0


def require_project(root: Path) -> None:
    if not (root / "project-config.json").is_file():
        raise SystemExit(f"Not an AI-ad production project: {root}")


def load_profiles() -> dict:
    path = Path(__file__).resolve().parent.parent / "references" / "model-profiles.json"
    return read_json(path)["profiles"]


def action_limit(profile: dict, seconds: float | None) -> int | None:
    if seconds is None or not profile.get("action_budget"):
        return None
    for range_text, limit in profile["action_budget"].items():
        low, high = (float(value) for value in range_text.split("-", 1))
        if low <= float(seconds) <= high:
            return int(limit)
    return None


def validate_shot(shot: dict, profiles: dict) -> list[dict]:
    findings = []
    shot_id = shot.get("shot_id", "UNKNOWN")
    timing = shot.get("timing", {})
    generation = timing.get("generation_seconds")
    profile_name = shot.get("model_profile")
    profile = profiles.get(profile_name)
    if profile is None:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "unknown_model_profile", "message": profile_name})
        return findings
    max_seconds = profile.get("max_request_seconds")
    if generation is None:
        findings.append({"severity": "warning", "shot_id": shot_id, "code": "missing_generation_seconds", "message": "Set generation duration before batching."})
    elif max_seconds is not None and generation > max_seconds:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "duration_over_model_limit", "message": f"{generation}s > {max_seconds}s"})
    actions = shot.get("action_units", [])
    limit = action_limit(profile, generation)
    if limit is not None and len(actions) > limit:
        findings.append({"severity": "warning", "shot_id": shot_id, "code": "action_budget_exceeded", "message": f"{len(actions)} action units > recommended {limit}; split or simplify."})
    risks = set(shot.get("risk_tags", []))
    high_risks = risks.intersection(profile.get("high_risk_tags", []))
    focus = set(shot.get("review", {}).get("focus", []))
    for risk in sorted(high_risks - focus):
        findings.append({"severity": "warning", "shot_id": shot_id, "code": "uncovered_review_risk", "message": f"Add '{risk}' to review.focus."})
    if "exact_text" in risks and shot.get("route") != "post-production":
        findings.append({"severity": "warning", "shot_id": shot_id, "code": "exact_text_route", "message": "Route exact text/UI/logo to post-production or an approved static UI asset."})
    if shot.get("review", {}).get("status") not in SHOT_STATUSES:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "invalid_review_status", "message": str(shot.get("review", {}).get("status"))})
    if not shot.get("story_requirement"):
        findings.append({"severity": "error", "shot_id": shot_id, "code": "missing_story_requirement", "message": "Story requirement is required."})
    return findings


def all_shots(root: Path) -> list[tuple[Path, dict]]:
    result = []
    for path in sorted((root / "02_storyboard" / "shots").glob("*/shot.json")):
        result.append((path, read_json(path)))
    return result


def add_asset(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    path = root / "01_assets" / "asset-registry.json"
    registry = read_json(path)
    if any(item.get("asset_id") == args.asset_id for item in registry.get("assets", [])) and not args.force:
        raise SystemExit(f"Asset already exists: {args.asset_id}")
    registry["assets"] = [item for item in registry.get("assets", []) if item.get("asset_id") != args.asset_id]
    registry["assets"].append({
        "asset_id": args.asset_id,
        "type": args.type,
        "version": args.version,
        "status": args.status,
        "identity_or_location": args.identity,
        "path": args.path,
        "prompt_path": args.prompt_path,
        "approved_invariants": [],
        "used_by_shots": [],
        "created_at": now_iso(),
        "updated_at": now_iso()
    })
    write_json(path, registry)
    print(path)
    return 0


def validate_project(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    config = read_json(root / "project-config.json")
    findings = []
    for gate, status in config.get("gates", {}).items():
        if status not in GATE_STATUSES:
            findings.append({"severity": "error", "shot_id": "PROJECT", "code": "invalid_gate_status", "message": f"{gate}: {status}"})
    for department, status in config.get("departments", {}).items():
        if status not in GATE_STATUSES:
            findings.append({"severity": "error", "shot_id": "PROJECT", "code": "invalid_department_status", "message": f"{department}: {status}"})
    registry = read_json(root / "01_assets" / "asset-registry.json")
    asset_ids = set()
    for asset in registry.get("assets", []):
        asset_id = asset.get("asset_id")
        if not asset_id:
            findings.append({"severity": "error", "shot_id": "ASSET", "code": "missing_asset_id", "message": str(asset)})
            continue
        if asset_id in asset_ids:
            findings.append({"severity": "error", "shot_id": "ASSET", "code": "duplicate_asset_id", "message": asset_id})
        asset_ids.add(asset_id)
        if asset.get("status") not in ASSET_STATUSES:
            findings.append({"severity": "error", "shot_id": "ASSET", "code": "invalid_asset_status", "message": f"{asset_id}: {asset.get('status')}"})
    profiles = load_profiles()
    shots = all_shots(root)
    if not shots:
        findings.append({"severity": "warning", "shot_id": "PROJECT", "code": "no_shots", "message": "No production shots have been created."})
    for _, shot in shots:
        findings.extend(validate_shot(shot, profiles))
        for asset_ref in shot.get("assets", {}).get("asset_refs", []):
            if asset_ref not in asset_ids:
                findings.append({"severity": "error", "shot_id": shot.get("shot_id"), "code": "missing_asset_reference", "message": asset_ref})
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "project": config.get("project_id"),
        "summary": {
            "shots": len(shots),
            "errors": sum(item["severity"] == "error" for item in findings),
            "warnings": sum(item["severity"] == "warning" for item in findings),
        },
        "findings": findings,
    }
    output = root / "dashboard" / "validation-report.json"
    write_json(output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    for finding in findings:
        print(f"{finding['severity'].upper()} {finding['shot_id']} {finding['code']}: {finding['message']}")
    return 1 if report["summary"]["errors"] else 0


def set_review(args) -> int:
    root = Path(args.project).expanduser().resolve()
    path = root / "02_storyboard" / "shots" / args.shot_id / "shot.json"
    shot = read_json(path)
    old = shot["review"].get("status")
    shot["review"]["status"] = args.status
    if args.issue:
        shot["review"].setdefault("issues", []).append(args.issue)
    if args.note:
        shot["review"]["notes"] = args.note
    shot["review"]["updated_at"] = now_iso()
    shot.setdefault("history", []).append({"at": now_iso(), "from": old, "to": args.status, "issue": args.issue, "note": args.note})
    write_json(path, shot)
    print(path)
    return 0


def set_workflow(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    path = root / "project-config.json"
    config = read_json(path)
    collection = "gates" if args.scope == "gate" else "departments"
    if args.name not in config.get(collection, {}):
        raise SystemExit(f"Unknown {args.scope}: {args.name}")
    old = config[collection][args.name]
    config[collection][args.name] = args.status
    config["updated_at"] = now_iso()
    config.setdefault("workflow_history", []).append({
        "at": now_iso(), "scope": args.scope, "name": args.name,
        "from": old, "to": args.status, "note": args.note,
    })
    write_json(path, config)
    print(path)
    return 0


def add_decision(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    path = root / "00_brief" / "decision-log.json"
    log = read_json(path)
    existing = next((item for item in log.get("decisions", []) if item.get("decision_id") == args.decision_id), None)
    if existing and not args.force:
        raise SystemExit(f"Decision already exists: {args.decision_id}")
    decision = {
        "decision_id": args.decision_id,
        "question": args.question,
        "options": args.option,
        "selected": args.selected,
        "rationale": args.rationale,
        "status": args.status,
        "created_at": existing.get("created_at") if existing else now_iso(),
        "updated_at": now_iso(),
    }
    log["decisions"] = [item for item in log.get("decisions", []) if item.get("decision_id") != args.decision_id]
    log["decisions"].append(decision)
    write_json(path, log)
    print(path)
    return 0


def export_dashboard(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    config = read_json(root / "project-config.json")
    asset_registry = read_json(root / "01_assets" / "asset-registry.json")
    rows = []
    for path, shot in all_shots(root):
        review = shot.get("review", {})
        timing = shot.get("timing", {})
        rows.append({
            "shot_id": shot.get("shot_id"),
            "client_shot_id": shot.get("client_shot_id"),
            "story_requirement": shot.get("story_requirement"),
            "route": shot.get("route"),
            "model_profile": shot.get("model_profile"),
            "generation_seconds": timing.get("generation_seconds"),
            "edit_use_seconds": timing.get("edit_use_seconds"),
            "action_units": len(shot.get("action_units", [])),
            "asset_refs": shot.get("assets", {}).get("asset_refs", []),
            "risk_tags": shot.get("risk_tags", []),
            "status": review.get("status"),
            "review_focus": review.get("focus", []),
            "issues": review.get("issues", []),
            "notes": review.get("notes", ""),
            "review_dimensions": review.get("dimensions", {}),
            "creative_rationale": shot.get("creative_rationale", {}),
            "shot_file": str(path.relative_to(root)),
        })
    counts = {status: sum(row["status"] == status for row in rows) for status in sorted(SHOT_STATUSES)}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "project": {"project_id": config.get("project_id"), "title": config.get("title"), "specs": config.get("specs"), "gates": config.get("gates"), "departments": config.get("departments", {})},
        "summary": {"shot_count": len(rows), "asset_count": len(asset_registry.get("assets", [])), "status_counts": counts, "open_issue_count": sum(len(row["issues"]) for row in rows)},
        "assets": asset_registry.get("assets", []),
        "shots": rows,
    }
    dashboard_dir = root / "dashboard"
    write_json(dashboard_dir / "review-state.json", payload)
    fieldnames = ["shot_id", "client_shot_id", "story_requirement", "route", "model_profile", "generation_seconds", "edit_use_seconds", "action_units", "asset_refs", "risk_tags", "status", "review_focus", "issues", "notes", "shot_file"]
    with (dashboard_dir / "review-board.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flattened = dict(row)
            flattened = {key: value for key, value in flattened.items() if key in fieldnames}
            for key in ("asset_refs", "risk_tags", "review_focus", "issues"):
                flattened[key] = " | ".join(flattened[key])
            writer.writerow(flattened)
    print(dashboard_dir)
    return 0


def doctor(args) -> int:
    checks = []
    for command in ("ffmpeg", "ffprobe"):
        checks.append({"name": command, "required_for": "contact-sheet and media QA", "available": shutil.which(command) is not None})
    checks.append({"name": "python", "required_for": "project management", "available": True, "version": sys.version.split()[0]})
    if args.project:
        root = Path(args.project).expanduser().resolve()
        checks.append({"name": "project-config", "required_for": "project workflow", "available": (root / "project-config.json").is_file()})
        checks.append({"name": "project-write", "required_for": "project workflow", "available": root.exists() and root.is_dir()})
    payload = {"generated_at": now_iso(), "api_automation": "not_checked", "checks": checks}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(item["available"] for item in checks) else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a production project")
    init.add_argument("--output", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--project-id")
    init.add_argument("--aspect-ratio", default="9:16")
    init.add_argument("--resolution", default="720x1280")
    init.add_argument("--fps", type=float, default=30)
    init.add_argument("--duration", type=float)
    init.add_argument("--language", default="zh-CN")
    init.add_argument("--keyframe-model", default="gpt-image-keyframe")
    init.add_argument("--video-model", default="seedance-2.0-mini")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=init_project)

    add = sub.add_parser("add-shot", help="Create a production-shot record")
    add.add_argument("--project", required=True)
    add.add_argument("--shot-id", required=True)
    add.add_argument("--client-shot-id", default="")
    add.add_argument("--summary", required=True)
    add.add_argument("--model-profile", default="seedance-2.0-mini")
    add.add_argument("--client-seconds", type=float)
    add.add_argument("--generation-seconds", type=float)
    add.add_argument("--edit-seconds", type=float)
    add.add_argument("--force", action="store_true")
    add.set_defaults(func=add_shot)

    asset = sub.add_parser("add-asset", help="Register a versioned character, costume, environment, prop or UI asset")
    asset.add_argument("--project", required=True)
    asset.add_argument("--asset-id", required=True)
    asset.add_argument("--type", required=True, choices=["character", "costume", "environment", "prop", "effect", "ui", "gameplay", "logo", "audio"])
    asset.add_argument("--version", default="v1")
    asset.add_argument("--status", default="draft", choices=sorted(ASSET_STATUSES))
    asset.add_argument("--identity", default="")
    asset.add_argument("--path", default="")
    asset.add_argument("--prompt-path", default="")
    asset.add_argument("--force", action="store_true")
    asset.set_defaults(func=add_asset)

    validate = sub.add_parser("validate", help="Validate gates, timing, action budgets and review coverage")
    validate.add_argument("--project", required=True)
    validate.set_defaults(func=validate_project)

    review = sub.add_parser("set-review", help="Update a shot review status and append history")
    review.add_argument("--project", required=True)
    review.add_argument("--shot-id", required=True)
    review.add_argument("--status", required=True, choices=sorted(SHOT_STATUSES))
    review.add_argument("--issue", default="")
    review.add_argument("--note", default="")
    review.set_defaults(func=set_review)

    workflow = sub.add_parser("set-workflow", help="Update a project gate or department status")
    workflow.add_argument("--project", required=True)
    workflow.add_argument("--scope", required=True, choices=["gate", "department"])
    workflow.add_argument("--name", required=True)
    workflow.add_argument("--status", required=True, choices=sorted(GATE_STATUSES))
    workflow.add_argument("--note", default="")
    workflow.set_defaults(func=set_workflow)

    decision = sub.add_parser("add-decision", help="Record or lock a material creative decision")
    decision.add_argument("--project", required=True)
    decision.add_argument("--decision-id", required=True)
    decision.add_argument("--question", required=True)
    decision.add_argument("--option", action="append", default=[])
    decision.add_argument("--selected", default="")
    decision.add_argument("--rationale", default="")
    decision.add_argument("--status", default="open", choices=sorted(DECISION_STATUSES))
    decision.add_argument("--force", action="store_true")
    decision.set_defaults(func=add_decision)

    dashboard = sub.add_parser("export-dashboard", help="Export JSON and CSV for a future review board")
    dashboard.add_argument("--project", required=True)
    dashboard.set_defaults(func=export_dashboard)

    doc = sub.add_parser("doctor", help="Check local non-API production capabilities")
    doc.add_argument("--project")
    doc.set_defaults(func=doctor)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
