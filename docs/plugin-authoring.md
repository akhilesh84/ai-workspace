# Plugin Authoring Guide

A plugin is a self-contained bundle: one agent + its private skills + its MCP config.

## Structure

```
plugins/<plugin-name>/
├── latest -> v1/          ← symlink to current stable version
└── v1/
    ├── plugin.json        ← metadata
    ├── AGENT.md           ← agent persona, behavior, skill/MCP references
    ├── system_prompt.md   ← injected into any AI client
    ├── mcp_config.json    ← wires MCP servers for this plugin
    └── skills/
        └── <skill-name>/
            ├── latest -> v1/
            └── v1/
                ├── SKILL.md
                ├── scripts/
                └── references/
```

## Step-by-Step

### 1. Copy the template
```bash
cp -r plugins/_template/v1 plugins/<my-plugin>/v1
cd plugins/<my-plugin>
ln -s v1 latest
```

### 2. Fill in `plugin.json`
Update `name`, `description`, `skills`, and `mcp_servers`.

### 3. Write `AGENT.md`
Define the agent's role, the skills it uses, and the MCP tools available.

### 4. Write `system_prompt.md`
This is the system prompt injected into the AI client. Keep it concise and behavioral.

### 5. Configure `mcp_config.json`
Point to shared servers in `../../mcp-servers/<server>/latest` or external URLs.

### 6. Add your skills
```bash
mkdir -p skills/<skill-name>/v1/{scripts,references,examples}
ln -s v1 skills/<skill-name>/latest
# Write SKILL.md with YAML frontmatter
```

### 7. Version bump (when breaking changes needed)
```bash
cp -r v1 v2
# make changes in v2/
ln -sfn v2 ../latest
```

## Referencing Shared Resources

Plugins can reference top-level shared skills or servers using relative paths:
- `../../../../skills/<skill-name>/latest` — shared skill
- `../../../../mcp-servers/<server-name>/latest` — shared MCP server
