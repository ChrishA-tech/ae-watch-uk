"""Tests for Terraform Infrastructure as Code (IaC) configuration.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import re
from pathlib import Path

TERRAFORM_ROOT = Path("infra/terraform")


def test_terraform_modules_and_files_exist():
    """Verify all Terraform modules and root configuration files exist."""
    expected_files = [
        TERRAFORM_ROOT / "main.tf",
        TERRAFORM_ROOT / "variables.tf",
        TERRAFORM_ROOT / "outputs.tf",
        TERRAFORM_ROOT / "modules/networking/main.tf",
        TERRAFORM_ROOT / "modules/networking/variables.tf",
        TERRAFORM_ROOT / "modules/networking/outputs.tf",
        TERRAFORM_ROOT / "modules/database/main.tf",
        TERRAFORM_ROOT / "modules/database/variables.tf",
        TERRAFORM_ROOT / "modules/database/outputs.tf",
        TERRAFORM_ROOT / "modules/security/main.tf",
        TERRAFORM_ROOT / "modules/security/variables.tf",
        TERRAFORM_ROOT / "modules/security/outputs.tf",
        TERRAFORM_ROOT / "modules/compute/main.tf",
        TERRAFORM_ROOT / "modules/compute/variables.tf",
        TERRAFORM_ROOT / "modules/compute/outputs.tf",
    ]

    for tf_file in expected_files:
        assert tf_file.exists(), f"Missing Terraform file: {tf_file}"
        assert tf_file.stat().st_size > 50, f"Terraform file is empty: {tf_file}"


def test_terraform_hcl_syntax_validation():
    """Verify that all .tf files have balanced braces, quotes, and valid HCL blocks."""
    tf_files = list(TERRAFORM_ROOT.rglob("*.tf"))
    assert len(tf_files) >= 15

    for tf_path in tf_files:
        content = tf_path.read_text(encoding="utf-8")

        # Strip commented lines
        lines = [line.strip() for line in content.splitlines() if not line.strip().startswith("#")]
        clean_content = "\n".join(lines)

        # Check balanced curly braces
        open_braces = clean_content.count("{")
        close_braces = clean_content.count("}")
        assert open_braces == close_braces, (
            f"Unbalanced braces in {tf_path}: {open_braces} open vs {close_braces} close"
        )

        # Check valid block declarations
        for line in lines:
            if line.endswith("{"):
                # Must start with a known HCL top-level block keyword or block parameter
                first_token = line.split()[0].strip('"')
                if not re.match(r"^[a-zA-Z0-9_\-]+$", first_token):
                    continue
                # Ensure quotes are balanced on the header line
                assert line.count('"') % 2 == 0, (
                    f"Unbalanced quotes in block header: {line} in {tf_path}"
                )


def test_terraform_author_and_project_tags():
    """Verify that author attribution and project tags are embedded across IaC."""
    root_main = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")
    assert "CHRISH PEP FELIX A" in root_main
    assert "ae-watch-uk" in root_main
    assert "postgres16" in (TERRAFORM_ROOT / "modules/database/main.tf").read_text(encoding="utf-8")
