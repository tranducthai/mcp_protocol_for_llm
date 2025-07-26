# 🧪 MCP Server for Claude Desktop

This guide shows you how to use your Model Context Protocol (MCP) server using Claude for Desktop.

<a href="https://glama.ai/mcp/servers/@tranducthai/mcp_protocol_weather">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@tranducthai/mcp_protocol_weather/badge" alt="Weather SSE Server MCP server" />
</a>

## 1. Requirements

- Claude/Cursor for Desktop (Windows or macOS)
- MCP server script (e.g., `weather.py`,'map.py') running via `uv run weather.py`

## 2. Configure Claude to Launch the MCP Server

Create or edit the Claude config file:

- **macOS/Linux**: `~/.config/claude/claude_desktop_config.json` or `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Example content:

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather",
        "run",
        "weather.py"
      ]
    }
  }
}
```

Replace `/ABSOLUTE/PATH/...` with the actual absolute path to the folder containing `weather.py`.

## 3. Restart Claude

Close and reopen Claude for Desktop. If configured correctly, a tool icon will appear at the bottom-left of the chat window.

## 4. Test Your Tool

Click the **tool icon** to see your MCP server tools like `search-location` and `get-forecast`.

Try prompts such as:

```
What’s the weather in Vinh, VietNam?
Find the restaurant near Ho Guom ?
```

Claude should use your local server to respond.

## 5. Troubleshooting

If you don’t see your server or tool in Claude:

### Check config

- Ensure JSON syntax is valid.
- Use absolute paths, not relative ones.

### Check logs

Logs may be found in:

- **macOS/Linux**: `~/Library/Logs/Claude/mcp.log`
- **Windows**: `%APPDATA%\Claude\Logs\mcp.log`

You can tail logs like this (macOS/Linux):

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```

### Manually test server

Run:

```bash
uv --directory /ABSOLUTE/PATH/... run weather.py
```

## ✅ Success

If you see your tool in Claude and prompts generate valid responses, the integration is complete!