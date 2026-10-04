import * as vscode from 'vscode';
import { OllamaAgent, AgentEvent } from './agentCore';
import { exec } from 'child_process';

let panel: vscode.WebviewPanel | undefined;
let agent: OllamaAgent | undefined;
let statusTimer: NodeJS.Timeout | undefined;

import { runPowerShellTool, runHttpGetTool, runListFilesTool } from './tools';

export function activate(context: vscode.ExtensionContext) {
  const api = vscode.extensions.getExtension("github.copilot")?.exports;

  if (api?.registerTool) {
    api.registerTool({
      name: "powershell.run",
      execute: async (args: any) => {
        return await runPowerShellTool(args.command);
      }
    });

    api.registerTool({
      name: "http.get",
      execute: async (args: any) => {
        return await runHttpGetTool(args.url);
      }
    });

    api.registerTool({
      name: "fs.list",
      execute: async (args: any) => {
        return runListFilesTool(args.path);
      }
    });
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('ollamaAgent.start', () => startAgent()),
    vscode.commands.registerCommand('ollamaAgent.stop', () => stopAgent())
  );
}

export function deactivate() {
  stopAgent();
}

function startAgent() {
  if (panel) {
    vscode.window.showInformationMessage('Ollama agent already running.');
    return;
  }

  panel = vscode.window.createWebviewPanel(
    'ollamaAgentDashboard',
    'Ollama Agent Dashboard',
    vscode.ViewColumn.Beside,
    { enableScripts: true }
  );

  panel.webview.html = getHtml();

  agent = new OllamaAgent((event: AgentEvent) => {
    if (panel) panel.webview.postMessage(event);
  });

  panel.onDidDispose(() => {
    panel = undefined;
    agent = undefined;
    if (statusTimer) clearInterval(statusTimer);
  });

  panel.webview.onDidReceiveMessage(async (msg) => {
    if (!agent) return;
    if (msg.type === 'user') {
      await agent.handleUserInput(msg.text);
    }
  });

  if (agent) {
    agent.handleUserInput('Agent session started. Describe your environment.');
  }

  statusTimer = setInterval(() => pollOllamaStatus(), 3000);
}

function stopAgent() {
  if (panel) {
    panel.dispose();
    panel = undefined;
  }
  agent = undefined;
  if (statusTimer) clearInterval(statusTimer);
}

function pollOllamaStatus() {
  if (!panel) return;
  exec('ollama ps', (err, stdout, stderr) => {
    if (err) {
      panel?.webview.postMessage({
        type: 'status',
        text: `ollama ps error: ${stderr || err.message}`
      });
    } else {
      panel?.webview.postMessage({
        type: 'status',
        text: `ollama ps:\n${stdout}`
      });
    }
  });
}

function getHtml(): string {
  return `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { background:#1e1e1e; color:#e5e5e5; font-family:system-ui; padding:10px; }
  #log { height:400px; overflow-y:auto; background:#111; padding:8px; border:1px solid #333; font-size:12px; white-space:pre-wrap; }
  .status { color:#9cdcfe; }
  .user { color:#4fc1ff; }
  .model { color:#c586c0; }
  .tool { color:#b5cea8; }
  .error { color:#f44747; }
  #row { margin-top:10px; display:flex; gap:6px; }
  #input { flex:1; background:#252526; border:1px solid #3c3c3c; color:#e5e5e5; padding:6px; }
  button { background:#0e639c; color:white; border:none; padding:6px 12px; cursor:pointer; }
</style>
</head>
<body>
<h3>Ollama Agent Activity</h3>
<div id="log"></div>
<div id="row">
  <input id="input" placeholder="Ask the agent..." />
  <button id="send">Send</button>
</div>
<script>
  const vscode = acquireVsCodeApi();
  const logEl = document.getElementById('log');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send');

  window.addEventListener('message', (event) => {
    const msg = event.data;
    const div = document.createElement('div');
    div.className = msg.type;
    div.textContent = '[' + msg.type.toUpperCase() + '] ' + msg.text;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  });

  sendBtn.onclick = () => {
    const text = inputEl.value.trim();
    if (!text) return;
    vscode.postMessage({ type: 'user', text });
    inputEl.value = '';
  };

  inputEl.onkeydown = (e) => {
    if (e.key === 'Enter') sendBtn.click();
  };
</script>
</body>
</html>
`;
}
