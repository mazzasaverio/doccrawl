import os
from pathlib import Path
from datetime import datetime

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        # File da escludere completamente dalla documentazione
        self.exclude_files = {
            'project_docs.py',
            'llm_analysis.md',
            'project_documentation.md'
        }
        
        # Pattern da ignorare
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea'
        }
        
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml',  '.txt', '.sh','.vscode'}

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        # Esclude esplicitamente i file nella lista exclude_files
        if path.name in self.exclude_files:
            return True
            
        for pattern in self.ignore_patterns:
            if pattern in str(path) or any(part.startswith('.') for part in path.parts):
                return True
        return False

    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            filtered_entries = [e for e in entries if not self._should_ignore(e)]
            
            for i, entry in enumerate(filtered_entries):
                is_last = i == len(filtered_entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        if file_path.name in self.exclude_files:
            return ""
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                ext = file_path.suffix[1:] if file_path.suffix else ''
                formatted_path = str(file_path.relative_to(self.root_dir))
                return f"\n# {formatted_path}\n```{ext}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(root_path):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if (file_path.suffix in self.code_extensions and 
                    not self._should_ignore(file_path) and 
                    file_path.name not in self.exclude_files):
                    content = self.get_file_content(file_path)
                    if content:  # Solo se c'è contenuto
                        code_contents.append(content)
        
        return '\n'.join(code_contents)
    
    def get_requirements(self) -> str:
        """Get project dependencies."""
        reqs = ['# Project Dependencies\n']
        
        # Try reading from pyproject.toml
        pyproject_path = self.root_dir / 'pyproject.toml'
        if pyproject_path.exists():
            reqs.append(self.get_file_content(pyproject_path))
        
        # Try reading from requirements.txt
        req_path = self.root_dir / 'requirements.txt'
        if req_path.exists():
            reqs.append(self.get_file_content(req_path))
        
        return '\n'.join(reqs)
    
    def generate_documentation(self, output_file: str = 'project_documentation.md'):
        """Generate complete project documentation."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        content = [
         
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
       

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("\n✅ Documentation generated successfully!")
    print("📄 Files created:")
    print("  - project_documentation.md (Complete documentation)")
    print("  - llm_analysis.md (Optimized for LLM analysis)\n")