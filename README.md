# cdcd-skills

Public agent skills and Codex plugin packages maintained by cdcd.

This repository is intentionally sanitized. It does not contain private Lark/Feishu Wiki URLs, Wiki tokens, local filesystem paths, app secrets, access tokens, Open IDs, or tenant-specific identifiers.

## Included Plugins

### `sync-local-doc-to-data-wiki`

Publishes a local Markdown document into a configured Lark/Feishu Wiki parent node as a child docx page through `lark-cli`. This is a compact personal development workflow for the recurring Data Wiki sync pattern, not a replacement for `lark-cli` or Lark OpenAPI tooling.

Path:

```text
plugins/sync-local-doc-to-data-wiki
```

## Configure Runtime Secrets Locally

Set the target Wiki parent at runtime, not in this repository:

```bash
export LARK_DATA_WIKI_PARENT="https://example.feishu.cn/wiki/REPLACE_WITH_PARENT_NODE"
```

Optional:

```bash
export LARK_DATA_WIKI_SPACE_ID="REPLACE_WITH_SPACE_ID"
export LARK_CLI_IDENTITY="auto"
export LARK_CLI_BIN="lark-cli"
```

The local machine must have `lark-cli` configured and authenticated for the target Wiki parent. Keep `lark-cli` as the source of truth for auth, permissions, and API behavior; this project only records the repeatable agent workflow around it.

## Install For Codex As A Marketplace

This repo includes a Codex marketplace file at `.agents/plugins/marketplace.json`.

From Codex:

```bash
codex plugin marketplace add lr00rl/cdcd-skills
```

For local development:

```bash
codex plugin marketplace add /path/to/cdcd-skills
```

Restart Codex after adding or refreshing the marketplace, then install `sync-local-doc-to-data-wiki` from the plugin browser.

## Install As A Direct Codex Skill

Direct skill folders are useful for local development:

```bash
mkdir -p ~/.agents/skills
cp -R plugins/sync-local-doc-to-data-wiki/skills/sync-local-doc-to-data-wiki ~/.agents/skills/
```

Restart Codex if the skill does not appear.

## Install For Claude

Claude Code can use the same Agent Skills folder:

```bash
mkdir -p ~/.claude/skills
cp -R plugins/sync-local-doc-to-data-wiki/skills/sync-local-doc-to-data-wiki ~/.claude/skills/
```

Then ask Claude to use `sync-local-doc-to-data-wiki`.

## Example Usage

```text
Use $sync-local-doc-to-data-wiki to sync /path/to/requirement.md into the configured Data Wiki parent.
```

Or run the helper directly from the skill directory:

```bash
python3 plugins/sync-local-doc-to-data-wiki/skills/sync-local-doc-to-data-wiki/scripts/sync_local_doc_to_lark_wiki.py \
  /path/to/requirement.md \
  --parent-wiki "$LARK_DATA_WIKI_PARENT" \
  --mode upsert
```

## Publishing Notes

- Keep tenant-specific configuration in environment variables or user prompts.
- Do not add real Wiki URLs or tokens to examples, tests, docs, screenshots, or commit messages.
- Prefer adding new reusable workflows as separate plugins under `plugins/`.
