#!/usr/bin/env python3
"""Create and validate AI-ad production projects without calling generation APIs."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


SCHEMA_VERSION = 3
SHOT_STATUSES = {"draft", "keyframe-review", "keyframe-approved", "video-review", "approved", "revision", "blocked"}
GATE_STATUSES = {"pending", "approved", "waived", "blocked"}
ASSET_STATUSES = {"draft", "review", "approved", "rejected", "deprecated"}
DECISION_STATUSES = {"open", "locked", "deferred"}
MAX_BOARD_REQUEST_BYTES = 2 * 1024 * 1024
MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024
MAX_REFERENCE_REQUEST_BYTES = MAX_REFERENCE_IMAGE_BYTES + 1024 * 1024
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm", ".m4v"}
REFERENCE_CATEGORIES = {"style", "character"}
REFERENCE_STATUSES = {"active", "deleted"}
REFERENCE_MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
REFERENCE_MIME_ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "image/x-png": "image/png",
}
REFERENCE_REGISTRY_RELATIVE = Path("01_assets/reference-library.json")
REFERENCE_LIBRARY_RELATIVE = Path("01_assets/references")


class RevisionConflict(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def write_bytes(path: Path, value: bytes) -> None:
    """Atomically write a small uploaded file on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def validate_safe_id(value: str, label: str = "id") -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value or ""):
        raise ValueError(f"Invalid {label}: use letters, digits, hyphen or underscore only")
    return value


def contained_path(base: Path, candidate: Path, label: str = "path") -> Path:
    base = base.resolve()
    candidate = candidate.resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError(f"{label} escapes its allowed directory")
    return candidate


def reference_registry_path(root: Path) -> Path:
    return root / REFERENCE_REGISTRY_RELATIVE


def empty_reference_registry() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "references": [],
        "history": [],
    }


def load_reference_registry(root: Path) -> dict:
    path = reference_registry_path(root)
    if not path.is_file():
        return empty_reference_registry()
    registry = read_json(path)
    if not isinstance(registry, dict):
        raise ValueError("reference library must be an object")
    if not isinstance(registry.get("references", []), list):
        raise ValueError("reference library references must be a list")
    if not isinstance(registry.get("history", []), list):
        raise ValueError("reference library history must be a list")
    revision = registry.get("revision", 0)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValueError("reference library revision must be a non-negative integer")
    registry.setdefault("schema_version", SCHEMA_VERSION)
    registry.setdefault("revision", 0)
    registry.setdefault("references", [])
    registry.setdefault("history", [])
    return registry


