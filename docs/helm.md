# Enterprise Scaling via Helm

TLCM splits its ingestion logic. When your AI agent calls `remember()`, the memory enters the Tier-1 Short Term Memory queue asynchronously. 

For high-scale production, you cannot run SQLite concurrently across multiple pods effectively.

### Deploying the Helm Chart

Inside the `/helm-charts/tlcm-engine` directory, you will find the standard configuration.

```bash
helm install my-engine ./helm-charts/tlcm-engine --values my-enterprise-values.yaml
```

**my-enterprise-values.yaml**:
```yaml
replicaCount: 5  # Scale the Async Bus and API handlers
env:
  COGNITION_BACKEND: "openai"
  VECTOR_STORE_PROVIDER: "qdrant"
  RELATIONAL_STORE_PROVIDER: "postgres"
  TLCM_API_KEY: "secretk8skey"
persistence:
  enabled: false # Ensure state is offloaded to remote DBs (Postgres/Qdrant)
```

Since the Node runtime uses asynchronous bridging, adding `replicaCount: 5` automatically spreads STM-to-LTM queue processing evenly across nodes.
