# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-01
**Commit:** d0d03f9
**Branch:** main
**Repo:** DublokSoftware/workflows

---

## OVERVIEW

Reusable GitHub Actions workflow for Docker CI/CD pipelines. Provides multi-platform image builds, dual registry push (Docker Hub + GHCR), SBOM generation, vulnerability scanning, and automated GitHub releases.

**Key Value**: Other repos call this workflow via `uses:` — single source of truth for Docker CI/CD.

---

## STRUCTURE

```
workflows/
├── .github/workflows/
│   ├── build-and-push.yml           # Main reusable workflow (275 lines)
│   └── build-and-push/              # Python helper scripts (9 files)
│       ├── update_version.py        # Version from branch + build number
│       ├── generate_docker_tags.py  # Docker Hub + GHCR tag generation
│       ├── generate_sbom.py         # SBOM via sbominify (DinD-aware)
│       ├── compare_sboms.py         # Change detection for scheduled builds
│       ├── generate_vulnerability_report.py  # Trivy scanning
│       ├── publish_release.py       # GitHub release + tag management
│       ├── commit_files.py          # Multi-file atomic commits (Git Data API)
│       ├── upload_release_assets.py # Release asset upload via gh CLI
│       └── cancel_workflow.py       # Scheduled build cancellation
├── AGENTS.md                        # This file
├── README.md                        # Minimal (just "# workflows")
├── repomix.config.json              # Repomix config for repo packing
├── .sh                              # Repomix helper script
└── .gitignore                       # Python gitignore template
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/modify workflow steps | `build-and-push.yml` | 25 sequential steps |
| Add new workflow input | `build-and-push.yml:4-51` | inputs + secrets section |
| Change version logic | `update_version.py` | Branch regex: `^(v[0-9]+(\.[0-9]+)*)([-][a-zA-Z0-9._-]+)?$` |
| Modify Docker tags | `generate_docker_tags.py` | SHA tag + version tags |
| SBOM generation | `generate_sbom.py` | sbominify container, DinD detection |
| Vulnerability scanning | `generate_vulnerability_report.py` | Trivy container |
| Release creation | `publish_release.py` | `GitHubReleaseManager` class |
| Multi-file commits | `commit_files.py` | GitHub Git Data API (6-step atomic commit) |
| Scheduled build skip | `compare_sboms.py` + `cancel_workflow.py` | Skip if SBOM unchanged |

---

## WORKFLOW INPUTS & SECRETS

### Inputs (passed via `with:`)

| Input | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `image_name` | **Yes** | string | — | Docker image name |
| `runner` | No | string | `ubuntu-latest` | GitHub Actions runner |
| `project_name` | No | string | — | Multi-project support (affects file naming) |
| `platforms` | No | string | `linux/amd64,linux/arm64` | Build platforms |
| `context_path` | No | string | `src` | Docker build context |
| `dockerfile_path` | No | string | `Dockerfile` | Dockerfile location |
| `push_to_dockerhub` | No | boolean | `true` | Push to Docker Hub |
| `push_to_ghcr` | No | boolean | `true` | Push to GHCR |

### Secrets (passed via `secrets:`)

| Secret | Required | Description |
|--------|----------|-------------|
| `DOCKER_USERNAME` | If Docker Hub | Docker Hub username |
| `DOCKER_TOKEN` | If Docker Hub | Docker Hub access token |
| `ENCRYPTION_KEY` | No | Build-time encryption key |

### Permissions Required (caller must grant)

```yaml
permissions:
  contents: write   # Commits, releases
  packages: write   # GHCR push
  actions: write    # Workflow cancellation
```

---

## PIPELINE STAGES (25 steps)

```
1. Log event name
2. Determine trigger type
3. Checkout target repository → repo/
4. Checkout workflows repository → workflows/
5. Copy Python scripts to repo/.github/workflows/build-and-push/
6. update_version.py → full_version, tags
7. Docker Hub login (if enabled, 3 retries × 30s)
8. Setup QEMU (multi-arch)
9. Setup Docker Buildx
10. GHCR login (if enabled)
11. generate_docker_tags.py → sha_tag, all tags
12. Build + push image (SHA tag only)
13. List Docker images (diagnostic)
14. Save image to tar file
15. List Docker images (diagnostic)
16. generate_sbom.py → .sbom_/sbom.json, sbom.txt
17. List Docker images (diagnostic)
18. compare_sboms.py → new_sbom=true/false
19. cancel_workflow.py (if scheduled + no changes)
20. generate_vulnerability_report.py → .vulnerability_report.txt
21. List Docker images (diagnostic)
22. commit_files.py → commit artifacts to repo
23. publish_release.py → create GitHub release
24. upload_release_assets.py → attach SBOM, vuln report, image tar
25. Tag and push additional version tags (v1, v1.2, latest, etc.)
```

---

## CONVENTIONS

### Python Scripts

- **Shebang**: `#!/usr/bin/env python3`
- **Entry point**: `if __name__ == "__main__": main()` (some have `retry_main()`)
- **Config**: Environment variables only, no CLI args
- **Output**: Write to `os.environ['GITHUB_OUTPUT']`
- **Type hints**: Function signatures typed (publish_release.py is 100%)

