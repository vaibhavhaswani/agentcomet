import os
from setuptools import setup, find_packages

# Read README for long description safely
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Modern Agent Management & State Persistence Framework"

setup(
    name="agentcomet",
    version="0.5.0",
    description="Modern Agent Management & State Persistence Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Vaibhav Haswani",
    packages=find_packages(),
    install_requires=[
        "uaf-cli", 
        "requests",
        "pyyaml"
    ],
    python_requires=">=3.8",
)