def normalize_reference_category(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("reference category must be text")
    category = value.strip().lower()
    if category not in REFERENCE_CATEGORIES:
        raise ValueError(f"reference category must be one of: {', '.join(sorted(REFERENCE_CATEGORIES))}")
    return category


def normalize_reference_text(value, label: str, maximum: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"{label} is too long (maximum {maximum} characters)")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
        raise ValueError(f"{label} contains control characters")
    return value


def normalize_original_filename(value: str) -> str:
    value = normalize_reference_text(value or "upload", "filename", 255)
    value = Path(value.replace("\\", "/")).name.strip(". ")
    return value or "upload"


def normalize_image_mime(value: str | None) -> str:
    mime = (value or "").split(";", 1)[0].strip().lower()
    return REFERENCE_MIME_ALIASES.get(mime, mime)


def sniff_image_mime(value: bytes) -> str | None:
    if value.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if value.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if value.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_reference_image(value: bytes, claimed_mime: str | None = None) -> str:
    if not value:
        raise ValueError("reference image is empty")
    if len(value) > MAX_REFERENCE_IMAGE_BYTES:
        raise ValueError(f"reference image exceeds {MAX_REFERENCE_IMAGE_BYTES // (1024 * 1024)} MiB")
    detected = sniff_image_mime(value[:32])
    if detected not in REFERENCE_MIME_EXTENSIONS:
        raise ValueError("unsupported or invalid image; use PNG, JPEG, WebP or GIF")
    claimed = normalize_image_mime(claimed_mime)
    if claimed and claimed != "application/octet-stream" and claimed != detected:
        raise ValueError(f"image MIME mismatch: claimed {claimed}, detected {detected}")
    return detected


def reference_absolute_path(root: Path, relative: str, category: str | None = None, trash: bool = False) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("reference path must be a non-empty project-relative path")
    if trash:
        base = root / REFERENCE_LIBRARY_RELATIVE / ".trash"
    elif category:
        base = root / REFERENCE_LIBRARY_RELATIVE / normalize_reference_category(category)
    else:
        base = root / REFERENCE_LIBRARY_RELATIVE
    return contained_path(base, root / relative, "reference path")


def find_reference(registry: dict, reference_id: str) -> dict:
    validate_safe_id(reference_id, "reference id")
    reference = next((item for item in registry.get("references", []) if item.get("reference_id") == reference_id), None)
    if reference is None:
        raise FileNotFoundError(reference_id)
    return reference


def next_reference_id(registry: dict) -> str:
    existing = {item.get("reference_id") for item in registry.get("references", [])}
    while True:
        candidate = f"ref-{uuid.uuid4().hex[:12]}"
        if candidate not in existing:
            return candidate


def record_reference_history(registry: dict, action: str, reference: dict, actor: str, changed_fields: list[str] | None = None) -> None:
    from_revision = int(registry.get("revision", 0))
    registry["revision"] = from_revision + 1
    entry = {
        "at": now_iso(),
        "action": action,
        "actor": actor,
        "reference_id": reference.get("reference_id"),
        "reference_revision": int(reference.get("revision", 0)),
        "from_revision": from_revision,
        "revision": registry["revision"],
    }
    if changed_fields:
        entry["changed_fields"] = changed_fields
    registry.setdefault("history", []).append(entry)


def public_reference(root: Path, reference: dict) -> dict:
    item = copy.deepcopy(reference)
    item.pop("trash_path", None)
    item["id"] = item.get("reference_id")
    path = item.get("path", "")
    item["file_url"] = f"/files/{quote(path, safe='/')}" if item.get("status") == "active" and path else ""
    return item


def reference_library_payload(root: Path) -> dict:
    registry = load_reference_registry(root)
    active = []
    deleted = []
    for reference in registry.get("references", []):
        status = reference.get("status", "active")
        item = public_reference(root, reference)
        if status == "deleted":
            deleted.append(item)
        else:
            active.append(item)
    active.sort(key=lambda item: (item.get("category", ""), item.get("created_at", ""), item.get("reference_id", "")))
    deleted.sort(key=lambda item: (item.get("deleted_at", ""), item.get("reference_id", "")), reverse=True)
    return {
        "revision": int(registry.get("revision", 0)),
        "references": active,
        "deleted_references": deleted,
    }


def add_reference_bytes(
    root: Path,
    value: bytes,
    category: str,
    label: str = "",
    note: str = "",
    original_name: str = "upload",
    claimed_mime: str | None = None,
    reference_id: str | None = None,
    actor: str = "local-review-board",
) -> dict:
    require_project(root)
    category = normalize_reference_category(category)
    label = normalize_reference_text(label, "reference label", 200)
    note = normalize_reference_text(note, "reference note", 10_000)
    original_name = normalize_original_filename(original_name)
    mime = validate_reference_image(value, claimed_mime)
    registry = load_reference_registry(root)
    if reference_id:
        reference_id = validate_safe_id(reference_id, "reference id")
        if any(item.get("reference_id") == reference_id for item in registry.get("references", [])):
            raise ValueError(f"reference already exists: {reference_id}")
    else:
        reference_id = next_reference_id(registry)
    relative = (REFERENCE_LIBRARY_RELATIVE / category / f"{reference_id}{REFERENCE_MIME_EXTENSIONS[mime]}").as_posix()
    destination = reference_absolute_path(root, relative, category=category)
    if destination.exists():
        raise ValueError(f"reference destination already exists: {relative}")
    timestamp = now_iso()
    reference = {
        "reference_id": reference_id,
        "revision": 0,
        "category": category,
        "label": label or Path(original_name).stem[:200],
        "note": note,
        "path": relative,
        "original_name": original_name,
        "mime_type": mime,
        "size_bytes": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "deleted_at": None,
        "history": [{"at": timestamp, "action": "upload", "actor": actor, "revision": 0}],
    }
    write_bytes(destination, value)
    try:
        registry.setdefault("references", []).append(reference)
        record_reference_history(registry, "add_reference", reference, actor)
        write_json(reference_registry_path(root), registry)
    except Exception:
        if destination.is_file():
            destination.unlink()
        raise
    return public_reference(root, reference)


def validate_reference_base_revision(value, current_revision: int) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("base_revision must be a non-negative integer")
    if value != current_revision:
        raise RevisionConflict(f"This reference changed in another tab (current revision {current_revision}); reload before saving.")


def update_reference_metadata(root: Path, reference_id: str, payload: dict) -> dict:
    payload = require_mapping(payload, "payload")
    unknown = set(payload) - {"label", "note", "base_revision", "actor"}
    if unknown:
        raise ValueError(f"unsupported reference fields: {', '.join(sorted(unknown))}")
    registry = load_reference_registry(root)
    reference = find_reference(registry, reference_id)
    current_revision = int(reference.get("revision", 0))
    validate_reference_base_revision(payload.get("base_revision"), current_revision)
    changed = []
    for key, maximum in (("label", 200), ("note", 10_000)):
        if key in payload:
            value = normalize_reference_text(payload[key], f"reference {key}", maximum)
            if reference.get(key, "") != value:
                reference[key] = value
                changed.append(key)
    if changed:
        reference["revision"] = current_revision + 1
        reference["updated_at"] = now_iso()
        actor = normalize_reference_text(payload.get("actor", "local-review-board"), "actor", 200) or "local-review-board"
        reference.setdefault("history", []).append({
            "at": now_iso(), "action": "update_metadata", "actor": actor,
            "from_revision": current_revision, "revision": reference["revision"],
            "changed_fields": changed,
        })
        record_reference_history(registry, "update_reference", reference, actor, changed)
        write_json(reference_registry_path(root), registry)
    return public_reference(root, reference)


def delete_reference(root: Path, reference_id: str, base_revision=None, actor: str = "local-review-board") -> dict:
    registry = load_reference_registry(root)
    reference = find_reference(registry, reference_id)
    current_revision = int(reference.get("revision", 0))
    validate_reference_base_revision(base_revision, current_revision)
    if reference.get("status", "active") == "deleted":
        return public_reference(root, reference)
    source = reference_absolute_path(root, reference.get("path", ""), category=reference.get("category"))
    trash_relative = ""
    trash_destination = None
    if source.is_file():
        trash_relative = (REFERENCE_LIBRARY_RELATIVE / ".trash" / f"{reference_id}-{uuid.uuid4().hex[:8]}{source.suffix.lower()}").as_posix()
        trash_destination = reference_absolute_path(root, trash_relative, trash=True)
        trash_destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, trash_destination)
    timestamp = now_iso()
    reference["revision"] = current_revision + 1
    reference["status"] = "deleted"
    reference["deleted_at"] = timestamp
    reference["updated_at"] = timestamp
    reference["trash_path"] = trash_relative
    actor = normalize_reference_text(actor, "actor", 200) or "local-review-board"
    reference.setdefault("history", []).append({
        "at": timestamp, "action": "delete", "actor": actor,
        "from_revision": current_revision, "revision": reference["revision"],
    })
    try:
        record_reference_history(registry, "delete_reference", reference, actor, ["status"])
        write_json(reference_registry_path(root), registry)
    except Exception:
        if trash_destination and trash_destination.is_file() and not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            os.replace(trash_destination, source)
        raise
    return public_reference(root, reference)


