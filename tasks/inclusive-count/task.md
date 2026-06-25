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

How many integers are there from 7 to 23, inclusive? Write the count as a single
integer to `/root/answer.txt` (nothing else).
