# AI Chat — Setup Guide

This doc covers everything needed to get the RAG chatbot running from scratch.
Everything that CAN be automated IS automated (GitHub Actions + ArgoCD).
What requires SSH is written step by step — even if you forget everything.

---

## Prerequisites checklist

Before starting, make sure you have:

- [ ] k3s cluster running (both nodes Ready — verify with `KUBECONFIG=infra/kubeconfig.yaml kubectl get nodes`)
- [ ] ArgoCD running (`kubectl -n argocd get pods` — all Running)
- [ ] Tailscale connected on both nodes (verify: `ping 100.86.152.16` from Hetzner node)
- [ ] GHCR access (GitHub token with `packages:write` on Filipcsupka account)
- [ ] GitHub repo `Filipcsupka/ai-chat` created (push this directory to it)
- [ ] GitHub secret `INFRA_REPO_PAT` set in the `ai-chat` repo (PAT with `repo` write on `Filipcsupka/infra`)

---

## Step 1 — GPU node: pull the embedding model

SSH into the GPU node and pull `nomic-embed-text`. The chat model (`qwen3:8b`) is already installed.

```bash
ssh -i ~/.ssh/hetzner_ed25519 ja@100.86.152.16
```

Once connected:

```bash
# Pull the embedding model (~274MB, fast)
ollama pull nomic-embed-text

# Verify both models are present
ollama list
# Expected output includes:
#   qwen3:8b          (5.2 GB)   ← chat model
#   nomic-embed-text  (274 MB)   ← embedding model

# Confirm Ollama listens on all interfaces (should already be set)
cat /etc/systemd/system/ollama.service.d/override.conf
# Expected: Environment="OLLAMA_HOST=0.0.0.0"

# Quick API test (from the GPU node itself)
curl http://localhost:11434/api/tags
# Should return JSON listing installed models

exit
```

---

## Step 2 — Verify Ollama reachable from Hetzner node

From your local machine (or the Hetzner node):

```bash
# From local (Tailscale must be connected on your machine too, or use SSH tunnel)
curl http://100.86.152.16:11434/api/tags

# Or via SSH to the Hetzner node first, then test cluster-internal access
ssh -i ~/.ssh/hetzner_ed25519 root@178.104.235.97 \
  "curl -s http://100.86.152.16:11434/api/tags | head -c 200"
```

If this fails, check Tailscale status on both nodes:
```bash
ssh -i ~/.ssh/hetzner_ed25519 root@178.104.235.97 "tailscale status"
ssh -i ~/.ssh/hetzner_ed25519 ja@100.86.152.16 "tailscale status"
```

---

## Step 3 — Cloudflare: add DNS record

In the Cloudflare dashboard for `filipcsupka.online`:

1. Go to DNS → Records
2. Add an **A record**:
   - **Name**: `ai`
   - **IPv4 address**: `178.104.235.97`  (Hetzner VPS public IP)
   - **Proxy status**: Proxied (orange cloud) ← important for HTTPS
3. Save

This creates `ai.filipcsupka.online` → Hetzner → Traefik → RAG API.

> Note: Cloudflare SSL/TLS mode must be **Flexible** or **Full** (not Full Strict)
> because cert-manager handles the origin certificate, not Cloudflare.

---

## Step 4 — GitHub: create the ai-chat repo and push

```bash
cd /Users/filipcsupka/moje/ai-chat

# Init git repo
git init
git add .
git commit -m "feat: initial ai-chat RAG API and knowledge base"

# Create GitHub repo (requires gh CLI)
gh repo create Filipcsupka/ai-chat --public --push --source=.
```

Or create via GitHub UI and push manually.

---

## Step 5 — GitHub: add the INFRA_REPO_PAT secret

The CI needs to push to `Filipcsupka/infra` to update the ConfigMap and image tag.

1. Go to github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Create token:
   - Resource owner: Filipcsupka
   - Repository access: Only selected → `Filipcsupka/infra`
   - Permissions: Contents → Read and write
3. Copy the token
4. In the `ai-chat` repo → Settings → Secrets → Actions → New repository secret
   - Name: `INFRA_REPO_PAT`
   - Value: the token you copied

---

## Step 6 — Trigger the first CI build

