# Filip Csupka — Technical Skills

## Stack overview (bottom-up, as Filip sees it)

Filip thinks about the platform stack in layers, each one standing on the ones below it:

### L0 — Linux / Network / Security (foundation)
Shell, networking, syscalls, firewalls, troubleshooting.
Tools: systemd, iptables, tcpdump, strace, bash, ssh.
"Ground truth — every layer above is just YAML over this."

### L1 — Compute / Cloud / VM
Hetzner Cloud, AKS (Azure Kubernetes Service), AWS, HUB/SPOKE private cloud, bare metal.
"Physical and virtual nodes joined into one fleet."

### L2 — Docker / Containers
OCI images, registries, container runtimes (containerd, CRI), GHCR.
"Ship the same artefact from laptop to production."

### L3 — Kubernetes / OpenShift (core expertise)
Schedulers, operators, lifecycle management, multi-tenant clusters, k3s, AKS.
"Self-healing workloads, declared not clicked."

### L4 — Helm / Packaging
Helm charts, Kustomize overlays, operators, sealed secrets, OLM.
"Version-pinned, reviewable, repeatable installs."

### L5 — IaC / Terraform
Terraform modules, state management, Ansible playbooks, idempotent provisioning.
"Infrastructure as a pull request."

### L6 — CI/CD Pipelines
GitHub Actions, GitLab CI, runners, build→test→image→push→tag pipelines.
"Every commit rides the same pipe."

### L7 — GitOps / ArgoCD (strong)
ArgoCD, App-of-Apps pattern, sync waves, drift detection, auto-sync.
"The cluster reconciles itself toward main."

### L8 — Data Services
Kafka, PostgreSQL, MongoDB, Kafka Connect.
"Events flow through services, debugged across teams."

### L9 — Observability
Prometheus, Grafana, Loki, Tempo, Grafana Alloy, distributed tracing, alerting.
"Answers before incidents grow up."

### L10 — AI / DevEx (growing fast)
Claude Code, Codex, MCP, agent skills. Self-hosted LLM inference. This chatbot.
"Supervised by reality, no matter how loud the AI."

---

## Skill levels (approximate)

- Orchestration (k8s/OpenShift/Helm/Docker): 92%
- GitOps & automation (ArgoCD/CI-CD/Terraform): 88%
- Observability (Prometheus/Grafana/Loki/Tempo): 84%
- Data & messaging (Kafka/PostgreSQL/MongoDB): 74%

---

## Certifications / knowledge areas

- OpenShift operations and upgrades (professional experience)
- AWS Solutions Architect Associate level knowledge
- Kubernetes CKA-level operational depth (from production, not just study)
