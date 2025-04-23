# chat/management/commands/chat_agent.py

from django.core.management.base import BaseCommand
from chat.agent.chain_of_thought_runner import run_chain_of_thought_loop

class Command(BaseCommand):
    help = "Interactive Chain-of-Thought REPL Chat Agent"

    def handle(self, *args, **options):
        print("Ask your question (type 'exit' to quit):")

        chat_history = None
        repl = None

        while True:
            question = input("You: ")
            if question.lower() in {"exit", "quit"}:
                break

            print("LLM thinking...\n")

            result_gen = run_chain_of_thought_loop(question, chat_history, repl)
            for chunk in result_gen:
                if isinstance(chunk, tuple) and chunk[0] == "__STATE__":
                    chat_history, repl = chunk[1], chunk[2]
                else:
                    print(chunk, end="", flush=True)

            print("\n")
