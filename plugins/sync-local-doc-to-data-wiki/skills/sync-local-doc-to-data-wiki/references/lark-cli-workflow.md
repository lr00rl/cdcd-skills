# Lark CLI Workflow

Use this reference when the script cannot be used or when debugging a failed sync.

## Resolve The Parent Wiki Node

Extract the token from `/wiki/<token>` and resolve it before using it:

```bash
lark-cli wiki spaces get_node \
  --params '{"token":"PARENT_WIKI_TOKEN"}' \
  --format json
```

Read:

- `data.node.node_token`: parent Wiki node token.
- `data.node.space_id`: Wiki space ID.
- `data.node.title`: parent title for verification.
- `data.node.obj_token`: underlying doc token; do not use this as the parent node token.

## List Child Nodes

```bash
lark-cli api GET /open-apis/wiki/v2/spaces/SPACE_ID/nodes \
  --params '{"parent_node_token":"PARENT_WIKI_TOKEN","page_size":50}' \
  --format json
```

Page through `data.page_token` while `data.has_more` is true. Match duplicate candidates by exact `title` and `parent_node_token`.

## Create A Child Docx Node

Prefer Wiki node creation over `docs +create --wiki-node` when CLI configuration is unreliable.

```bash
lark-cli api POST /open-apis/wiki/v2/spaces/SPACE_ID/nodes \
  --data '{"obj_type":"docx","parent_node_token":"PARENT_WIKI_TOKEN","node_type":"origin","title":"TITLE"}' \
  --format json
```

Read:

- `data.node.node_token`: new Wiki token.
- `data.node.obj_token`: docx document token.
- `data.node.url`: final page URL when returned.

## Write Markdown Content

For a new node or an exact target node:

```bash
lark-cli docs +update \
  --doc "WIKI_NODE_TOKEN_OR_URL" \
  --mode overwrite \
  --markdown "$NORMALIZED_MARKDOWN"
```

Do not prepend an H1 that repeats the document title. Keep source headings as real Markdown headings.

## Verify

```bash
lark-cli docs +fetch --doc "WIKI_NODE_TOKEN_OR_URL" --format json
lark-cli wiki spaces get_node --params '{"token":"WIKI_NODE_TOKEN"}' --format json
```

Verification passes when:

- The fetched title matches the intended title.
- The fetched Markdown contains expected headings/content.
- `get_node` shows the expected `parent_node_token` and `space_id`.
