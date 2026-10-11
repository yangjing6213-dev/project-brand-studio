from __future__ import annotations

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class CiWorkflowContractTests(unittest.TestCase):
    def test_codeql_workflow_scans_python_and_github_actions(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")

        self.assertRegex(workflow, re.compile(r"(?m)^\s*language:\s*\[\s*actions\s*,\s*python\s*\]$"))
        self.assertIn("languages: ${{ matrix.language }}", workflow)
        self.assertIn("build-mode: none", workflow)


if __name__ == "__main__":
    unittest.main()
