# Contributing to Mac Fleet Automation Toolkit

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project follows a standard code of conduct. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch
5. Make your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.9+
- Ansible 2.14+
- Git

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/yourusername/mac-fleet-automation.git
cd mac-fleet-automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r scripts/requirements.txt
pip install -r web/requirements.txt

# Install development dependencies
pip install pytest ansible-lint shellcheck-py black isort flake8

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-feature`
- `bugfix/fix-issue-description`
- `docs/update-readme`
- `refactor/improve-function`

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(scripts): add support for bulk DNS operations
fix(ansible): correct homebrew path for Apple Silicon
docs(readme): update installation instructions
```

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints for functions
- Maximum line length: 100 characters
- Use docstrings for modules, classes, and functions

```python
def process_hostname(hostname: str, domain: str) -> str:
    """
    Process hostname and append domain if needed.
    
    Args:
        hostname: The hostname to process
        domain: The domain to append
        
    Returns:
        Fully qualified domain name
    """
    if not hostname.endswith(domain):
        return f"{hostname}.{domain}"
    return hostname
```

### Ansible

- Use YAML syntax consistently
- Include comments for complex tasks
- Use `ansible-lint` before committing
- Follow role directory structure conventions

```yaml
---
# tasks/main.yml
- name: Install required packages
  homebrew:
    name: "{{ item }}"
    state: present
  loop: "{{ required_packages }}"
  become_user: "{{ admin_user }}"
```

### Shell Scripts

- Use `shellcheck` for linting
- Include shebang: `#!/usr/bin/env bash`
- Use `set -euo pipefail` for safety
- Quote variables: `"${variable}"`

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

## Testing

### Python Tests

```bash
# Run all tests
pytest scripts/tests/

# Run with coverage
pytest --cov=scripts scripts/tests/

# Run specific test
pytest scripts/tests/test_powerdns_manager.py
```

### Ansible Tests

```bash
# Syntax check
ansible-playbook --syntax-check ansible/mac-mini-base-config.yml

# Lint
ansible-lint ansible/

# Dry run (check mode)
ansible-playbook -i inventory.ini playbook.yml --check
```

### Shell Script Tests

```bash
# Lint all shell scripts
shellcheck pipelines/*.sh
shellcheck web/setup.sh
```

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add entry to CHANGELOG.md (if applicable)
4. Create pull request with clear description

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Documentation updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] No sensitive data included
```

## Questions?

If you have questions, feel free to open an issue for discussion.

Thank you for contributing! 🎉