Push to main in the `ai-chat` repo (already done in step 4). GitHub Actions will:

1. Build the `rag-api` Docker image → push to GHCR
2. Update `knowledge-base-cm.yaml` in the `infra` repo with latest markdown files
3. Update image tag in `infra/gitops/apps/ai-chat/overlays/prod/kustomization.yaml`

Monitor progress at: `github.com/Filipcsupka/ai-chat/actions`

---

## Step 7 — Deploy ArgoCD app

```bash
KUBECONFIG=/Users/filipcsupka/moje/infra/kubeconfig.yaml \
  kubectl apply -f /Users/filipcsupka/moje/infra/argocd/apps/ai-chat.yaml
```

ArgoCD will sync `gitops/apps/ai-chat/overlays/prod` and create:
- Namespace `ai-chat`
- Ollama Service + Endpoints (pointing to GPU node host)
- ChromaDB Deployment + PVC
- RAG API Deployment + Service + Ingress

Watch sync progress:
```bash
KUBECONFIG=/Users/filipcsupka/moje/infra/kubeconfig.yaml \
  kubectl -n ai-chat get pods -w
```

Expected final state (takes ~2-3 minutes):
```
NAME                        READY   STATUS    
chromadb-xxx                1/1     Running   
rag-api-xxx                 1/1     Running   
```

---

## Step 8 — Verify end-to-end

```bash
# 1. Health check (should return {"status":"ok"})
curl https://ai.filipcsupka.online/health

# 2. Readiness (should return chunks count after ingestion completes)
curl https://ai.filipcsupka.online/ready

# 3. Test chat (sync endpoint, no streaming)
curl -X POST https://ai.filipcsupka.online/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "What does Filip do on weekends?"}'

# 4. Test streaming (should stream SSE tokens)
curl -N -X POST https://ai.filipcsupka.online/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Filip good at?"}'
```

---

## Troubleshooting

### RAG API pod not starting

```bash
KUBECONFIG=infra/kubeconfig.yaml kubectl -n ai-chat describe pod -l app=rag-api
KUBECONFIG=infra/kubeconfig.yaml kubectl -n ai-chat logs -l app=rag-api
```

Common cause: ChromaDB not ready yet. RAG API readiness probe retries for 2 minutes.

### Ingestion fails (Ollama unreachable)

```bash
# Check Ollama endpoint is accessible from a pod on the GPU node
KUBECONFIG=infra/kubeconfig.yaml kubectl -n ai-chat run test --rm -it \
  --image=curlimages/curl --restart=Never --overrides='{"spec":{"nodeSelector":{"accelerator":"nvidia"},"tolerations":[{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}' \
  -- curl http://ollama.ai-chat.svc.cluster.local:11434/api/tags
```

If this fails, the Endpoints object IP (`100.86.152.16`) is not reachable. Check Tailscale.

### ChromaDB data lost after pod restart

The PVC persists data. If PVC was deleted, RAG API will re-ingest on next startup (~60s). This is expected and logged.

### Certificate not issued

```bash
KUBECONFIG=infra/kubeconfig.yaml kubectl -n ai-chat describe certificate rag-api-tls
KUBECONFIG=infra/kubeconfig.yaml kubectl -n ai-chat describe certificaterequest
```

cert-manager uses HTTP-01 challenge via Traefik. Cloudflare must be in Flexible mode (not Full Strict) for the ACME challenge to succeed on first issuance.

---

## Day-2 operations

### Update knowledge base

1. Edit markdown files in `knowledge-base/`
2. `git commit && git push`
3. CI rebuilds image + updates ConfigMap in infra
4. ArgoCD re-deploys RAG API pod
5. New pod ingests updated knowledge base on startup (~60s)

### Add a new model

```bash
ssh -i ~/.ssh/hetzner_ed25519 ja@100.86.152.16
ollama pull <model-name>
```

Then update `OLLAMA_CHAT_MODEL` env var in `gitops/apps/ai-chat/base/rag-api.yaml` and push.

### Check GPU utilization during inference

```bash
ssh -i ~/.ssh/hetzner_ed25519 ja@100.86.152.16 "nvidia-smi"
```

### Manual ingestion trigger (without redeployment)

```bash
curl -X POST https://ai.filipcsupka.online/ingest
```
