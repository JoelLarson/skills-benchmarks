---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: hard
  category: reasoning
  subcategory: arithmetic
  category_confidence: high
  task_type: [reasoning]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [order-of-operations, tip-tax, precision]
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

A dinner bill is $186.40 before tax and tip.

Apply the following:
1. Add a tip of 18%, computed on the $186.40 pre-tax amount.
2. Add 7.25% sales tax, computed on the $186.40 pre-tax amount ONLY (the tip is
   not taxed, and the tax is not applied on top of the tip).
3. Split the resulting grand total evenly among 4 people.

Write the amount each person pays, rounded to the nearest cent, as a single
number to `/root/answer.txt` (for example: `12.34`). Write nothing else to that
file.