def restore_reference(root: Path, reference_id: str, base_revision=None, actor: str = "local-review-board") -> dict:
    registry = load_reference_registry(root)
    reference = find_reference(registry, reference_id)
    current_revision = int(reference.get("revision", 0))
    validate_reference_base_revision(base_revision, current_revision)
    if reference.get("status", "active") != "deleted":
        return public_reference(root, reference)
    trash_relative = reference.get("trash_path", "")
    if not trash_relative:
        raise ValueError("deleted reference has no recoverable file")
    source = reference_absolute_path(root, trash_relative, trash=True)
    if not source.is_file():
        raise ValueError("deleted reference file is missing from trash")
    destination = reference_absolute_path(root, reference.get("path", ""), category=reference.get("category"))
    if destination.exists():
        raise ValueError("cannot restore because the original destination is occupied")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, destination)
    timestamp = now_iso()
    reference["revision"] = current_revision + 1
    reference["status"] = "active"
    reference["deleted_at"] = None
    reference["updated_at"] = timestamp
    reference.pop("trash_path", None)
    actor = normalize_reference_text(actor, "actor", 200) or "local-review-board"
    reference.setdefault("history", []).append({
        "at": timestamp, "action": "restore", "actor": actor,
        "from_revision": current_revision, "revision": reference["revision"],
    })
    try:
        record_reference_history(registry, "restore_reference", reference, actor, ["status"])
        write_json(reference_registry_path(root), registry)
    except Exception:
        if destination.is_file() and not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            os.replace(destination, source)
        raise
    return public_reference(root, reference)


def project_dirs() -> list[str]:
    return [
        "00_brief",
        "01_assets/characters",
        "01_assets/environments",
        "01_assets/props",
        "01_assets/references/style",
        "01_assets/references/character",
        "01_assets/references/.trash",
        "02_storyboard/shots",
        "02_storyboard/scenes",
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
    write_json(root / "00_brief" / "story-state.json", {
        "schema_version": SCHEMA_VERSION,
        "premise": "",
        "central_conflict": "",
        "audience_promise": "",
        "opening_state": "",
        "ending_state": "",
        "beats": [],
    })
    write_json(root / "02_storyboard" / "field-policy.json", {
        "schema_version": SCHEMA_VERSION,
        "locked": [],
        "state_driven": [],
        "shot_dynamic": [],
        "notes": "Classify fields before batch prompting; locked fields require explicit approval to change.",
    })
    write_json(root / "02_storyboard" / "scenes" / "scene-bibles.json", {
        "schema_version": SCHEMA_VERSION,
        "scenes": [],
    })
    write_json(root / "00_brief" / "decision-log.json", {
        "schema_version": SCHEMA_VERSION,
        "decisions": []
    })
    write_json(root / "01_assets" / "asset-registry.json", {
        "schema_version": SCHEMA_VERSION,
        "assets": []
    })
    write_json(root / REFERENCE_REGISTRY_RELATIVE, {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "references": [],
        "history": [],
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
        "revision": 0,
        "client_shot_id": args.client_shot_id,
        "story_requirement": args.summary,
        "scene_id": "",
        "story": {
            "function": "",
            "new_information": "",
            "conflict_delta": "",
            "emotion_delta": "",
            "relationship_delta": "",
            "visual_delta": "",
            "outcome_delta": "",
            "next_hook": "",
        },
        "characters": [],
        "production_adjustment": "",
        "blocking_diagram": "",
        "blocking": {
            "axis_id": "",
            "camera_side": "",
            "world_space": {},
            "screen_space": {},
        },
        "motion": {
            "start": {},
            "preparation": "",
            "path": "",
            "impact": "",
            "reaction": "",
            "end": {},
            "dominant_vector": "",
            "continuity_anchors": [],
        },
        "camera": {
            "shot_size": "",
            "angle": "",
            "height": "",
            "lens": "",
            "movement": "",
            "cut_motivation": "",
        },
        "transition": {
            "inherit_from": "",
            "type": "",
            "allowed_delta": {},
        },
        "editorial": {
            "client_script": "",
            "shot_script": "",
            "dialogue": "",
            "voiceover": "",
            "on_screen_text": "",
            "keyframe_prompt": "",
            "video_prompt": "",
            "negative_prompt": "",
            "post_production": "",
        },
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
        "production": {
            "priority": "B",
            "generation_complexity": {
                "score": 0,
                "factors": {
                    "character_count": 0,
                    "contact_complexity": 0,
                    "prop_interaction": 0,
                    "motion_complexity": 0,
                    "camera_motion": 0,
                    "transformation": 0,
                    "continuity_dependency": 0,
                },
            },
            "generation_budget": "",
            "failure_source": "",
        },
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
        "annotations": [],
        "history": [],
    }


def add_shot(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    validate_safe_id(args.shot_id, "shot id")
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
    blocking_risks = {
        "multi_character_contact", "fight", "door_motion", "weapon_continuity",
        "screen_direction", "crossing", "crowd", "fall",
    }
    continuity = shot.get("continuity", {})
    position_count = max(
        len(continuity.get("start", {}).get("character_positions", {})),
        len(continuity.get("end", {}).get("character_positions", {})),
    )
    if not str(shot.get("blocking_diagram", "")).strip() and (risks.intersection(blocking_risks) or position_count >= 2):
        findings.append({
            "severity": "warning",
            "shot_id": shot_id,
            "code": "missing_blocking_diagram",
            "message": "Add a blocking diagram with camera, screen/space direction, character positions, facing and motion arrows.",
        })
    production = shot.get("production", {})
    priority = production.get("priority", "B")
    if priority not in {"A", "B", "C"}:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "invalid_generation_priority", "message": str(priority)})
    complexity = production.get("generation_complexity", {})
    score = complexity.get("score", 0) if isinstance(complexity, dict) else complexity
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 10:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "invalid_generation_complexity", "message": "generation complexity must be between 0 and 10"})
    elif score >= 8 and not ({"complex_motion", "multi_character_contact", "camera_motion_complexity", "transformation"} & risks):
        findings.append({"severity": "warning", "shot_id": shot_id, "code": "high_complexity_without_risk", "message": "Add the controlling risk tag and plan split coverage or Pose A/B/C."})
    failure_source = production.get("failure_source", "")
    if failure_source and failure_source not in {"prompt", "asset", "spatial", "motion", "camera", "model"}:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "invalid_failure_source", "message": str(failure_source)})
    transition_type = shot.get("transition", {}).get("type", "")
    valid_transitions = {"", "exact", "action", "temporal", "reaction", "insert", "time-jump", "spatial-reestablish"}
    if transition_type not in valid_transitions:
        findings.append({"severity": "error", "shot_id": shot_id, "code": "invalid_transition_type", "message": str(transition_type)})
    blocking = shot.get("blocking", {})
    if blocking and (blocking.get("axis_id") or blocking.get("camera_side")):
        if not blocking.get("world_space") or not blocking.get("screen_space"):
            findings.append({"severity": "warning", "shot_id": shot_id, "code": "incomplete_structured_blocking", "message": "Record both world_space and screen_space before keyframe approval."})
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


