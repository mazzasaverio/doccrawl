# Project Overview for LLM Analysis

Key aspects to analyze:

1. Code structure and organization

2. Dependency management

3. Best practices implementation

4. Potential improvements

5. Security considerations


# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── llm_analysis.md
├── project_documentation.md
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# llm_analysis.md
```md
# Project Overview for LLM Analysis

Key aspects to analyze:

1. Code structure and organization

2. Dependency management

3. Best practices implementation

4. Potential improvements

5. Security considerations


# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── project_docs.py
├── project_documentation.md
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# project_docs.py
```py
# project_docs.py

import os
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Set

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea', '.vscode'
        }
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml', '.md', '.txt', '.sh'}
        
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path or any(part.startswith('.') for part in Path(path).parts):
                return True
        return False
    
    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            
            for i, entry in enumerate(entries):
                if self._should_ignore(str(entry)):
                    continue
                
                is_last = i == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"\n# {file_path}\n```{file_path.suffix[1:] if file_path.suffix else ''}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(str(root_path)):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if file_path.suffix in self.code_extensions and not self._should_ignore(str(file_path)):
                    code_contents.append(self.get_file_content(file_path))
        
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
            f"# Project Documentation\nGenerated on: {timestamp}\n",
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        # Create a compact version for LLMs
        compact_content = [
            "# Project Overview for LLM Analysis\n",
            "Key aspects to analyze:\n",
            "1. Code structure and organization\n",
            "2. Dependency management\n",
            "3. Best practices implementation\n",
            "4. Potential improvements\n",
            "5. Security considerations\n\n",
            self.get_tree(),
            self.get_code_contents()
        ]
        
        with open('llm_analysis.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(compact_content))

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("Documentation generated successfully!")
    print("- Full documentation: project_documentation.md")
    print("- LLM analysis version: llm_analysis.md")
```


# project_documentation.md
```md
# Project Documentation
Generated on: 2024-10-27 12:53:32

# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── project_docs.py
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Project Dependencies


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```

# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# project_docs.py
```py
# project_docs.py

import os
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Set

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea', '.vscode'
        }
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml', '.md', '.txt', '.sh'}
        
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path or any(part.startswith('.') for part in Path(path).parts):
                return True
        return False
    
    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            
            for i, entry in enumerate(entries):
                if self._should_ignore(str(entry)):
                    continue
                
                is_last = i == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"\n# {file_path}\n```{file_path.suffix[1:] if file_path.suffix else ''}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(str(root_path)):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if file_path.suffix in self.code_extensions and not self._should_ignore(str(file_path)):
                    code_contents.append(self.get_file_content(file_path))
        
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
            f"# Project Documentation\nGenerated on: {timestamp}\n",
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        # Create a compact version for LLMs
        compact_content = [
            "# Project Overview for LLM Analysis\n",
            "Key aspects to analyze:\n",
            "1. Code structure and organization\n",
            "2. Dependency management\n",
            "3. Best practices implementation\n",
            "4. Potential improvements\n",
            "5. Security considerations\n\n",
            self.get_tree(),
            self.get_code_contents()
        ]
        
        with open('llm_analysis.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(compact_content))

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("Documentation generated successfully!")
    print("- Full documentation: project_documentation.md")
    print("- LLM analysis version: llm_analysis.md")
```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# project_documentation.md
```md
# Project Documentation
Generated on: 2024-10-27 12:57:34

# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── llm_analysis.md
├── project_documentation.md
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Project Dependencies


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```

# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# llm_analysis.md
```md
# Project Overview for LLM Analysis

Key aspects to analyze:

1. Code structure and organization

2. Dependency management

3. Best practices implementation

4. Potential improvements

5. Security considerations


# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── project_docs.py
├── project_documentation.md
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# project_docs.py
```py
# project_docs.py

import os
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Set

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea', '.vscode'
        }
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml', '.md', '.txt', '.sh'}
        
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path or any(part.startswith('.') for part in Path(path).parts):
                return True
        return False
    
    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            
            for i, entry in enumerate(entries):
                if self._should_ignore(str(entry)):
                    continue
                
                is_last = i == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"\n# {file_path}\n```{file_path.suffix[1:] if file_path.suffix else ''}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(str(root_path)):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if file_path.suffix in self.code_extensions and not self._should_ignore(str(file_path)):
                    code_contents.append(self.get_file_content(file_path))
        
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
            f"# Project Documentation\nGenerated on: {timestamp}\n",
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        # Create a compact version for LLMs
        compact_content = [
            "# Project Overview for LLM Analysis\n",
            "Key aspects to analyze:\n",
            "1. Code structure and organization\n",
            "2. Dependency management\n",
            "3. Best practices implementation\n",
            "4. Potential improvements\n",
            "5. Security considerations\n\n",
            self.get_tree(),
            self.get_code_contents()
        ]
        
        with open('llm_analysis.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(compact_content))

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("Documentation generated successfully!")
    print("- Full documentation: project_documentation.md")
    print("- LLM analysis version: llm_analysis.md")
```


# project_documentation.md
```md
# Project Documentation
Generated on: 2024-10-27 12:53:32

# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── project_docs.py
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Project Dependencies


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```

# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# project_docs.py
```py
# project_docs.py

import os
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Set

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea', '.vscode'
        }
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml', '.md', '.txt', '.sh'}
        
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path or any(part.startswith('.') for part in Path(path).parts):
                return True
        return False
    
    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            
            for i, entry in enumerate(entries):
                if self._should_ignore(str(entry)):
                    continue
                
                is_last = i == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"\n# {file_path}\n```{file_path.suffix[1:] if file_path.suffix else ''}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(str(root_path)):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if file_path.suffix in self.code_extensions and not self._should_ignore(str(file_path)):
                    code_contents.append(self.get_file_content(file_path))
        
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
            f"# Project Documentation\nGenerated on: {timestamp}\n",
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        # Create a compact version for LLMs
        compact_content = [
            "# Project Overview for LLM Analysis\n",
            "Key aspects to analyze:\n",
            "1. Code structure and organization\n",
            "2. Dependency management\n",
            "3. Best practices implementation\n",
            "4. Potential improvements\n",
            "5. Security considerations\n\n",
            self.get_tree(),
            self.get_code_contents()
        ]
        
        with open('llm_analysis.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(compact_content))

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("Documentation generated successfully!")
    print("- Full documentation: project_documentation.md")
    print("- LLM analysis version: llm_analysis.md")
```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# project_documentation.md
```md
# Project Documentation
Generated on: 2024-10-27 12:53:32

# Project Structure

├── LICENSE
├── README.md
├── config
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── project_docs.py
├── pyproject.toml
├── src
│   ├── config
│   ├── core
│   ├── db
│   ├── models
│   └── utils
├── tests
└── uv.lock
# Project Dependencies


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```

# Code Contents


# README.md
```md
# doccrawl
Simple document crawler that harvests PDFs and documents from configured web sources.

```


# project_docs.py
```py
# project_docs.py

import os
from pathlib import Path
from datetime import datetime
import subprocess
from typing import List, Set

class ProjectDocumentor:
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = {
            '.git', '.venv', '__pycache__', '.pytest_cache',
            'logs', 'downloads', 'dist', 'build', '*.pyc',
            '.coverage', '.env', '.DS_Store', '.idea', '.vscode'
        }
        self.code_extensions = {'.py', '.yml', '.yaml', '.toml', '.md', '.txt', '.sh'}
        
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path or any(part.startswith('.') for part in Path(path).parts):
                return True
        return False
    
    def get_tree(self) -> str:
        """Generate tree structure of the project."""
        tree_output = ['# Project Structure\n']
        
        def add_to_tree(dir_path: Path, prefix: str = ''):
            entries = sorted(dir_path.iterdir())
            
            for i, entry in enumerate(entries):
                if self._should_ignore(str(entry)):
                    continue
                
                is_last = i == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                tree_output.append(f'{prefix}{connector}{entry.name}')
                
                if entry.is_dir():
                    next_prefix = prefix + ('    ' if is_last else '│   ')
                    add_to_tree(entry, next_prefix)
        
        add_to_tree(self.root_dir)
        return '\n'.join(tree_output)
    
    def get_file_content(self, file_path: Path) -> str:
        """Read and return file content with proper formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"\n# {file_path}\n```{file_path.suffix[1:] if file_path.suffix else ''}\n{content}\n```\n"
        except Exception as e:
            return f"\n# {file_path}\nError reading file: {str(e)}\n"
    
    def get_code_contents(self) -> str:
        """Get contents of all code files."""
        code_contents = ['# Code Contents\n']
        
        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._should_ignore(str(root_path)):
                continue
                
            for file in sorted(files):
                file_path = root_path / file
                if file_path.suffix in self.code_extensions and not self._should_ignore(str(file_path)):
                    code_contents.append(self.get_file_content(file_path))
        
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
            f"# Project Documentation\nGenerated on: {timestamp}\n",
            self.get_tree(),
            self.get_requirements(),
            self.get_code_contents()
        ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        # Create a compact version for LLMs
        compact_content = [
            "# Project Overview for LLM Analysis\n",
            "Key aspects to analyze:\n",
            "1. Code structure and organization\n",
            "2. Dependency management\n",
            "3. Best practices implementation\n",
            "4. Potential improvements\n",
            "5. Security considerations\n\n",
            self.get_tree(),
            self.get_code_contents()
        ]
        
        with open('llm_analysis.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(compact_content))

if __name__ == "__main__":
    documentor = ProjectDocumentor()
    documentor.generate_documentation()
    print("Documentation generated successfully!")
    print("- Full documentation: project_documentation.md")
    print("- LLM analysis version: llm_analysis.md")
```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```

```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "scrapegraphai>=1.27.0",
]

```


# docker/docker-compose.yml
```yml

```
