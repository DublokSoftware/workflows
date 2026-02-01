# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-01
**Commit:** 5d3e900
**Branch:** main

## OVERVIEW

Reusable GitHub Actions workflow for Docker multi-platform build, push to Docker Hub/GHCR, SBOM generation, vulnerability scanning, and automated releases. Python 3 + GitHub Actions YAML.

## STRUCTURE

```
workflows/
├── .github/workflows/
│   ├── build-and-push.yml        # Main reusable workflow (entry point)
│   └── build-and-push/           # Python helper scripts (9 files)
│       ├── update_version.py     # Version from branch + build number
│       ├── generate_docker_tags.py
│       ├── generate_sbom.py      # Uses sbominify container
│       ├── compare_sboms.py      # Change detection
│       ├── generate_vulnerability_report.py  # Trivy scanning
│       ├── publish_release.py    # GitHub release creation
│       ├── commit_files.py       # Multi-file atomic commits
│       ├── upload_release_assets.py
│       └── cancel_workflow.py
├── repomix.config.json           # Repo packing config
└── .sh                           # Repomix helper script
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/modify workflow steps | `build-and-push.yml` | Sequential execution |
| Change version logic | `update_version.py` | Branch name → semver tags |
| Modify Docker tags | `generate_docker_tags.py` | Docker Hub + GHCR formats |
| SBOM generation | `generate_sbom.py` | Handles Docker-in-Docker |
| Vulnerability scanning | `generate_vulnerability_report.py` | Uses Trivy |
| Release creation | `publish_release.py` | GitHubReleaseManager class |
| Multi-file commits | `commit_files.py` | GitHub Git Data API |

## CONVENTIONS

**Python Scripts:**
- Shebang: `#!/usr/bin/env python3`
- All scripts standalone with `if __name__ == "__main__"`
- Type hints on function signatures
- Logging: `logging.basicConfig()` with `%(asctime)s - %(levelname)s - %(message)s`
- Config via env vars, not CLI args (`os.environ['VAR']`)
- GitHub output: write to `os.environ['GITHUB_OUTPUT']`

**Error Handling:**
- Custom exceptions (e.g., `GitHubAPIError`)
- Retry with exponential backoff: `sleep_time = retry_delay * (attempt + 1)`
- Rate limit handling via `X-RateLimit-Reset` header
- Max 3 retries default

**Versioning:**
- Branch-based: `v1.2.3-beta` → tags `v1`, `v1.2`, `v1.2.3`, `v1.2.3.{build}-beta`
- Build number stored in `.version_{project}_{branch}.json`
- PROJECT_NAME env var enables multi-project support

## ANTI-PATTERNS (THIS PROJECT)

- `generate_sbom.py:144` — `docker_login()` commented out, dead code or forgotten debug
- `generate_docker_tags.py:76` — Typo: `+==` should be `===` in print statement

## WORKFLOW USAGE

Called by other repos as reusable workflow:
```yaml
jobs:
  build:
    uses: dubloksoftware/workflows/.github/workflows/build-and-push.yml@main
    with:
      image_name: my-app
      platforms: linux/amd64,linux/arm64
      context_path: src
      dockerfile_path: Dockerfile
    secrets:
      DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
      DOCKER_TOKEN: ${{ secrets.DOCKER_TOKEN }}
```

**Required inputs:** `image_name`
**Required secrets:** `DOCKER_USERNAME`, `DOCKER_TOKEN` (if pushing to Docker Hub)

## PIPELINE STAGES

1. Checkout repos (target + workflows)
2. `update_version.py` → version tags
3. Docker login (Docker Hub + GHCR)
4. Build + push multi-arch image
5. `generate_sbom.py` → SBOM files
6. `compare_sboms.py` → skip if unchanged (scheduled only)
7. `generate_vulnerability_report.py` → Trivy scan
8. `commit_files.py` → commit artifacts
9. `publish_release.py` → GitHub release
10. `upload_release_assets.py` → attach files
11. Tag additional Docker versions

## NOTES

- No tests — scripts tested via workflow execution
- No requirements.txt — scripts use stdlib + `requests` (pip installed in workflow)
- Docker-in-Docker detection in `generate_sbom.py` for self-hosted runners
- Concurrency: `cancel-in-progress: false` — builds complete, no interruption
- SBOM comparison cancels scheduled builds if no changes detected
