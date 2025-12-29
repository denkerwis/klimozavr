from pathlib import Path

content = """[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "klimozawr"
version = "0.1.0"
description = "Windows offline ICMP monitor (PySide6 + SQLite + Windows ICMP API)"
requires-python = ">=3.12"
dependencies = [
  "PySide6>=6.7.0",
  "argon2-cffi>=23.1.0",
]
authors = [{name="klimozawr"}]
readme = "README.md"
license = {file="LICENSE"}

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pyinstaller>=6.6.0",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
"""

Path("pyproject.toml").write_text(content, encoding="utf-8", newline="\n")
print("pyproject.toml rewritten (utf-8 no BOM)")
