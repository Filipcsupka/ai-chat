# ai-chat

Self-hosted RAG chatbot for [filipcsupka.online](https://filipcsupka.online).

Runs entirely on a home NVIDIA RTX 2070 connected to a k3s cluster via Tailscale.
No OpenAI. No monthly API bill. Just a gaming PC doing LLM inference in a Kubernetes pod.

## What's in here

```
knowledge-base/   Markdown files — what the chatbot knows about Filip
rag-api/          Python FastAPI service — RAG pipeline (embed → retrieve → generate)
docs/setup.md     Full setup guide (step-by-step, written for future-Filip)
.github/          CI: build Docker image, sync knowledge base to infra repo
```

## How it works

1. **Knowledge base** — markdown files describing Filip's experience, skills, projects, personal info
2. **Embeddings** — `nomic-embed-text` via Ollama converts text chunks to vectors
3. **ChromaDB** — stores embedded chunks, does cosine similarity search
4. **Generation** — `qwen3:8b` via Ollama reads retrieved context and answers the question
5. **RAG API** — FastAPI service tying it together, exposed at `ai.filipcsupka.online`
6. **Chat widget** — React component on the CV site calling the API from the browser

## Infrastructure

- GPU node: home PC, Ubuntu 26.04, RTX 2070 (8GB VRAM), 30GB RAM
- Ollama: systemd service on GPU node host, `OLLAMA_HOST=0.0.0.0`
- k3s: GPU node is a worker in the Hetzner k3s cluster (joined via Tailscale)
- ChromaDB + RAG API: k8s pods on GPU node, managed by ArgoCD
- Ingress: Traefik on Hetzner VPS, TLS via cert-manager + Let's Encrypt
- Cloudflare: proxies `ai.filipcsupka.online` → `178.104.235.97`

## CI/CD flow

```
Push to main
  → GitHub Actions builds rag-api Docker image → GHCR
  → Updates knowledge-base ConfigMap in Filipcsupka/infra repo
  → Updates image tag in infra/gitops/apps/ai-chat/overlays/prod/
  → ArgoCD auto-syncs → new pod starts → ingests knowledge base
```

## Setup

See [docs/setup.md](docs/setup.md) — it covers everything including the one manual step (pull embedding model on GPU node).

## Updating what the chatbot knows

Edit any file in `knowledge-base/`, push to main. CI does the rest.
