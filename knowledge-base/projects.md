# Filip Csupka — Side Projects

## vevsdesign.sk — wife's design studio

A website for his wife's graphic design studio. Hosted on the same Hetzner Kubernetes cluster as his CV, deployed through the same ArgoCD GitOps pipeline. Same pipeline, different namespace. Because a simple VPS would be suspiciously reasonable.

URL: https://vevsdesign.sk
Stack: Next.js, Docker, k3s, ArgoCD, Cloudflare, Traefik, cert-manager, Let's Encrypt

---

## filip-cv — this very website (filipcsupka.online)

The CV website you're currently visiting. Built as a Next.js static export, served by nginx, deployed via GitOps/ArgoCD to a Hetzner k3s cluster.

URL: https://filipcsupka.online
GitHub: https://github.com/Filipcsupka/cv-web
Stack: Next.js 15, React 19, TypeScript, Tailwind v4, nginx, Docker, Kubernetes, Cloudflare

---

## Home lab cluster — personal Kubernetes platform

A production-style Kubernetes cluster running on Hetzner Cloud (control plane + public workloads) with a home GPU worker node (NVIDIA RTX 2070) connected via Tailscale VPN. Not a toy — it runs real websites, GitOps delivery, monitoring, and now AI inference.

Infrastructure:
- Hetzner VPS (cx22, nbg1): k3s control plane + worker for public apps
- Home gaming PC: k3s GPU worker, Ubuntu 26.04, 30GB RAM, RTX 2070 (8GB VRAM)
- Tailscale: private VPN mesh connecting home GPU node to Hetzner node
- Terraform: provisions Hetzner resources (one `terraform apply` from zero to cluster)
- Ansible: configures k3s, Traefik, cert-manager, GPU worker join
- ArgoCD: GitOps delivery, auto-sync from GitHub
- Traefik: ingress controller with Let's Encrypt TLS via cert-manager
- Prometheus + Grafana: monitoring

---

## AI Chat (this chatbot) — self-hosted RAG on home GPU

The chatbot you're talking to right now. It runs entirely on Filip's home gaming PC, not on any cloud AI service. No OpenAI API calls, no monthly subscription, fully under control.

Technical details:
- Ollama: LLM inference runtime on the GPU node (RTX 2070, 8GB VRAM, CUDA 7.5)
- Model: qwen3:8b (5.2GB, runs fully on GPU)
- Embeddings: nomic-embed-text via Ollama (for semantic search)
- ChromaDB: vector database storing embedded knowledge chunks
- RAG API: Python FastAPI service that handles: embed query → retrieve context → generate answer
- Knowledge base: markdown files about Filip (this very file system)
- Deployment: k8s pod on GPU node, managed by ArgoCD, connected to cv-web via Traefik ingress at ai.filipcsupka.online
- The CV website (static nginx) calls the RAG API directly from the browser

Why: to learn the full AI inference stack — model serving, RAG pipelines, vector databases, GPU scheduling in Kubernetes — and to flex a bit.
