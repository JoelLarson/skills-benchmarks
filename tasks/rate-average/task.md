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

A car drives from town A to town B at a constant 60 mph, then immediately returns
from B to A along the same route at a constant 40 mph. What is the car's average
speed over the entire round trip, in mph? Write the answer as a single number to
`/root/answer.txt` (nothing else).
