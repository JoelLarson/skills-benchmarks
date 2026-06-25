---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: easy
  category: reasoning
  subcategory: data-parsing
  category_confidence: high
  task_type: [reasoning]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [parsing, filter, attention]
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

`/root/employees.json` is a JSON array of employee records, each with `name`,
`dept`, and `salary`.

Among employees in the `Engineering` department, find the one with the highest
salary. Write that employee's `name` (exactly, nothing else) to
`/root/answer.txt`.
