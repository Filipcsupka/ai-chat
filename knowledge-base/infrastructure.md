# How This AI Chatbot Works — Infrastructure Deep Dive

This document explains the technical setup behind the AI chat you're using right now. Filip built it to learn the stack and flex a bit. Everything runs on his own hardware and infrastructure.

## Architecture overview

```
You (browser on filipcsupka.online)
  │
  │  HTTPS request to ai.filipcsupka.online/chat
  ▼
Cloudflare CDN/proxy
  │
  ▼
Hetzner VPS — 178.104.235.97
  k3s control plane node ("family-webapp")
  Traefik ingress controller (hostPort 80/443)
  │
  │  Routes to rag-api Service via k8s cluster DNS
  │  (cross-node traffic via Tailscale flannel)
  ▼
Home PC — GPU node ("k3sgpu") — Tailscale IP 100.86.152.16
  Ubuntu 26.04 LTS, 30GB RAM, NVIDIA GeForce RTX 2070 (8GB VRAM, CUDA 7.5)
  ┌─────────────────────────────────────────────────────┐
  │  k3s GPU worker node                                │
  │                                                     │
  │  [rag-api pod]          [chromadb pod]              │
  │    FastAPI service        Vector database           │
  │    RAG pipeline           ChromaDB                 │
  │    ↕ HTTP                 ↕ HTTP                   │
  │                                                     │
  │  [Ollama — host process, systemd service]           │
  │    LLM inference engine                             │
  │    Models: qwen3:8b, deepseek-coder, mistral        │
  │    GPU: RTX 2070 (CUDA, full VRAM utilization)     │
  └─────────────────────────────────────────────────────┘
```

## What happens when you send a message

1. **You type a question** in the chat widget on filipcsupka.online
2. **Your browser** sends a POST request to `https://ai.filipcsupka.online/chat` (JavaScript fetch)
3. **Cloudflare** proxies the request to the Hetzner VPS (178.104.235.97)
4. **Traefik** (ingress controller on k3s) receives the HTTPS request, terminates TLS, routes to the `rag-api` Kubernetes Service
5. **Cross-node routing**: the request travels from Hetzner to the home GPU node via Tailscale VPN (flannel overlay network)
6. **RAG API** (FastAPI, Python) receives the request and runs the RAG pipeline:
   a. **Embeds your query**: calls Ollama's embedding endpoint with `nomic-embed-text` model → gets a vector (numerical representation of your question)
   b. **Semantic search**: queries ChromaDB with that vector → retrieves the 3-5 most relevant knowledge chunks from the knowledge base
   c. **Builds context prompt**: assembles a prompt with the retrieved chunks + your question + system instructions
   d. **LLM generation**: calls Ollama with `qwen3:8b` model → the model generates a response using the context
7. **Response** travels back through the same path to your browser
8. **Chat widget** displays the answer

## Components

### Ollama (LLM inference runtime)
- Runs as a systemd service on the GPU node host
- Manages GPU memory, model loading/unloading
- Exposes OpenAI-compatible REST API on port 11434
- Configured with `OLLAMA_HOST=0.0.0.0` (accessible from k8s pods)

### qwen3:8b (chat model)
- 8 billion parameter Qwen 3 model from Alibaba
- 5.2GB on disk, runs fully in VRAM (RTX 2070 has 8GB)
- Handles: question answering, context understanding, natural language generation
- Supports both English and Slovak

### nomic-embed-text (embedding model)
- Lightweight embedding model (~274MB)
- Converts text into 768-dimensional vectors
- Used for: embedding the knowledge base chunks and embedding your queries

### ChromaDB (vector database)
- Open-source embedding database
- Stores embedded knowledge chunks with metadata
- Similarity search: finds chunks most relevant to your query
- Runs as a k8s pod on the GPU node, data persisted via PVC

### RAG API (FastAPI)
- Python service implementing the Retrieval-Augmented Generation pipeline
- On startup: loads knowledge base markdown files, chunks them, embeds each chunk, stores in ChromaDB
- On each chat request: embed query → retrieve → generate → respond
- Exposes POST /chat endpoint with CORS for filipcsupka.online
- Runs as a k8s pod on the GPU node

### k3s cluster
- Lightweight Kubernetes distribution
- Control plane on Hetzner VPS (public cloud, stable, always-on)
- GPU worker node on home gaming PC (connected via Tailscale)
- GitOps: all deployments managed by ArgoCD from GitHub

### Traefik ingress
- Receives traffic on hostPort 80/443 on the Hetzner VPS
- TLS terminated with Let's Encrypt certificates (via cert-manager)
- Routes `ai.filipcsupka.online` to the RAG API service

### Tailscale VPN
- Creates a private encrypted mesh network between nodes
- Hetzner node and home GPU node are on the same Tailscale tailnet
- k3s uses Tailscale interface (tailscale0) as the flannel backend for pod networking
- The GPU node has no public IP — it's only reachable via Tailscale

## GPU details

- NVIDIA GeForce RTX 2070 (consumer gaming GPU)
- 8192 MiB VRAM (8GB)
- CUDA compute capability 7.5
- Driver: 595.71.05
- Used for: LLM inference (Ollama runs models on GPU, massive speedup over CPU)
- GPU scheduling in k3s: nvidia-device-plugin allocates `nvidia.com/gpu: 1` resource

## Why home GPU vs cloud GPU

Cloud GPU (e.g. AWS p3, GCP A100): $2-10/hour, no upfront cost, disposable
Home RTX 2070: already owned (gaming PC), runs 24/7 for ~$20/month electricity
For a personal project with low traffic: home GPU wins on cost and is more fun to operate.

## Knowledge base (RAG source)

The chatbot knows about Filip because of markdown files stored in the `ai-chat` GitHub repository. When the RAG API starts, it reads these files, splits them into chunks (~500 tokens each), embeds each chunk with `nomic-embed-text`, and stores everything in ChromaDB.

Files:
- `profile.md` — who Filip is, contact, summary
- `experience.md` — work history
- `skills.md` — technical skills by layer
- `projects.md` — side projects including this chatbot
- `personal.md` — weekends, MTB, family, personality
- `infrastructure.md` — this file (how the chatbot works)

To update what the chatbot knows: edit a markdown file → push to GitHub → GitHub Actions rebuilds the Docker image → ArgoCD syncs → new pod starts with fresh knowledge.
