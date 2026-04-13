import os
import shutil
from agentcomet import Agent, create_agent, load_agent
from agentcomet.models import Ollama
from agentcomet.tools import tool

# LLM Instance
llm = Ollama(model="gemma3:4b")

# 1. Custom tool
@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

print("--- Testing ToolSpec ---")
print("multiply tool name:", multiply.name)

# 2. Custom Math Agent
print("\n--- Creating Math Agent ---")
class MyMathAgent(Agent):
    def setup(self):
        self.name = "math-bot"
        self.description = "Math assistant that remembers calculations"
        self.author = "TestUser"
        self.add_tools(multiply)

agent = MyMathAgent(llm=llm)

# 3. Chat — share info and do calculations (auto-saved to memory)
print("\n--- Chatting with agent ---")
print(agent.run("Hi, my name is Vaibhav"))
print(agent.run("What is 6 times 7?"))
print(agent.run("Now multiply that result by 3"))
print(agent.run("What is 15 times 8?"))

# Check stored messages
print(f"\n--- Memory: {len(agent.memory.get('messages', []))} messages stored ---")

# 4. Save state and export
print("\n--- Save & Export ---")
agent.save_state("after-calculations")

uaf_path = "test_math_bot.uaf"
if os.path.exists(uaf_path):
    os.remove(uaf_path)
agent.export(uaf_path)

# 5. Load from UAF — ask about earlier calculations
print("\n--- Load & Ask from Memory ---")
loaded = load_agent(uaf_path)
print(f"Restored {len(loaded.memory.get('messages', []))} messages")

print("\nAsking loaded agent about previous session:")
print(loaded.run("What is my name?"))
print(loaded.run("What calculations did we do earlier?"))
print(loaded.run("What was 6 times 7?"))

# 6. Tool-call parser regression checks
print("\n--- Tool Call Parser ---")
parsed = agent._parse_tool_call(
    "TOOL_CALL: write(path='tmp/out.py', content='''print(\"hello\")\\nprint(\"world\")''')"
)
assert parsed is not None
tool_name, kwargs = parsed
assert tool_name == "write"
assert kwargs["path"] == "tmp/out.py"
assert kwargs["content"] == "print(\"hello\")\nprint(\"world\")"

assert agent._parse_tool_call(
    "I already wrote it.\nTOOL_CALL: write(path='tmp/out.py', content='''x''')"
) is None

# Cleanup
os.remove(uaf_path)
if os.path.exists(".agentcomet"):
    shutil.rmtree(".agentcomet")

print("\nDone!")
