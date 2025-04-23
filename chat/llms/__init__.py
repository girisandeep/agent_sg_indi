from .openai_client import OpenAIClient

def get_llm_client(provider):
    if provider == "openai":
        return OpenAIClient()
    raise ValueError(f"Unknown LLM provider: {provider}")