def add_reference(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    source = Path(args.file).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"reference image not found: {source}")
    if source.stat().st_size > MAX_REFERENCE_IMAGE_BYTES:
        raise ValueError(f"reference image exceeds {MAX_REFERENCE_IMAGE_BYTES // (1024 * 1024)} MiB")
    with source.open("rb") as handle:
        value = handle.read(MAX_REFERENCE_IMAGE_BYTES + 1)
    reference = add_reference_bytes(
        root,
        value,
        category=args.category,
        label=args.label,
        note=args.note,
        original_name=source.name,
        claimed_mime=mimetypes.guess_type(source.name)[0],
        reference_id=args.reference_id,
        actor="cli",
    )
    payload = {
        "ok": True,
        "reference": reference,
        "reference_library_revision": load_reference_registry(root).get("revision", 0),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
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
    reference_registry = load_reference_registry(root)
    reference_ids = set()
    for reference in reference_registry.get("references", []):
        if not isinstance(reference, dict):
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "invalid_reference", "message": str(reference)})
            continue
        reference_id = reference.get("reference_id", "")
        try:
            validate_safe_id(reference_id, "reference id")
        except ValueError as exc:
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "invalid_reference_id", "message": str(exc)})
            continue
        if reference_id in reference_ids:
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "duplicate_reference_id", "message": reference_id})
        reference_ids.add(reference_id)
        category = reference.get("category")
        status = reference.get("status", "active")
        if category not in REFERENCE_CATEGORIES:
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "invalid_reference_category", "message": f"{reference_id}: {category}"})
            continue
        if status not in REFERENCE_STATUSES:
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "invalid_reference_status", "message": f"{reference_id}: {status}"})
            continue
        try:
            if status == "active":
                media_path = reference_absolute_path(root, reference.get("path", ""), category=category)
            else:
                trash_path = reference.get("trash_path", "")
                media_path = reference_absolute_path(root, trash_path, trash=True) if trash_path else None
        except ValueError as exc:
            findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "unsafe_reference_path", "message": f"{reference_id}: {exc}"})
            continue
        if media_path is None:
            findings.append({"severity": "warning", "shot_id": "REFERENCE", "code": "unrecoverable_deleted_reference", "message": reference_id})
        elif not media_path.is_file():
            findings.append({"severity": "error" if status == "active" else "warning", "shot_id": "REFERENCE", "code": "missing_reference_file", "message": f"{reference_id}: {media_path.relative_to(root)}"})
        else:
            actual_size = media_path.stat().st_size
            with media_path.open("rb") as handle:
                actual_mime = sniff_image_mime(handle.read(32))
            if actual_mime != reference.get("mime_type"):
                findings.append({"severity": "error", "shot_id": "REFERENCE", "code": "reference_mime_mismatch", "message": f"{reference_id}: {reference.get('mime_type')} vs {actual_mime}"})
            if actual_size != reference.get("size_bytes"):
                findings.append({"severity": "warning", "shot_id": "REFERENCE", "code": "reference_size_mismatch", "message": f"{reference_id}: {reference.get('size_bytes')} vs {actual_size}"})
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
    validate_safe_id(args.shot_id, "shot id")
    path = root / "02_storyboard" / "shots" / args.shot_id / "shot.json"
    shot = read_json(path)
    old = shot["review"].get("status")
    from_revision = int(shot.get("revision", 0))
    shot["review"]["status"] = args.status
    if args.issue:
        shot["review"].setdefault("issues", []).append(args.issue)
    if args.note:
        shot["review"]["notes"] = args.note
    shot["review"]["updated_at"] = now_iso()
    shot["revision"] = from_revision + 1
    shot.setdefault("history", []).append({
        "at": now_iso(), "action": "set_review", "actor": "cli",
        "from_revision": from_revision, "revision": shot["revision"],
        "before": {"review.status": old},
        "after": {"review.status": args.status, "review.issue_added": args.issue, "review.notes": args.note},
    })
    write_json(path, shot)
    print(path)
    return 0


