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
  tags: [sequential-discount, order-of-operations, precision]
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

An order is for 7 units priced at $42.50 each.

Apply the following, strictly in this order:
1. Compute the subtotal (units x unit price).
2. Apply a 12% bulk discount to the subtotal.
3. Subtract a $15.00 coupon from the discounted amount.
4. Add 6.5% sales tax on the amount from step 3.
5. Add a $4.99 handling fee (the handling fee is NOT taxed).

Write the final total, rounded to the nearest cent, as a single number to
`/root/answer.txt` (for example: `123.45`). Write nothing else to that file.
