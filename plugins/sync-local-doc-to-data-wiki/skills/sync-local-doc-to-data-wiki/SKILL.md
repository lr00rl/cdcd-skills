---
name: sync-local-doc-to-data-wiki
description: Use when a local Markdown or text document should be synchronized into a configured Lark/Feishu Wiki directory through lark-cli, especially recurring Data-team requirement/TODO docs. Use for personal create, update, or upsert publishing workflows that need Markdown formatting preservation and no hardcoded wiki tokens.
---

# Sync Local Doc To Data Wiki

## Overview

Publish a local Markdown document into a configured Lark/Feishu Wiki parent node as a child docx page through `lark-cli`. This skill is a compact personal workflow guide for using `lark-cli` consistently; it is not a replacement for `lark-cli`, the Lark OpenAPI, or the existing `lark-*` skills.

## Required Inputs

- A local Markdown/text file path.
- A target parent Wiki URL or node token from the user, `--parent-wiki`, `LARK_DATA_WIKI_PARENT`, or Claude plugin config.
- A title, or default to the local file stem.
- A mode: `upsert` by default, `create` to fail if the page exists, or `update` to fail if it does not.
- A working `lark-cli` installation with auth and resource permissions for the target Wiki parent.

If configuration or permissions are unclear, read `references/configuration.md`.

## Standard Workflow

1. Confirm the target is a Wiki parent directory, not a docx token. Resolve `/wiki/<token>` with `wiki spaces get_node`; never treat a Wiki URL token as a docx token without resolving it.
2. Check existing child nodes under the parent by listing Wiki children. Do not use keyword search as the primary duplicate check; Lark search has short query limits and may search outside the target directory.
3. Normalize Markdown before publishing:
   - Convert CRLF to LF.
   - Trim leading/trailing whitespace.
   - Collapse excessive blank lines.
   - Remove a leading H1 only when it exactly duplicates the document title.
   - Do not add a manual table of contents; Lark generates one.
4. Create or update the child docx:
   - Create: call Wiki node creation under the parent, then overwrite the new page with Markdown.
   - Update: overwrite the existing child page.
   - Upsert: update if an exact title match exists, otherwise create.
5. Verify by fetching the created/updated page and resolving the new Wiki node. Report the final Wiki URL, title, action, and verification evidence.

## Preferred Script

Use the bundled script when deterministic repetition is useful. The script is a thin orchestrator over `lark-cli`; if it gets in the way, follow the workflow manually with `lark-cli`.

```bash
python3 scripts/sync_local_doc_to_lark_wiki.py \
  /path/to/local-doc.md \
  --parent-wiki "$LARK_DATA_WIKI_PARENT" \
  --mode upsert
```

Useful options:

- `--title "..."` overrides the file-stem title.
- `--mode create|update|upsert` controls duplicate behavior.
- `--space-id "..."` skips parent-node space discovery when already known.
- `--identity user|bot|auto` passes identity only when a non-auto value is required.
- `--dry-run` resolves and plans but does not create/update.

When installed as a Claude Code plugin, the script also accepts Claude plugin `userConfig` values exported as `CLAUDE_PLUGIN_OPTION_*` environment variables. Prefer explicit CLI arguments or `LARK_*` environment variables when a session uses multiple Wiki parents.

If the script fails because of unsupported CLI behavior, read `references/lark-cli-workflow.md` and perform the same API calls manually with `lark-cli`.

## Safety Rules

- Never commit real Wiki URLs, node tokens, local user paths, Open IDs, app IDs, app secrets, or access tokens into this skill or any public repo.
- Treat `overwrite` as safe only for a newly created page or an exact-title child page selected by the user/target directory.
- If multiple child pages have the same title, stop and ask for the exact target node unless the user already provided one.
- Do not delete old Wiki pages as part of sync. If cleanup is requested, make it a separate explicit task.
- If permission errors occur, report whether the missing layer is API scope, user auth, parent-node container edit permission, or docx edit permission when the error makes that clear.

## Verification

After publishing:

- Run `lark-cli docs +fetch --doc <wiki-url>` or let the script fetch when extended to do so.
- Confirm the title and expected Markdown headings exist.
- Confirm `wiki spaces get_node` shows `parent_node_token` equal to the intended parent.
- Final response must include the created/updated Wiki URL and whether the operation was `created`, `updated`, or `dry-run`.
