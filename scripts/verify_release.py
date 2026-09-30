"""Check tracked working-tree files for local state, oversized files and secrets.

Only file names and check categories are reported; matched values are never printed.
This is a narrow pre-push check, not a replacement for a security audit.
"""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "Credential in URL": re.compile(rb"https?://[^\s/@:]+:[^\s/@]{12,}@"),
}
BLOCKED_PARTS = {"node_modules", ".expo", ".venv", ".venv-data", ".venv-ml", ".venv-training", ".venv-grib", "__pycache__", ".slim"}


def main():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    paths = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    if not paths:
        raise RuntimeError("Stage the intended repository files before release verification")
    issues, sizes = [], []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            continue
        if BLOCKED_PARTS.intersection(path.relative_to(ROOT).parts):
            issues.append({"path": relative, "reason": "Local dependency/runtime directory"})
        if path.name.startswith(".env") and path.name != ".env.example":
            issues.append({"path": relative, "reason": "Environment values"})
        if path.suffix in {".sqlite", ".db", ".pid", ".pyc"} or ".sqlite-" in path.name:
            issues.append({"path": relative, "reason": "Local runtime state"})
        payload = path.read_bytes()
        sizes.append((len(payload), relative))
        if len(payload) >= 100 * 1024 * 1024:
            issues.append({"path": relative, "reason": "At or above GitHub 100MiB file limit"})
        if b"\0" not in payload[:8192]:
            for label, expression in RULES.items():
                if expression.search(payload):
                    issues.append({"path": relative, "reason": label})
    report = {"status": "passed" if not issues else "failed", "tracked_files": len(paths),
              "tracked_bytes": sum(size for size, _ in sizes), "largest_files": [
                  {"path": path, "bytes": size} for size, path in sorted(sizes, reverse=True)[:8]],
              "issues": issues, "scope": "Known token/key patterns, tracked local state and per-file size; no matched values retained"}
    output = ROOT / "artifacts/release_scan.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
