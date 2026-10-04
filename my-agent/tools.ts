import { exec } from 'child_process';
import fetch from 'node-fetch';
import * as fs from 'fs';
import * as path from 'path';

export type ToolResult = { name: string; output: string };

export function runPowerShellTool(command: string): Promise<ToolResult> {
  return new Promise((resolve) => {
    exec(`powershell -Command "${command}"`, (err, stdout, stderr) => {
      if (err) {
        resolve({ name: 'powershell', output: stderr || err.message });
      } else {
        resolve({ name: 'powershell', output: stdout });
      }
    });
  });
}

export async function runHttpGetTool(url: string): Promise<ToolResult> {
  try {
    const res = await fetch(url);
    const text = await res.text();
    return { name: 'http_get', output: text.slice(0, 4000) };
  } catch (e: any) {
    return { name: 'http_get', output: e.message };
  }
}

export function runListFilesTool(p: string): ToolResult {
  try {
    const files = fs.readdirSync(p).map(f => path.join(p, f)).join('\n');
    return { name: 'list_files', output: files };
  } catch (e: any) {
    return { name: 'list_files', output: e.message };
  }
}

export async function runTool(name: string, args: any): Promise<ToolResult> {
  switch (name) {
    case 'powershell':
      return runPowerShellTool(args.command);
    case 'http_get':
      return runHttpGetTool(args.url);
    case 'list_files':
      return runListFilesTool(args.path);
    default:
      return { name, output: `Unknown tool: ${name}` };
  }
}
