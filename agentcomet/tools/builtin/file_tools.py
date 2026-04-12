import os
from agentcomet.tools import tool

@tool
def read(path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Read contents of a file, supporting line numbers and pagination.
    Args:
        path: Absolute or relative path to the file.
        start_line: The starting line number (1-indexed) to read from.
        end_line: The ending line number (inclusive). Set to -1 to read to the end.
    """
    try:
        absolute_path = os.path.abspath(path)
        if not os.path.exists(absolute_path):
            return f"Error: File does not exist at {absolute_path}"
            
        with open(absolute_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        total_bytes = sum(len(line.encode("utf-8")) for line in lines)
        
        start_idx = max(1, start_line) - 1
        end_idx = total_lines if end_line == -1 else min(total_lines, end_line)
        
        out_lines = []
        for i in range(start_idx, end_idx):
            line_content = lines[i].rstrip("\\n")
            out_lines.append(f"{i + 1}: {line_content}")
            
        header = f"File Path: {absolute_path}\\n"
        header += f"Total Lines: {total_lines} | Total Bytes: {total_bytes}\\n"
        header += f"Showing lines {start_idx + 1} to {end_idx}:\\n"
        header += "-" * 40 + "\\n"
        
        return header + "\\n".join(out_lines) + "\\n" + "-" * 40
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

@tool
def write(path: str, content: str, overwrite: bool = True) -> str:
    """
    Write or overwrite entirely the content of a file.
    Args:
        path: Absolute or relative path to the file.
        content: The complete raw string content to write.
        overwrite: If false, fails if the file already exists.
    """
    import os
    absolute_path = os.path.abspath(path)
    
    if not overwrite and os.path.exists(absolute_path):
        return f"Error: File already exists at {absolute_path}. Set overwrite=True if you intend to overwrite it."
        
    try:
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Success! Wrote {len(content.splitlines())} lines ({len(content.encode('utf-8'))} bytes) to {absolute_path}"
    except Exception as e:
        return f"Error writing file {absolute_path}: {str(e)}"

@tool
def list_dir(path: str = ".") -> str:
    """
    List the contents of a directory. 
    Args:
        path: Absolute or relative directory path to list. Defaults to current directory (".").
    """
    import os
    absolute_path = os.path.abspath(path)
    
    if not os.path.exists(absolute_path):
        return f"Error: Directory does not exist at {absolute_path}"
    if not os.path.isdir(absolute_path):
        return f"Error: {absolute_path} is not a directory."
        
    try:
        entries = os.listdir(absolute_path)
        directories = []
        files = []
        
        for entry in entries:
            full_path = os.path.join(absolute_path, entry)
            if os.path.isdir(full_path):
                directories.append(entry)
            else:
                try:
                    size = os.path.getsize(full_path)
                except Exception:
                    size = 0
                files.append((entry, size))
                
        directories.sort()
        files.sort(key=lambda x: x[0])
        
        result = [f"Directory contents of: {absolute_path}"]
        result.append("-" * 40)
        
        if directories:
            result.append("Directories:")
            for d in directories:
                result.append(f"  [DIR] {d}/")
                
        if files:
            result.append("Files:")
            for f, size in files:
                result.append(f"  [FILE] {f} ({size} bytes)")
                
        if not directories and not files:
            result.append("  (Empty Directory)")
            
        result.append("-" * 40)
        return "\\n".join(result)
    except Exception as e:
        return f"Error listing directory {absolute_path}: {str(e)}"

