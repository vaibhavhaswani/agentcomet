from setuptools import setup, find_packages

setup(
    name="agentcomet",
    version="0.1.0",
    description="Modern Agent Version Control & Orchestration System",
    author="AgentComet Team",
    packages=find_packages(),
    install_requires=[
        "uaf_compiler", 
    ],

    python_requires=">=3.8",
)
