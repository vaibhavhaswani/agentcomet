import argparse
import sys
import os

from .orchestrators import AgentOrchestrator, AgentOrchestrator
# from .vcs import Repository
from .agents.loader import load_agent

def main():
    parser = argparse.ArgumentParser(prog="afc", description="Agent File Commit - Agent Lifecycle Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init Agent Project
    parser_init = subparsers.add_parser("init", help="Initialize a new agent project")
    parser_init.add_argument("name", help="Name of the agent")
    
    # VCS Commands
    parser_vcs = subparsers.add_parser("vcs", help="VCS commands")
    vcs_subparsers = parser_vcs.add_subparsers(dest="vcs_command", help="VCS subcommands")
    
    vcs_init = vcs_subparsers.add_parser("init", help="Initialize a new repository")
    
    vcs_commit = vcs_subparsers.add_parser("commit", help="Commit files")
    vcs_commit.add_argument("-m", "--message", required=True, help="Commit message")
    vcs_commit.add_argument("files", nargs="+", help="Files to commit")
    
    vcs_log = vcs_subparsers.add_parser("log", help="Show commit logs")

    # Run command
    parser_run = subparsers.add_parser("run", help="Run a workflow or agent")
    parser_run.add_argument("file", help="Path to workflow file or agent .uaf")
    
    # Build command
    parser_build = subparsers.add_parser("build", help="Build the agent into a .uaf file")
    parser_build.add_argument("--setup", default="uaf_setup.yaml", help="Path to setup file")

    args = parser.parse_args()

    # Handle VCS commands
    if args.command == "vcs":
        repo = Repository(os.getcwd())
        
        if args.vcs_command == "init":
            repo.init()
            
        elif args.vcs_command == "commit":
            try:
                repo.commit(args.message, args.files)
            except Exception as e:
                print(f"Error: {e}")
                
        elif args.vcs_command == "log":
            repo.log()
            
        else:
            parser_vcs.print_help()

    elif args.command == "init":
        print(f"Initializing new agent project: {args.name}")
        # Placeholder for directory scaffolding
        os.makedirs(args.name, exist_ok=True)
        with open(os.path.join(args.name, "agent.yaml"), "w") as f:
            f.write(f"name: {args.name}\nversion: \"1.0\"\n")
        # Template uaf_setup.yaml
        with open(os.path.join(args.name, "uaf_setup.yaml"), "w") as f:
            f.write(f"output: {args.name}.uaf\nfiles:\n  agent.yaml: agent.yaml\n")
            
        print(f"Created directory {args.name}/")

    elif args.command == "build":
        try:
            from uaf_cli.builder import UAFBuilder
            print(f"Building from {args.setup}...")
            builder = UAFBuilder(args.setup)
            builder.build()
        except ImportError:
            print("Error: uaf-cli not found.")
        except Exception as e:
            print(f"Build Error: {e}")
        
    elif args.command == "run":
        print(f"Running {args.file}...")
        # Basic run logic for a single UAF
        try:
            agent = load_agent(args.file)
            result = agent.invoke({})
            print("Result:", result)
        except Exception as e:
            print(f"Error running agent: {e}")
        
    else:
        parser.print_help()

# if __name__ == "__main__":
#     main()
