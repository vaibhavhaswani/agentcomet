import os
import json
import shutil
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class Commit:
    hash: str
    message: str
    author: str
    timestamp: float
    parent: Optional[str]
    files: Dict[str, str] # filename -> file_hash

class Repository:
    """
    Simple VCS for AgentComet.
    Stores versions of agents in .agentcomet directory.
    """
    DIR_NAME = ".agentcomet"

    def __init__(self, root_path: str = "."):
        self.root = os.path.abspath(root_path)
        self.repo_dir = os.path.join(self.root, self.DIR_NAME)
        self.objects_dir = os.path.join(self.repo_dir, "objects")
        self.refs_dir = os.path.join(self.repo_dir, "refs")
        self.head_file = os.path.join(self.repo_dir, "HEAD")

    def init(self):
        """
        Initialize a new repository.
        """
        if os.path.exists(self.repo_dir):
            print("Repository already initialized.")
            return

        os.makedirs(self.objects_dir)
        os.makedirs(os.path.join(self.refs_dir, "heads"))
        
        # Default branch is main
        with open(self.head_file, "w") as f:
            f.write("ref: refs/heads/main")
        
        print(f"Initialized empty AgentComet repository in {self.repo_dir}")

    def _hash_file(self, filepath: str) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()

    def _write_object(self, content: bytes) -> str:
        """
        Write content to objects dir with content-addressable hash.
        """
        sha = hashlib.sha256(content).hexdigest()
        path = os.path.join(self.objects_dir, sha)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(content)
        return sha

    def _copy_file_to_object(self, filepath: str) -> str:
        sha = self._hash_file(filepath)
        dest = os.path.join(self.objects_dir, sha)
        if not os.path.exists(dest):
            shutil.copy2(filepath, dest)
        return sha

    def _get_current_head(self) -> Optional[str]:
        if not os.path.exists(self.head_file):
            return None
        with open(self.head_file, "r") as f:
            ref = f.read().strip()
        
        if ref.startswith("ref: "):
            ref_path = os.path.join(self.repo_dir, ref[5:])
            if os.path.exists(ref_path):
                with open(ref_path, "r") as f:
                    return f.read().strip()
            return None # New branch
        return ref # Detached HEAD

    def commit(self, message: str, files: List[str], author: str = "Unknown"):
        """
        Create a new commit with the specified files.
        """
        if not os.path.exists(self.repo_dir):
            raise ValueError("Repository not initialized. Run 'init' first.")
        
        # 1. Store files
        file_hashes = {}
        for fpath in files:
            full_path = os.path.join(self.root, fpath)
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File {fpath} not found.")
            file_hash = self._copy_file_to_object(full_path)
            file_hashes[fpath] = file_hash

        # 2. Create Commit object
        parent = self._get_current_head()
        
        commit_data = {
            "message": message,
            "author": author,
            "timestamp": datetime.now().timestamp(),
            "parent": parent,
            "files": file_hashes
        }
        
        commit_content = json.dumps(commit_data, sort_keys=True).encode('utf-8')
        commit_hash = self._write_object(commit_content)
        
        # 3. Update HEAD
        with open(self.head_file, "r") as f:
            ref = f.read().strip()
        
        if ref.startswith("ref: "):
            ref_path = os.path.join(self.repo_dir, ref[5:])
            with open(ref_path, "w") as f:
                f.write(commit_hash)
        else:
            # Detached head - update head directly? usually not allowed or simple
            with open(self.head_file, "w") as f:
                f.write(commit_hash)

        print(f"[{commit_hash[:7]}] {message}")
        return commit_hash

    def log(self):
        """
        Print commit log.
        """
        current = self._get_current_head()
        while current:
            obj_path = os.path.join(self.objects_dir, current)
            if not os.path.exists(obj_path):
                print(f"Error: Commit object {current} missing.")
                break
            
            with open(obj_path, "r") as f:
                data = json.load(f)
            
            ts = datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"commit {current}")
            print(f"Author: {data['author']}")
            print(f"Date:   {ts}")
            print(f"\n    {data['message']}\n")
            
            current = data['parent']