def set_shot_media(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    validate_safe_id(args.shot_id, "shot id")
    shot_path = root / "02_storyboard" / "shots" / args.shot_id / "shot.json"
    if not shot_path.is_file():
        raise SystemExit(f"Unknown shot: {args.shot_id}")
    media_path = Path(args.file).expanduser().resolve()
    if not media_path.is_file():
        raise SystemExit(f"Media file not found: {media_path}")
    if media_path.suffix.lower() not in MEDIA_SUFFIXES:
        raise SystemExit(f"Unsupported media type: {media_path.suffix}")
    try:
        relative = media_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise SystemExit("Shot media must be stored inside the project directory.") from exc
    shot = read_json(shot_path)
    current_revision = int(shot.get("revision", 0))
    assets = shot.setdefault("assets", {})
    old_path = assets.get(args.kind, "")
    old_status = shot.get("review", {}).get("status")
    changed_fields = []
    if old_path != relative:
        assets[args.kind] = relative
        changed_fields.append(f"assets.{args.kind}")
    if args.status:
        if args.status not in SHOT_STATUSES:
            raise SystemExit(f"Invalid review status: {args.status}")
        review = shot.setdefault("review", {})
        if review.get("status") != args.status:
            review["status"] = args.status
            review["updated_at"] = now_iso()
            changed_fields.append("review.status")
    if changed_fields:
        shot["revision"] = current_revision + 1
        shot.setdefault("history", []).append({
            "at": now_iso(),
            "action": f"attach_{args.kind}",
            "actor": args.actor,
            "from_revision": current_revision,
            "revision": current_revision + 1,
            "changed_fields": changed_fields,
            "before": {f"assets.{args.kind}": old_path, "review.status": old_status},
            "after": {f"assets.{args.kind}": relative, "review.status": shot.get("review", {}).get("status")},
        })
        write_json(shot_path, shot)
        write_dashboard_files(root)
    print(json.dumps({"shot_id": args.shot_id, "revision": shot.get("revision", 0), args.kind: relative, "changed_fields": changed_fields}, ensure_ascii=False))
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


def dashboard_payload(root: Path) -> dict:
    config = read_json(root / "project-config.json")
    asset_registry = read_json(root / "01_assets" / "asset-registry.json")
    reference_library = reference_library_payload(root)
    rows = []
    for path, shot in all_shots(root):
        review = shot.get("review", {})
        timing = shot.get("timing", {})
        rows.append({
            "shot_id": shot.get("shot_id"),
            "revision": int(shot.get("revision", 0)),
            "client_shot_id": shot.get("client_shot_id"),
            "story_requirement": shot.get("story_requirement"),
            "production_adjustment": shot.get("production_adjustment", ""),
            "blocking_diagram": shot.get("blocking_diagram", ""),
            "editorial": shot.get("editorial", {}),
            "route": shot.get("route"),
            "model_profile": shot.get("model_profile"),
            "client_reference_seconds": timing.get("client_reference_seconds"),
            "generation_seconds": timing.get("generation_seconds"),
            "edit_use_seconds": timing.get("edit_use_seconds"),
            "action_units": len(shot.get("action_units", [])),
            "asset_refs": shot.get("assets", {}).get("asset_refs", []),
            "keyframe": shot.get("assets", {}).get("keyframe", ""),
            "video": shot.get("assets", {}).get("video", ""),
            "risk_tags": shot.get("risk_tags", []),
            "status": review.get("status"),
            "review_focus": review.get("focus", []),
            "issues": review.get("issues", []),
            "notes": review.get("notes", ""),
            "annotations": shot.get("annotations", []),
            "review_dimensions": review.get("dimensions", {}),
            "creative_rationale": shot.get("creative_rationale", {}),
            "shot_file": str(path.relative_to(root)),
        })
    counts = {status: sum(row["status"] == status for row in rows) for status in sorted(SHOT_STATUSES)}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "project": {"project_id": config.get("project_id"), "title": config.get("title"), "specs": config.get("specs"), "gates": config.get("gates"), "departments": config.get("departments", {})},
        "summary": {
            "shot_count": len(rows),
            "asset_count": len(asset_registry.get("assets", [])),
            "reference_count": len(reference_library["references"]),
            "status_counts": counts,
            "open_issue_count": sum(len(row["issues"]) for row in rows),
        },
        "assets": asset_registry.get("assets", []),
        "asset_library_revision": int(asset_registry.get("revision", 0)),
        "references": reference_library["references"],
        "deleted_references": reference_library["deleted_references"],
        "reference_library_revision": reference_library["revision"],
        "shots": rows,
    }
    return payload


def update_asset_from_board(root: Path, asset_id: str, payload: dict) -> dict:
    """Revision-safe metadata update for a generated/confirmable production asset."""
    validate_safe_id(asset_id, "asset id")
    unknown = set(payload) - {"status", "identity_or_location", "approval_note", "stage", "base_revision", "actor"}
    if unknown:
        raise ValueError(f"unsupported asset fields: {', '.join(sorted(unknown))}")
    path = root / "01_assets" / "asset-registry.json"
    registry = read_json(path)
    asset = next((item for item in registry.get("assets", []) if item.get("asset_id") == asset_id), None)
    if asset is None:
        raise FileNotFoundError(asset_id)
    current_revision = int(asset.get("revision", 0))
    base_revision = payload.get("base_revision")
    if base_revision is not None and base_revision != current_revision:
        raise RevisionConflict(f"This asset changed in another tab (current revision {current_revision}); reload before saving.")
    status = payload.get("status", asset.get("status", "draft"))
    if status not in ASSET_STATUSES:
        raise ValueError("invalid asset status")
    changed = []
    for key, maximum in (("identity_or_location", 4_000), ("approval_note", 8_000), ("stage", 200)):
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, str) or len(value) > maximum:
            raise ValueError(f"{key} must be text no longer than {maximum} characters")
        if asset.get(key, "") != value:
            asset[key] = value
            changed.append(key)
    if asset.get("status") != status:
        asset["status"] = status
        changed.append("status")
    if changed:
        asset["revision"] = current_revision + 1
        asset["updated_at"] = now_iso()
        registry["revision"] = int(registry.get("revision", 0)) + 1
        registry.setdefault("history", []).append({
            "at": now_iso(), "action": "asset_board_update", "asset_id": asset_id,
            "actor": payload.get("actor", "local-review-board"), "changed_fields": changed,
            "asset_revision": asset["revision"], "library_revision": registry["revision"],
        })
        write_json(path, registry)
        write_dashboard_files(root)
    return asset


