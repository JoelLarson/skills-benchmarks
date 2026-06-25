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
  tags: [arithmetic, sequential-discount, precision]
verifier:
  type: test-script
  timeout_sec: 300
  service: main
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 600
environment:
  network_mode: none
  build_timeout_sec: 600
  os: linux
  cpus: 1
  memory_mb: 1024
  storage_mb: 2048
  gpus: 0
---

A widget has a list price of $480.00.

Apply the following in order:
1. A 15% discount off the list price.
2. A further 20% discount off the price from step 1.
3. An 8.25% sales tax on the price from step 2.

Write the final price, rounded to the nearest cent, as a single number to
`/root/answer.txt` (for example: `123.45`). Write nothing else to that file.
