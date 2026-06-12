# Configuration

This skill is public-repo safe. It must not store private Lark/Feishu URLs, Wiki tokens, local absolute paths, app secrets, access tokens, or user IDs.

The skill intentionally depends on `lark-cli`. Treat it as a personal workflow layer that teaches an agent how to apply `lark-cli` safely and repeatably for this sync task, not as a replacement CLI or SDK.

## Runtime Inputs

Use one of these for the parent Wiki node:

```bash
export LARK_DATA_WIKI_PARENT="https://example.feishu.cn/wiki/REPLACE_WITH_PARENT_NODE"
```

Optional:

```bash
export LARK_DATA_WIKI_SPACE_ID="REPLACE_WITH_SPACE_ID"
export LARK_CLI_BIN="lark-cli"
export LARK_CLI_IDENTITY="auto"
```

Prefer passing `--parent-wiki` in the user task or command when multiple Data Wiki parents are in use.

## Required Tools

- `lark-cli` available on `PATH`, or set `LARK_CLI_BIN`.
- `lark-cli config show` succeeds without printing secrets.
- `lark-cli auth status --verify` succeeds for the identity that can edit the target Wiki parent.

## Required Permissions

The exact scope names can vary by tenant/app setup, but this workflow needs:

- Read parent Wiki node metadata.
- Retrieve/list child Wiki nodes.
- Create Wiki nodes.
- Edit docx document content.

Typical scope set:

```bash
lark-cli auth login --scope "wiki:node:read wiki:node:retrieve wiki:node:create docx:document:write_only docx:document:readonly"
```

API scopes are not enough by themselves. The calling user or app must also have container edit permission on the parent Wiki node and edit permission on an existing child doc when updating.

## Common Failures

- `permission denied` on Wiki create: missing parent-node container edit permission or Wiki node create scope.
- `permission denied` on document update: missing docx write permission or page edit access.
- `keychain entry not found`: local `lark-cli` app config is incomplete. Prefer raw `lark-cli api` calls for Wiki node creation and verify `lark-cli doctor`.
- Search returns nothing for long titles: do not rely on search for duplicate checks; list target parent children instead.