### Logging

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### Error Handling & Retry

| Pattern | Scripts | Details |
|---------|---------|---------|
| Exponential backoff | `publish_release.py` | `sleep = retry_delay * (attempt + 1)` → 2s, 4s, 6s |
| Linear backoff | `update_version.py`, `upload_release_assets.py`, `cancel_workflow.py` | Fixed 2s delay |
| Rate limit aware | `publish_release.py` | Checks `X-RateLimit-Reset` header |
| No retry | `commit_files.py`, `generate_*.py`, `compare_sboms.py` | Single attempt |

### GitHub API Patterns

**Authentication**:
- Most scripts: `Authorization: token {GITHUB_TOKEN}`
- `cancel_workflow.py`: `Authorization: Bearer {GITHUB_TOKEN}` (different!)

**Atomic multi-file commit** (commit_files.py):
1. GET `/git/refs/heads/{branch}` → commit SHA
2. GET `/git/commits/{sha}` → tree SHA
3. POST `/git/blobs` for each file
4. POST `/git/trees` with base tree + blobs
5. POST `/git/commits` with parent + tree
6. PATCH `/git/refs/heads/{branch}` → update branch pointer

### PROJECT_NAME Multi-Project Support

When `PROJECT_NAME` env var is set:
- Version files: `.version_{project}_{branch}.json`
- SBOM dirs: `.sbom_{project}_/` (temp) → `.sbom_{project}/` (committed)
- Vulnerability reports: `.vulnerability_report_{project}.txt`
- Release tags: `{project}-{version}`
- Release names: `Release {project} {version}`

---

## ENVIRONMENT VARIABLES

### Script Requirements

| Script | Required Env Vars | Optional |
|--------|-------------------|----------|
| `update_version.py` | `GH_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_REF`, `GITHUB_OUTPUT` | `PROJECT_NAME` |
| `generate_docker_tags.py` | `TAGS_JSON`, `DOCKER_USERNAME`, `IMAGE_NAME`, `REPO_OWNER`, `PUSH_TO_DOCKERHUB`, `PUSH_TO_GHCR`, `GITHUB_OUTPUT` | `GITHUB_SHA`, `PROJECT_NAME` |
| `generate_sbom.py` | `IMAGE_TAG`, `HOME` | `PROJECT_NAME`, `GITHUB_TOKEN`, `GITHUB_ACTOR` |
| `compare_sboms.py` | `GITHUB_OUTPUT` | `PROJECT_NAME` |
| `generate_vulnerability_report.py` | `IMAGE_TAG`, `GITHUB_TOKEN`, `GITHUB_ACTOR` | `PROJECT_NAME` |
| `commit_files.py` | `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_REF`, `VERSION` | `PROJECT_NAME` |
| `publish_release.py` | `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_REF`, `GITHUB_SHA`, `GITHUB_OUTPUT` | `PROJECT_NAME` |
| `upload_release_assets.py` | `GH_TOKEN`, `VERSION`, `IMAGE_NAME` | `PROJECT_NAME` |
| `cancel_workflow.py` | `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID` | — |

---

## EXTERNAL DEPENDENCIES

### Containers Used

| Container | Used By | Purpose |
|-----------|---------|---------|
| `ghcr.io/dockforge/sbominify:latest` | `generate_sbom.py` | SBOM generation |
| `ghcr.io/aquasecurity/trivy:latest` | `generate_vulnerability_report.py` | Vulnerability scanning |
| `ghcr.io/aquasecurity/trivy-db:latest` | `generate_vulnerability_report.py` | Trivy vulnerability DB |
| `mirror.gcr.io/moby/buildkit:buildx-stable-1` | `build-and-push.yml` | Docker Buildx driver |

### Python Packages

