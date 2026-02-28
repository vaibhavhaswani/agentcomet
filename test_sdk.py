import os
import shutil
from agentcomet import Agent, create_agent, load_agent
from agentcomet.models import Ollama
from agentcomet.tools import tool

# LLM Instance — used throughout
llm = Ollama(model="gemma3:4b")

# 1. Custom tool
@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

print("--- Testing ToolSpec ---")
print("multiply tool name:", multiply.name)
print("multiply schema:", multiply.schema)

# 2. Declarative Agent via create_agent
print("\n--- Testing declarative create_agent ---")
agent1 = create_agent(
    name="math-bot-declarative",
    description="Mathematical assistant created via create_agent",
    author="TestUser",
    llm=llm,
    tools=[multiply],
    memory=True
)
print(agent1.run("What is 5 times 4?"))

# 3. Custom Agent Class
print("\n--- Testing Custom Agent Class ---")
class MyMathAgent(Agent):
    def setup(self):
        self.name = "math-bot-custom"
        self.description = "Mathematical assistant created via custom class"
        self.author = "TestUser"
        self.use_memory(True)
        self.add_tools(multiply)

    def run(self, input: str):
        return self.chat(f"Custom prompt: {input}")

# LLM passed at instantiation
agent2 = MyMathAgent(llm=llm)
print(agent2.run("What is 6 times 7?"))

# 4. Export to UAF
uaf_path = "test_math_bot_custom.uaf"
if os.path.exists(uaf_path):
    os.remove(uaf_path)

print("\n--- Testing UAF Export ---")
agent2.export(uaf_path)

# 5. Load from UAF
print("\n--- Testing UAF Load via AgentCometRuntime ---")
loaded_agent = load_agent(uaf_path)
print("Loaded agent type:", type(loaded_agent))
if loaded_agent:
    print(loaded_agent.run("Hello from loaded agent"))

print("\nDone!")
