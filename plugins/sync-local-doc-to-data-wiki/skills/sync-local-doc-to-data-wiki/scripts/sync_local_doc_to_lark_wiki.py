#!/usr/bin/env python3
"""Sync a local Markdown document into a Lark/Feishu Wiki child page."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


class SyncError(RuntimeError):
    pass


def main() -> int:
    args = parse_args()
    lark = args.lark_cli or config_value("LARK_CLI_BIN", "lark_cli_bin") or "lark-cli"
    parent = args.parent_wiki or config_value("LARK_DATA_WIKI_PARENT", "data_wiki_parent")
    if not parent:
        raise SyncError("missing --parent-wiki, LARK_DATA_WIKI_PARENT, or Claude plugin data_wiki_parent config")

    markdown_path = Path(args.markdown_file).expanduser()
    if not markdown_path.is_file():
        raise SyncError(f"markdown file not found: {markdown_path}")

    title = args.title or markdown_path.stem
    markdown = normalize_markdown(markdown_path.read_text(encoding="utf-8"), title)
    parent_token = extract_wiki_token(parent)
    identity = None if args.identity == "auto" else args.identity

    parent_node = get_wiki_node(lark, parent_token, identity)
    space_id = args.space_id or config_value("LARK_DATA_WIKI_SPACE_ID", "data_wiki_space_id") or parent_node["space_id"]
    children = list_children(lark, space_id, parent_node["node_token"], identity)
    matches = [node for node in children if node.get("title") == title and node.get("obj_type") == "docx"]

    if len(matches) > 1:
        urls = [node.get("url") or node.get("node_token") for node in matches]
        raise SyncError(f"multiple child docx pages have title {title!r}: {urls}")

    planned_action = "update" if matches else "create"
    if args.mode == "create" and matches:
        raise SyncError(f"page already exists under parent: {matches[0].get('url') or matches[0].get('node_token')}")
    if args.mode == "update" and not matches:
        raise SyncError(f"page does not exist under parent: {title}")

    if args.dry_run:
        result = {
            "ok": True,
            "action": f"dry-run-{planned_action}",
            "title": title,
            "parent_title": parent_node.get("title"),
            "existing_url": matches[0].get("url") if matches else None,
            "markdown_bytes": len(markdown.encode("utf-8")),
        }
        add_private_details(
            result,
            args.show_tokens,
            parent_node_token=parent_node["node_token"],
            space_id=space_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if matches:
        target = matches[0]
        update_markdown(lark, target.get("url") or target["node_token"], markdown, identity)
        result_node = get_wiki_node(lark, target["node_token"], identity)
        action = "updated"
    else:
        created = create_child_docx(lark, space_id, parent_node["node_token"], title, identity)
        target = created
        update_markdown(lark, target.get("url") or target["node_token"], markdown, identity)
        result_node = get_wiki_node(lark, target["node_token"], identity)
        action = "created"

    result = {
        "ok": True,
        "action": action,
        "title": title,
        "url": target.get("url") or f"https://<tenant>.feishu.cn/wiki/{target['node_token']}",
        "markdown_bytes": len(markdown.encode("utf-8")),
    }
    add_private_details(
        result,
        args.show_tokens,
        node_token=target["node_token"],
        obj_token=target.get("obj_token"),
        parent_node_token=result_node.get("parent_node_token"),
        space_id=result_node.get("space_id"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown_file", help="Local Markdown/text file to publish")
    parser.add_argument("--parent-wiki", help="Parent Wiki URL or node token")
    parser.add_argument("--title", help="Child page title. Defaults to file stem")
    parser.add_argument("--mode", choices=("upsert", "create", "update"), default="upsert")
    parser.add_argument("--space-id", help="Wiki space ID. Defaults to parent get_node result or LARK_DATA_WIKI_SPACE_ID")
    parser.add_argument(
        "--identity",
        choices=("auto", "user", "bot"),
        default=config_value("LARK_CLI_IDENTITY", "lark_cli_identity") or "auto",
    )
    parser.add_argument("--lark-cli", help="Path to lark-cli binary")
    parser.add_argument("--dry-run", action="store_true", help="Resolve and plan without creating/updating")
    parser.add_argument("--show-tokens", action="store_true", help="Include raw Wiki/doc tokens in JSON output")
    return parser.parse_args()


def config_value(env_name: str, plugin_key: str) -> str | None:
    for key in (
        env_name,
        f"CLAUDE_PLUGIN_OPTION_{plugin_key}",
        f"CLAUDE_PLUGIN_OPTION_{plugin_key.upper()}",
    ):
        value = os.environ.get(key)
        if value:
            return value
    return None


def normalize_markdown(markdown: str, title: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    first_heading = re.match(r"^#\s+(.+?)\s*(?:\n|$)", text)
    if first_heading and first_heading.group(1).strip() == title:
        text = text[first_heading.end() :].lstrip()
    return text + "\n"


def extract_wiki_token(value: str) -> str:
    match = re.search(r"/wiki/([^/?#]+)", value)
    if match:
        return match.group(1)
    token = value.strip()
    if not token:
        raise SyncError("empty Wiki token")
    return token


def get_wiki_node(lark: str, token: str, identity: str | None) -> dict[str, Any]:
    payload = run_json(
        [lark, "wiki", "spaces", "get_node", "--params", json.dumps({"token": token}), "--format", "json"]
        + identity_args(identity)
    )
    node = payload.get("data", {}).get("node")
    if not isinstance(node, dict):
        raise SyncError(f"unexpected get_node response for {token}: {payload}")
    return node


def list_children(lark: str, space_id: str, parent_token: str, identity: str | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"parent_node_token": parent_token, "page_size": 50}
        if page_token:
            params["page_token"] = page_token
        payload = run_json(
            [lark, "api", "GET", f"/open-apis/wiki/v2/spaces/{space_id}/nodes", "--params", json.dumps(params), "--format", "json"]
            + identity_args(identity)
        )
        data = payload.get("data", {})
        batch = data.get("items", [])
        if not isinstance(batch, list):
            raise SyncError(f"unexpected child list response: {payload}")
        items.extend(node for node in batch if isinstance(node, dict))
        if not data.get("has_more"):
            return items
        page_token = data.get("page_token")
        if not page_token:
            raise SyncError("child list reported has_more without page_token")


def create_child_docx(lark: str, space_id: str, parent_token: str, title: str, identity: str | None) -> dict[str, Any]:
    data = {
        "obj_type": "docx",
        "parent_node_token": parent_token,
        "node_type": "origin",
        "title": title,
    }
    payload = run_json(
        [lark, "api", "POST", f"/open-apis/wiki/v2/spaces/{space_id}/nodes", "--data", json.dumps(data), "--format", "json"]
        + identity_args(identity)
    )
    node = payload.get("data", {}).get("node")
    if not isinstance(node, dict) or not node.get("node_token"):
        raise SyncError(f"unexpected create response: {payload}")
    return node


def update_markdown(lark: str, doc_ref: str, markdown: str, identity: str | None) -> None:
    payload = run_json(
        [lark, "docs", "+update", "--doc", doc_ref, "--mode", "overwrite", "--markdown", markdown]
        + identity_args(identity)
    )
    if payload.get("ok") is False or payload.get("code") not in (None, 0):
        raise SyncError(f"update failed: {payload}")


def identity_args(identity: str | None) -> list[str]:
    return ["--as", identity] if identity else []


def add_private_details(result: dict[str, Any], show_tokens: bool, **values: Any) -> None:
    if show_tokens:
        result.update(values)
        return
    redacted = {key: redact(value) for key, value in values.items() if value}
    if redacted:
        result["private_details_redacted"] = redacted


def redact(value: Any) -> str:
    text = str(value)
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def run_json(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        command_text = shlex.join(command)
        raise SyncError(
            f"command failed ({proc.returncode}): {command_text}\n"
            f"stdout: {proc.stdout.strip()}\n"
            f"stderr: {proc.stderr.strip()}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SyncError(f"command returned non-JSON output: {proc.stdout[:500]}") from exc
    if payload.get("code") not in (None, 0):
        raise SyncError(f"Lark API error: {json.dumps(payload, ensure_ascii=False)}")
    return payload


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
