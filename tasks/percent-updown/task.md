---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: medium
  category: reasoning
  subcategory: arithmetic
  category_confidence: high
  task_type: [reasoning]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [arithmetic, trap, precision]
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

A quantity starts at 80. It is first increased by 25%, and then that result is
decreased by 25%. What is the final value? Write it as a single number to
`/root/answer.txt` (nothing else).
