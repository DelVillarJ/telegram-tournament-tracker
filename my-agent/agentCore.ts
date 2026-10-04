import { ollamaStream, OllamaMessage } from './ollamaClient';
import { runTool, ToolResult } from './tools';

export type AgentEvent =
  | { type: 'status'; text: string }
  | { type: 'user'; text: string }
  | { type: 'model'; text: string }
  | { type: 'tool'; text: string }
  | { type: 'error'; text: string };

export type AgentSink = (event: AgentEvent) => void;

export class OllamaAgent {
  private messages: OllamaMessage[] = [];
  private sink: AgentSink;
  private model = 'qwen3.5:9b';

  constructor(sink: AgentSink) {
    this.sink = sink;
    this.messages.push({
      role: 'system',
      content: [
        'You are a VS Code AI agent.',
        'You can call tools using a JSON block like:',
        '{"tool":"powershell","args":{"command":"dir"}}',
        'or {"tool":"http_get","args":{"url":"https://topdeck.gg/docs/tournaments-v2"}}',
        'After tools run, you will see their output and must continue reasoning.'
      ].join('\n')
    });
  }

  async handleUserInput(input: string) {
    this.sink({ type: 'user', text: input });
    this.messages.push({ role: 'user', content: input });

    let fullReply = '';

    try {
      await ollamaStream(this.model, this.messages, (chunk) => {
        fullReply += chunk;
        this.sink({ type: 'model', text: chunk });
      });

      this.messages.push({ role: 'assistant', content: fullReply });

      const toolCall = this.tryParseTool(fullReply);
      if (toolCall) {
        const { name, args } = toolCall;
        this.sink({
          type: 'tool',
          text: `Calling tool: ${name} with args: ${JSON.stringify(args)}`
        });

        const result: ToolResult = await runTool(name, args);
        this.sink({
          type: 'tool',
          text: `Tool ${result.name} output:\n${result.output}`
        });

        this.messages.push({ role: 'tool', content: result.output });

        let followUp = '';
        await ollamaStream(this.model, this.messages, (chunk) => {
          followUp += chunk;
          this.sink({ type: 'model', text: chunk });
        });

        this.messages.push({ role: 'assistant', content: followUp });
      }
    } catch (err: any) {
      this.sink({ type: 'error', text: `Agent error: ${err.message}` });
    }
  }

  private tryParseTool(reply: string): { name: string; args: any } | null {
    const start = reply.indexOf('{');
    const end = reply.lastIndexOf('}');
    if (start === -1 || end === -1 || end <= start) return null;

    try {
      const json = JSON.parse(reply.slice(start, end + 1));
      if (json.tool && json.args) {
        return { name: json.tool, args: json.args };
      }
    } catch {
      return null;
    }
    return null;
  }
}