def write_dashboard_files(root: Path) -> dict:
    payload = dashboard_payload(root)
    dashboard_dir = root / "dashboard"
    write_json(dashboard_dir / "review-state.json", payload)
    fieldnames = ["shot_id", "client_shot_id", "story_requirement", "blocking_diagram", "route", "model_profile", "generation_seconds", "edit_use_seconds", "action_units", "asset_refs", "risk_tags", "status", "review_focus", "issues", "notes", "shot_file"]
    with (dashboard_dir / "review-board.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in payload["shots"]:
            flattened = dict(row)
            flattened = {key: value for key, value in flattened.items() if key in fieldnames}
            for key in ("asset_refs", "risk_tags", "review_focus", "issues"):
                flattened[key] = " | ".join(flattened[key])
            writer.writerow(flattened)
    template = Path(__file__).resolve().parent.parent / "assets" / "review-board" / "index.html"
    if template.is_file():
        shutil.copyfile(template, dashboard_dir / "index.html")
    return payload


def export_dashboard(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    write_dashboard_files(root)
    dashboard_dir = root / "dashboard"
    print(dashboard_dir)
    return 0


def inspect_project(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    requested_ids = args.shot_id or []
    fields = args.field or []
    if requested_ids:
        records = []
        for shot_id in requested_ids:
            validate_safe_id(shot_id, "shot id")
            path = root / "02_storyboard" / "shots" / shot_id / "shot.json"
            if not path.is_file():
                raise SystemExit(f"Unknown shot: {shot_id}")
            shot = read_json(path)
            if args.full:
                record = shot
            elif fields:
                record = {
                    "shot_id": shot_id,
                    "revision": int(shot.get("revision", 0)),
                    "fields": {field: value_at(shot, field) for field in fields},
                }
            else:
                record = {
                    "shot_id": shot_id,
                    "revision": int(shot.get("revision", 0)),
                    "client_shot_id": shot.get("client_shot_id", ""),
                    "story_requirement": shot.get("story_requirement", ""),
                    "status": shot.get("review", {}).get("status", ""),
                    "timing": shot.get("timing", {}),
                    "risk_tags": shot.get("risk_tags", []),
                    "asset_refs": shot.get("assets", {}).get("asset_refs", []),
                    "keyframe": shot.get("assets", {}).get("keyframe", ""),
                    "video": shot.get("assets", {}).get("video", ""),
                    "blocking_diagram_present": bool(str(shot.get("blocking_diagram", "")).strip()),
                    "prompt_version_count": len(shot.get("assets", {}).get("prompt_versions", [])),
                }
            records.append(record)
        output = {"project": str(root), "shots": records}
    else:
        payload = dashboard_payload(root)
        output = {
            "project": payload.get("project", {}),
            "summary": payload.get("summary", {}),
            "reference_library_revision": payload.get("reference_library_revision", 0),
            "shots": [
                {
                    "shot_id": shot.get("shot_id"),
                    "revision": shot.get("revision", 0),
                    "status": shot.get("status"),
                    "generation_seconds": shot.get("generation_seconds"),
                    "edit_use_seconds": shot.get("edit_use_seconds"),
                    "risk_tags": shot.get("risk_tags", []),
                    "keyframe_ready": bool(shot.get("keyframe")),
                    "video_ready": bool(shot.get("video")),
                    "blocking_diagram_present": bool(str(shot.get("blocking_diagram", "")).strip()),
                }
                for shot in payload.get("shots", [])
            ],
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def merge_mapping(target: dict, updates: dict, allowed: set[str]) -> list[str]:
    changed = []
    for key in sorted(allowed):
        if key in updates and target.get(key) != updates[key]:
            target[key] = updates[key]
            changed.append(key)
    return changed


def require_mapping(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def validate_board_payload(payload) -> dict:
    payload = require_mapping(payload, "payload")
    for name in ("editorial", "timing", "review"):
        if name in payload:
            require_mapping(payload[name], name)
    for group in (payload, payload.get("editorial", {}), payload.get("review", {})):
        for key, value in group.items():
            if key in {"annotations", "timing", "editorial", "review", "issues", "base_revision"}:
                continue
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{key} must be text")
            if isinstance(value, str) and len(value) > 100_000:
                raise ValueError(f"{key} is too long")
    for key, value in payload.get("timing", {}).items():
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0):
            raise ValueError(f"timing.{key} must be a finite non-negative number")
    annotations = payload.get("annotations")
    if annotations is not None:
        if not isinstance(annotations, list) or len(annotations) > 500:
            raise ValueError("annotations must be a list with at most 500 items")
        for item in annotations:
            if not isinstance(item, dict):
                raise ValueError("each annotation must be an object")
            if not isinstance(item.get("text", ""), str) or len(item.get("text", "")) > 10_000:
                raise ValueError("annotation text is invalid")
    base_revision = payload.get("base_revision")
    if base_revision is not None and (not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0):
        raise ValueError("base_revision must be a non-negative integer")
    return payload


def value_at(document: dict, dotted_path: str):
    value = document
    for part in dotted_path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return copy.deepcopy(value)


def update_shot_from_board(root: Path, shot_id: str, payload: dict) -> dict:
    validate_safe_id(shot_id, "shot id")
    payload = validate_board_payload(payload)
    path = root / "02_storyboard" / "shots" / shot_id / "shot.json"
    if not path.is_file():
        raise FileNotFoundError(shot_id)
    shot = read_json(path)
    before_document = copy.deepcopy(shot)
    current_revision = int(shot.get("revision", 0))
    base_revision = payload.get("base_revision")
    if base_revision is not None and base_revision != current_revision:
        raise RevisionConflict(f"This shot changed in another tab (current revision {current_revision}); reload before saving.")
    changed = []
    changed += merge_mapping(
        shot,
        payload,
        {"story_requirement", "production_adjustment", "blocking_diagram"},
    )
    editorial = shot.setdefault("editorial", {})
    changed += [f"editorial.{key}" for key in merge_mapping(
        editorial,
        payload.get("editorial", {}),
        {
            "client_script", "shot_script", "dialogue", "voiceover",
            "on_screen_text", "keyframe_prompt", "video_prompt",
            "negative_prompt", "post_production",
        },
    )]
    timing = shot.setdefault("timing", {})
    changed += [f"timing.{key}" for key in merge_mapping(
        timing,
        payload.get("timing", {}),
        {"client_reference_seconds", "generation_seconds", "edit_use_seconds"},
    )]
    review = shot.setdefault("review", {})
    review_updates = payload.get("review", {})
    if "status" in review_updates and review_updates["status"] not in SHOT_STATUSES:
        raise ValueError("Invalid review status")
    changed += [f"review.{key}" for key in merge_mapping(
        review,
        review_updates,
        {"status", "notes", "issues"},
    )]
    if "annotations" in payload:
        annotations = payload["annotations"]
        if shot.get("annotations", []) != annotations:
            shot["annotations"] = annotations
            changed.append("annotations")
    review["updated_at"] = now_iso()
    if changed:
        next_revision = current_revision + 1
        shot["revision"] = next_revision
        shot.setdefault("history", []).append({
            "at": now_iso(),
            "action": "board_update",
            "actor": payload.get("actor", "local-review-board"),
            "from_revision": current_revision,
            "revision": next_revision,
            "changed_fields": changed,
            "before": {key: value_at(before_document, key) for key in changed},
            "after": {key: value_at(shot, key) for key in changed},
        })
    write_json(path, shot)
    write_dashboard_files(root)
    return shot


def allowed_media_files(root: Path) -> set[Path]:
    candidates = []
    registry = read_json(root / "01_assets" / "asset-registry.json")
    candidates.extend(item.get("path", "") for item in registry.get("assets", []))
    reference_registry = load_reference_registry(root)
    candidates.extend(
        item.get("path", "")
        for item in reference_registry.get("references", [])
        if item.get("status", "active") == "active"
    )
    for _, shot in all_shots(root):
        assets = shot.get("assets", {})
        candidates.extend((assets.get("keyframe", ""), assets.get("video", "")))
    allowed = set()
    for value in candidates:
        if not value or Path(value).is_absolute():
            continue
        candidate = (root / value).resolve()
        if root in candidate.parents and candidate.suffix.lower() in MEDIA_SUFFIXES and candidate.is_file():
            allowed.add(candidate)
    return allowed


def request_content_length(handler: BaseHTTPRequestHandler, maximum: int, allow_empty: bool = False) -> int:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("invalid Content-Length") from exc
    if length < 0 or (not allow_empty and length == 0):
        raise ValueError("request body is empty")
    if length > maximum:
        raise OverflowError(f"request exceeds {maximum} bytes")
    return length


def parse_json_request(handler: BaseHTTPRequestHandler, maximum: int = MAX_BOARD_REQUEST_BYTES, allow_empty: bool = False) -> dict:
    length = request_content_length(handler, maximum, allow_empty=allow_empty)
    if length == 0:
        return {}
    if not handler.headers.get("Content-Type", "").lower().startswith("application/json"):
        raise TypeError("Content-Type must be application/json")
    return require_mapping(json.loads(handler.rfile.read(length) or b"{}"), "payload")


def parse_reference_multipart(handler: BaseHTTPRequestHandler) -> tuple[dict, bytes, str, str]:
    length = request_content_length(handler, MAX_REFERENCE_REQUEST_BYTES)
    content_type = handler.headers.get("Content-Type", "")
    if "\r" in content_type or "\n" in content_type or not content_type.lower().startswith("multipart/form-data"):
        raise TypeError("Content-Type must be multipart/form-data")
    body = handler.rfile.read(length)
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii", "strict") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise ValueError("invalid multipart upload")
    fields = {}
    file_value = None
    file_name = ""
    file_mime = ""
    part_count = 0
    for part in message.iter_parts():
        part_count += 1
        if part_count > 10:
            raise ValueError("multipart upload has too many fields")
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str) or not name:
            raise ValueError("multipart field is missing a name")
        value = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename is not None:
            if name != "file" or file_value is not None:
                raise ValueError("upload must contain exactly one file field")
            if len(value) > MAX_REFERENCE_IMAGE_BYTES:
                raise ValueError(f"reference image exceeds {MAX_REFERENCE_IMAGE_BYTES // (1024 * 1024)} MiB")
            file_value = value
            file_name = normalize_original_filename(filename)
            file_mime = part.get_content_type()
            continue
        if name not in {"category", "label", "note", "actor", "reference_id"}:
            raise ValueError(f"unsupported multipart field: {name}")
        if name in fields:
            raise ValueError(f"duplicate multipart field: {name}")
        if len(value) > 20_000:
            raise ValueError(f"multipart field is too large: {name}")
        charset = part.get_content_charset("utf-8")
        try:
            fields[name] = value.decode(charset)
        except (LookupError, UnicodeDecodeError) as exc:
            raise ValueError(f"multipart field is not valid text: {name}") from exc
    if file_value is None:
        raise ValueError("upload is missing the file field")
    if "category" not in fields:
        raise ValueError("upload is missing the category field")
    return fields, file_value, file_name, file_mime


def revision_from_request_path(path: str):
    values = parse_qs(urlparse(path).query).get("base_revision", [])
    if not values:
        return None
    if len(values) != 1 or not re.fullmatch(r"\d+", values[0]):
        raise ValueError("base_revision query must be a non-negative integer")
    return int(values[0])


def make_dashboard_handler(root: Path):
    dashboard_dir = root / "dashboard"
    update_lock = threading.Lock()

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "AIAdReviewBoard/1.0"

        def send_json(self, status: int, value) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def mutation_origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            return not origin or urlparse(origin).netloc == self.headers.get("Host", "")

        def send_mutation_error(self, exc: Exception, missing: str = "resource not found") -> None:
            if isinstance(exc, FileNotFoundError):
                self.send_json(404, {"ok": False, "error": missing})
            elif isinstance(exc, RevisionConflict):
                self.send_json(409, {"ok": False, "error": str(exc)})
            elif isinstance(exc, OverflowError):
                self.close_connection = True
                self.send_json(413, {"ok": False, "error": str(exc)})
            elif isinstance(exc, TypeError):
                self.send_json(415, {"ok": False, "error": str(exc)})
            else:
                self.send_json(400, {"ok": False, "error": str(exc)})

        def reference_response(self, reference: dict, status: int = 200) -> None:
            self.send_json(status, {
                "ok": True,
                "reference": reference,
                "reference_library_revision": int(load_reference_registry(root).get("revision", 0)),
            })

        def asset_response(self, asset: dict, status: int = 200) -> None:
            registry = read_json(root / "01_assets" / "asset-registry.json")
            self.send_json(status, {"ok": True, "asset": asset, "asset_library_revision": int(registry.get("revision", 0))})

        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/api/state":
                self.send_json(200, dashboard_payload(root))
                return
            if route == "/api/references":
                self.send_json(200, reference_library_payload(root))
                return
            if route == "/api/assets":
                registry = read_json(root / "01_assets" / "asset-registry.json")
                self.send_json(200, {"assets": registry.get("assets", []), "asset_library_revision": int(registry.get("revision", 0))})
                return
            if route.startswith("/files/"):
                relative = unquote(route.removeprefix("/files/"))
                candidate = (root / relative).resolve()
                if candidate not in allowed_media_files(root):
                    self.send_error(404)
                    return
                body = candidate.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            relative = "index.html" if route in {"", "/"} else unquote(route.lstrip("/"))
            candidate = (dashboard_dir / relative).resolve()
            if dashboard_dir.resolve() not in candidate.parents and candidate != dashboard_dir.resolve():
                self.send_error(403)
                return
            if not candidate.is_file():
                self.send_error(404)
                return
            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            route = urlparse(self.path).path
            upload = route == "/api/references"
            restore_match = re.fullmatch(r"/api/references/([A-Za-z0-9_-]+)/restore", route)
            if not upload and not restore_match:
                self.send_error(404)
                return
            if not self.mutation_origin_allowed():
                self.send_json(403, {"ok": False, "error": "cross-origin update rejected"})
                return
            try:
                if upload:
                    fields, value, filename, mime = parse_reference_multipart(self)
                    actor = normalize_reference_text(fields.get("actor", "local-review-board"), "actor", 200) or "local-review-board"
                    with update_lock:
                        reference = add_reference_bytes(
                            root,
                            value,
                            category=fields["category"],
                            label=fields.get("label", ""),
                            note=fields.get("note", ""),
                            original_name=filename,
                            claimed_mime=mime,
                            reference_id=fields.get("reference_id") or None,
                            actor=actor,
                        )
                        write_dashboard_files(root)
                    self.reference_response(reference, status=201)
                    return
                payload = parse_json_request(self, allow_empty=True)
                unknown = set(payload) - {"base_revision", "actor"}
                if unknown:
                    raise ValueError(f"unsupported restore fields: {', '.join(sorted(unknown))}")
                base_revision = payload.get("base_revision", revision_from_request_path(self.path))
                actor = payload.get("actor", "local-review-board")
                with update_lock:
                    reference = restore_reference(root, restore_match.group(1), base_revision=base_revision, actor=actor)
                    write_dashboard_files(root)
                self.reference_response(reference)
            except (FileNotFoundError, RevisionConflict, OverflowError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.send_mutation_error(exc, missing="reference not found")

        def do_PATCH(self):
            route = urlparse(self.path).path
            shot_match = re.fullmatch(r"/api/shots/([A-Za-z0-9_-]+)", route)
            reference_match = re.fullmatch(r"/api/references/([A-Za-z0-9_-]+)", route)
            asset_match = re.fullmatch(r"/api/assets/([A-Za-z0-9_-]+)", route)
            if not shot_match and not reference_match and not asset_match:
                self.send_error(404)
                return
            if not self.mutation_origin_allowed():
                self.send_json(403, {"ok": False, "error": "cross-origin update rejected"})
                return
            try:
                payload = parse_json_request(self)
                with update_lock:
                    if shot_match:
                        shot = update_shot_from_board(root, shot_match.group(1), payload)
                    elif asset_match:
                        asset = update_asset_from_board(root, asset_match.group(1), payload)
                    else:
                        reference = update_reference_metadata(root, reference_match.group(1), payload)
                        write_dashboard_files(root)
                if shot_match:
                    self.send_json(200, {"ok": True, "shot": shot})
                elif asset_match:
                    self.asset_response(asset)
                else:
                    self.reference_response(reference)
            except (FileNotFoundError, RevisionConflict, OverflowError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.send_mutation_error(exc, missing="shot not found" if shot_match else ("asset not found" if asset_match else "reference not found"))

        def do_DELETE(self):
            match = re.fullmatch(r"/api/references/([A-Za-z0-9_-]+)", urlparse(self.path).path)
            if not match:
                self.send_error(404)
                return
            if not self.mutation_origin_allowed():
                self.send_json(403, {"ok": False, "error": "cross-origin update rejected"})
                return
            try:
                payload = parse_json_request(self, allow_empty=True)
                unknown = set(payload) - {"base_revision", "actor"}
                if unknown:
                    raise ValueError(f"unsupported delete fields: {', '.join(sorted(unknown))}")
                base_revision = payload.get("base_revision", revision_from_request_path(self.path))
                actor = payload.get("actor", "local-review-board")
                with update_lock:
                    reference = delete_reference(root, match.group(1), base_revision=base_revision, actor=actor)
                    write_dashboard_files(root)
                self.reference_response(reference)
            except (FileNotFoundError, RevisionConflict, OverflowError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.send_mutation_error(exc, missing="reference not found")

        def log_message(self, format, *args):
            if getattr(self.server, "verbose", False):
                super().log_message(format, *args)

    return DashboardHandler


def serve_dashboard(args) -> int:
    root = Path(args.project).expanduser().resolve()
    require_project(root)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("The editable board may only bind to a loopback address.")
    write_dashboard_files(root)
    server = ThreadingHTTPServer((args.host, args.port), make_dashboard_handler(root))
    server.verbose = args.verbose
    address, port = server.server_address[:2]
    print(f"http://{address}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
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
    init.add_argument("--aspect-ratio", default="16:9")
    init.add_argument("--resolution", default="1280x720")
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

    reference = sub.add_parser("add-reference", help="Import a project-level style or character reference image")
    reference.add_argument("--project", required=True)
    reference.add_argument("--category", required=True, choices=sorted(REFERENCE_CATEGORIES))
    reference.add_argument("--file", required=True)
    reference.add_argument("--label", default="")
    reference.add_argument("--note", default="")
    reference.add_argument("--reference-id")
    reference.set_defaults(func=add_reference)

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

    media = sub.add_parser("set-shot-media", help="Attach a project-local keyframe or video to a shot")
    media.add_argument("--project", required=True)
    media.add_argument("--shot-id", required=True)
    media.add_argument("--kind", required=True, choices=["keyframe", "video"])
    media.add_argument("--file", required=True)
    media.add_argument("--status", choices=sorted(SHOT_STATUSES))
    media.add_argument("--actor", default="local-production-manager")
    media.set_defaults(func=set_shot_media)

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

    inspect = sub.add_parser("inspect", help="Read a compact project overview or selected shot fields")
    inspect.add_argument("--project", required=True)
    inspect.add_argument("--shot-id", action="append", default=[])
    inspect.add_argument("--field", action="append", default=[])
    inspect.add_argument("--full", action="store_true")
    inspect.set_defaults(func=inspect_project)

    serve = sub.add_parser("serve-dashboard", help="Open a local editable storyboard review board")
    serve.add_argument("--project", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--verbose", action="store_true")
    serve.set_defaults(func=serve_dashboard)

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