- **stdlib only**: `compare_sboms.py`
- **requests**: All other scripts (installed inline: `pip install --break-system-packages requests`)
- **subprocess**: `generate_sbom.py`, `generate_vulnerability_report.py`, `upload_release_assets.py`

**Note**: No `requirements.txt` — `requests` installed in workflow step 6.

---

## ANTI-PATTERNS & KNOWN ISSUES

| File | Line | Issue | Severity |
|------|------|-------|----------|
| `generate_sbom.py` | 144 | `docker_login()` commented out — dead code or debug remnant | Low |
| `generate_docker_tags.py` | 76 | Typo: `+==` should be `===` in print (cosmetic) | Low |
| `build-and-push.yml` | 161, 177, 191, 224 | Duplicate "List Docker images" steps — redundant | Low |
| `commit_files.py` | 229 | Hardcoded 2-second sleep — magic number, no comment | Low |
| `cancel_workflow.py` | 101-102 | Infinite loop after success — may block cleanup | Medium |
| `cancel_workflow.py` | auth | Uses `Bearer` auth instead of `token` auth (inconsistent) | Low |

---

## USAGE EXAMPLES

### Basic Usage (Caller Workflow)

```yaml
name: Build and Push
on:
  push:
    paths: ['app/**', 'Dockerfile']
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  docker:
    permissions:
      contents: write
      packages: write
      actions: write
    uses: dubloksoftware/workflows/.github/workflows/build-and-push.yml@main
    with:
      image_name: ${{ github.event.repository.name }}
    secrets:
      DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
      DOCKER_TOKEN: ${{ secrets.DOCKER_TOKEN }}
```

### Multi-Project / Custom Runner

```yaml
jobs:
  docker:
    uses: dubloksoftware/workflows/.github/workflows/build-and-push.yml@main
    with:
      runner: 'self-hosted'
      project_name: 'my-project'
      image_name: my-app
      platforms: 'linux/amd64,linux/arm64,linux/arm/v7'
      context_path: 'docker'
      dockerfile_path: 'docker/Dockerfile.prod'
      push_to_dockerhub: true
      push_to_ghcr: false
    secrets:
      DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
      DOCKER_TOKEN: ${{ secrets.DOCKER_TOKEN }}
      ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
```

---

## VERSION TAGGING LOGIC

Branch name drives version tags:

| Branch | Extracted Version | Generated Tags |
|--------|-------------------|----------------|
| `v1.2.3` | `1.2.3` (stable) | `v1`, `v1.2`, `v1.2.3`, `v1.2.3.{build}`, `latest` |
| `v1.2.3-beta` | `1.2.3` + suffix `-beta` | `v1-beta`, `v1.2-beta`, `v1.2.3-beta`, `v1.2.3.{build}-beta`, `beta` |
| `main` | `0.0` (default) | `v0`, `v0.0`, `v0.0.{build}`, `latest` |

**Prerelease detection**: suffix in `['alpha', 'beta', 'rc']` → marks release as prerelease

**Build number**: Stored in `.version_{project}_{branch}.json`, increments each build

---

## SCHEDULED BUILD OPTIMIZATION

For `schedule` triggered builds:

1. `compare_sboms.py` compares new SBOM with committed SBOM
2. If identical → `cancel_workflow.py` cancels the run
3. Prevents unnecessary releases when dependencies unchanged

**Flow**:
```
generate_sbom.py → .sbom_/sbom.txt (new)
compare_sboms.py → compares with .sbom/sbom.txt (old)
  → new_sbom=false → cancel_workflow.py (exits early)
  → new_sbom=true → continue to release
```

---

## DOCKER-IN-DOCKER HANDLING

`generate_sbom.py` detects DinD environments:

**Detection**: Checks `/.dockerenv` file or `docker` in `/proc/1/cgroup`

| Environment | Approach |
|-------------|----------|
| Standard | Volume mount `-v {output_dir}:/output` |
| Docker-in-Docker | Named container + `docker cp` to extract files |

**Fallback**: If volume mount produces no files, automatically switches to docker cp method.

---

## TESTING

**No automated tests** — scripts validated via workflow execution.

**Manual testing**: Run workflow in a test repository with various inputs.

---

## NOTES

- **Concurrency**: `cancel-in-progress: false` — builds complete without interruption
- **Cache**: Uses GitHub Actions cache (`type=gha`) for Docker layer caching
- **OCI Labels**: Sets `org.opencontainers.image.title`, `.version`, `.source`
- **Repomix**: `.sh` generates `repopack.yml` for AI context packing
