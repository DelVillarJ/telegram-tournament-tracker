import os
from typing import List, Dict, Any, Optional
from groq import Groq
import requests
import logging

logger = logging.getLogger(__name__)

class HybridAgentOrchestrator:
    """
    Orchestrates tasks between local Ollama models and cloud Groq models
    to maximize speed and VRAM efficiency.
    """
    def __init__(self, groq_env_path: str, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        
        # Load Groq Key
        with open(groq_env_path, 'r') as f:
            for line in f:
                if line.startswith("GROQ_API_KEY="):
                    self.groq_key = line.split("=")[1].strip()
        
        self.groq_client = Groq(api_key=self.groq_key)
        
        # Load Ollama Cloud Key (assuming it's in the same .env file)
        self.ollama_cloud_key = None
        with open(groq_env_path, 'r') as f:
            for line in f:
                if line.startswith("OLLAMA_CLOUD_API_KEY="):
                    self.ollama_cloud_key = line.split("=")[1].strip()
        
        # Agent Mapping: (Task Type) -> (Model, Provider)
        self.agent_map = {
            "coding": ("gpt-oss:120b", "ollama_cloud"),
            "testing": ("gemma4:e4b-it-q8_0", "local"),
            "research": ("gemma4:31b", "ollama_cloud"),
            "security": ("qwen3.5:9b-q8_0", "local"),
            "general": ("qwen3.5:9b-q8_0", "local")
        }

    async def route_task(self, task_type: str, prompt: str) -> str:
        """Routes a task to the most efficient agent."""
        model, provider = self.agent_map.get(task_type, self.agent_map["general"])
        
        if provider == "groq":
            return await self._call_groq(model, prompt)
        elif provider == "ollama_cloud":
            return await self._call_ollama_cloud(model, prompt)
        else:
            return await self._call_local(model, prompt)

    async def _call_ollama_cloud(self, model: str, prompt: str) -> str:
        """Call Ollama Cloud API for high-capacity models."""
        if not self.ollama_cloud_key:
            logger.error("OLLAMA_CLOUD_API_KEY not found in env file")
            return await self._call_local("qwen3.5:9b-q8_0", prompt)
            
        try:
            response = requests.post(
                "https://api.ollama.cloud/api/generate",
                headers={"Authorization": f"Bearer {self.ollama_cloud_key}"},
                json={"model": model, "prompt": prompt, "stream": False}
            )
            return response.json().get("response", "No response from Ollama Cloud.")
        except Exception as e:
            logger.error(f"Ollama Cloud error: {e}")
            return await self._call_local("qwen3.5:9b-q8_0", prompt)

    async def _call_groq(self, model: str, prompt: str) -> str:
        """Call Groq Cloud API for high-speed inference."""
        try:
            completion = self.groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return await self._call_local("qwen3.5:9b-q8_0", prompt) # Fallback to local

    async def _call_local(self, model: str, prompt: str) -> str:
        """Call local Ollama instance."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False}
            )
            return response.json().get("response", "No response from local model.")
        except Exception as e:
            logger.error(f"Local Ollama error: {e}")
            return "Local model failed to respond."

# Example usage for the user
if __name__ == "__main__":
    import asyncio
    async def test():
        orch = HybridAgentOrchestrator("C:\\Users\\jdelv\\Documents\\python\\telegrambot\\.env.groq")
        print("Testing Coding Agent (Groq)...")
        print(await orch.route_task("coding", "Write a python function to sort a list"))
        print("\nTesting Security Agent (Local)...")
        print(await orch.route_task("security", "What are common SQL injection risks?"))

    asyncio.run(test())
