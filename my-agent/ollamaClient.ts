import fetch from 'node-fetch';

export interface OllamaMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
}

export async function ollamaChat(
  model: string,
  messages: OllamaMessage[]
): Promise<string> {
  const res = await fetch('http://127.0.0.1:11434/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages,
      stream: false
    })
  });

  const data = await res.json();
  return data?.message?.content ?? JSON.stringify(data, null, 2);
}

export async function ollamaStream(
  model: string,
  messages: OllamaMessage[],
  onChunk: (text: string) => void
): Promise<void> {
  const res = await fetch('http://127.0.0.1:11434/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages,
      stream: true
    })
  });

  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    for (const line of chunk.split('\n')) {
      if (!line.trim()) continue;
      try {
        const data = JSON.parse(line);
        const text = data?.message?.content;
        if (text) onChunk(text);
      } catch {
        // ignore malformed lines
      }
    }
  }
}
