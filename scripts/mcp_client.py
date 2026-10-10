"""Small standard-library MCP HTTP client for reproducible integration tests.

Uses Epic's existing transport. This is a test client, not an MCP server.
"""
import argparse
import json
import urllib.request
from pathlib import Path


class Client:
    def __init__(self, url="http://127.0.0.1:8000/mcp"):
        self.url, self.session, self.counter = url, None, 0
        self.protocol = "2025-11-25"
        initial = self.rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {}, "clientInfo": {"name": "AmineAcceptance", "version": "0.1.0"}})
        self.protocol = initial["protocolVersion"]
        self.rpc("notifications/initialized", {}, notification=True)

    def rpc(self, method, params=None, notification=False):
        self.counter += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notification:
            body["id"] = self.counter
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": self.protocol}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=55) as response:
            self.session = response.headers.get("Mcp-Session-Id", self.session)
            data = response.read().decode()
        if not data:
            return {}
        if data.startswith("event:") or data.startswith("data:"):
            events = [json.loads(line[5:].strip()) for line in data.splitlines() if line.startswith("data:") and line[5:].strip()]
            data = json.dumps(next(event for event in events if event.get("id") == body.get("id")))
        result = json.loads(data)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result.get("result", {})

    def call(self, name, arguments=None):
        return self.rpc("tools/call", {"name": name, "arguments": arguments or {}})

    def tool(self, toolset, name, arguments=None):
        return self.call("call_tool", {"toolset_name": toolset, "tool_name": name, "arguments": arguments or {}})


def text_result(result):
    return [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("method", nargs="?", default="tools/list")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = Client().rpc(args.method, json.loads(args.params))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
