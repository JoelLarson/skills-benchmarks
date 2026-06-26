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
  tags: [order-of-operations, pre-post-tax, precision]
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

An employee's monthly gross pay is $5,200.00. Compute net pay by applying,
strictly in this order:
1. Deduct a 401(k) contribution equal to 6% of gross pay. This is pre-tax.
2. Apply 22% federal income tax to the amount remaining after the 401(k)
   deduction (i.e. tax is computed on the post-401(k) amount).
3. Subtract a flat $180.00 for health insurance. This is a post-tax deduction.

Write the final net pay, rounded to the nearest cent, as a single number to
`/root/answer.txt` (for example: `123.45`). Write nothing else to that file.
