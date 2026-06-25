---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: medium
  category: coding
  subcategory: debugging
  category_confidence: high
  task_type: [coding]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [off-by-one, binary-search, debugging]
verifier:
  type: test-script
  timeout_sec: 300
  service: main
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 600
environment:
  network_mode: no-network
  build_timeout_sec: 600
  os: linux
  cpus: 1
  memory_mb: 1024
  storage_mb: 2048
  gpus: 0
---

The file `/root/solution.py` defines `bsearch(arr, target)`, which should return
the index of `target` in the ascending-sorted list `arr`, or `-1` if `target` is
not present. It currently contains a bug.

Fix `bsearch` in place in `/root/solution.py`. Do not change its name or
signature. Do not add new files.
