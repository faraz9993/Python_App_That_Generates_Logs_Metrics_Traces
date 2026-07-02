# My Observability Service

FastAPI microservice demonstrating structured JSON logs, Prometheus/OpenMetrics metrics,
OpenTelemetry tracing, synthetic traffic generation, simulation endpoints, and downstream
service calls along with exemplars feature.

## Run Locally

```bash
cd my-observability-service
python3.13 -m venv .venv
source .venv/bin/activate
pip install .
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Useful endpoints:

- `GET /`
- `GET /api/service-info`
- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /api/orders`
- `POST /api/orders`
- `GET /api/customers`
- `GET /api/products`
- `GET /simulate/normal`
- `GET /simulate/error`
- `GET /simulate/latency`
- `GET /simulate/cpu`
- `GET /simulate/memory`

Example order:

```bash
curl -X POST http://localhost:8080/api/orders \
  -H 'content-type: application/json' \
  -d '{"customer_id":1,"items":[{"product_id":1,"quantity":1}]}'
```

## Grafana Cloud / Alloy

Set `OTEL_ENABLED=true` and point `OTEL_EXPORTER_OTLP_ENDPOINT` at your Grafana Alloy
OTLP gRPC receiver. When Alloy is installed in the `monitoring` namespace, use
`http://grafana-alloy.monitoring.svc.cluster.local:4317`. The service emits W3C trace
context through OpenTelemetry FastAPI and HTTPX instrumentation.

Logs are JSON on stdout and include `timestamp`, `level`, `event`, `service_name`,
`environment`, `trace_id`, `span_id`, request metadata, latency, and request ID.

Metrics are exposed from `/metrics` in OpenMetrics format for Prometheus-compatible
scrapers, including HTTP request counters/histograms and business counters.

### Exemplars

Exemplars attach a sample trace ID to a metric sample. In Grafana, this lets you jump
from a latency spike or error metric directly to the trace that produced it.

This service adds exemplars to HTTP latency histograms, HTTP request counters, business
counters, and downstream call counters when tracing is enabled.

Verify exemplars:

```bash
curl http://<app-host>/simulate/latency
curl http://<app-host>/metrics | grep trace_id
```

Example output:

```text
http_request_duration_seconds_bucket{...} 1.0 # {trace_id="...",span_id="..."} ...
```

In Grafana, use a graph panel backed by Mimir/Prometheus and enable exemplars for the
query. Tempo must contain the matching trace IDs.

To enable exemplars end to end in the LGTM stack, configure Alloy remote write to send
exemplars to Mimir:

```hcl
prometheus.remote_write "mimir" {
  endpoint {
    url            = "http://lgtm-mimir-nginx.monitoring.svc.cluster.local/api/v1/push"
    send_exemplars = true
  }
}
```

Configure Mimir to store exemplars in `lgtm-stack/helm/values-lgtm.local.yaml`:

```yaml
mimir:
  mimir:
    structuredConfig:
      limits:
        max_global_exemplars_per_user: 100000
```

The nested `mimir.mimir.structuredConfig` path is required by the LGTM Helm chart.

In Grafana, configure the Mimir/Prometheus datasource exemplar link:

```text
Internal link: enabled
Data source: Tempo
URL Label: trace_id
Label name: trace_id
```

Verify Alloy is forwarding exemplars:

```bash
kubectl port-forward -n monitoring svc/grafana-alloy 12345:12345
curl -s http://localhost:12345/metrics | grep prometheus_remote_storage_exemplars_total
```

Verify Mimir is storing exemplars:

```bash
kubectl port-forward -n monitoring svc/lgtm-mimir-nginx 9009:80
curl -G "http://localhost:9009/prometheus/api/v1/query_exemplars" \
  --data-urlencode 'query=http_request_duration_seconds_bucket' \
  --data-urlencode "start=$(date -u -d '15 minutes ago' +%s)" \
  --data-urlencode "end=$(date -u +%s)"
```

In Grafana Explore, select the Mimir datasource, enable exemplars, and query:

```promql
http_request_duration_seconds_bucket{service="my-observability-service", endpoint="/api/orders", le="0.005"}
```

For the local LGTM stack installed in the `monitoring` namespace, install Alloy with:

```bash
helm install grafana-alloy grafana/alloy -n monitoring -f helm/alloy-values.yaml
```

The application exports OTLP traces to:

```text
http://grafana-alloy.monitoring.svc.cluster.local:4317
```

## Deploy LGTM Stack

Clone the LGTM stack repository and add the Helm repositories:

```bash
git clone git@github.com:daviaraujocc/lgtm-stack.git
cd lgtm-stack

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

Create the monitoring namespace:

```bash
kubectl create ns monitoring
```

Install kube-prometheus-stack:

```bash
helm install prometheus-operator --version 66.3.1 -n monitoring \
  prometheus-community/kube-prometheus-stack -f helm/values-prometheus.yaml
```

Before installing LGTM, make sure Mimir exemplar storage is enabled in
`helm/values-lgtm.local.yaml`:

```yaml
mimir:
  mimir:
    structuredConfig:
      limits:
        max_global_exemplars_per_user: 100000
```

Install the LGTM stack:

```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.local.yaml
```

Install Grafana Alloy from the application repository so it can collect this service's
logs, metrics, and traces:

```bash
cd ../my-observability-service

helm install grafana-alloy grafana/alloy -n monitoring \
  -f helm/alloy-values.yaml
```

If the LGTM or Alloy values change later, use `helm upgrade`:

```bash
cd ../lgtm-stack
helm upgrade lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.local.yaml

cd ../my-observability-service
helm upgrade grafana-alloy grafana/alloy -n monitoring \
  -f helm/alloy-values.yaml
```

Verify the monitoring stack:

```bash
kubectl get all -n monitoring
kubectl get svc -n monitoring
```

Access Grafana:

```bash
kubectl port-forward -n monitoring svc/lgtm-grafana 3000:80
```

Open:

```text
http://localhost:3000
```

## Docker

```bash
docker build -t my-observability-service:latest .
docker run --rm -p 8080:8080 --env-file .env.example my-observability-service:latest
```

Access the application at:

- `http://localhost:8080/`
- `http://localhost:8080/docs`
- `http://localhost:8080/health`
- `http://localhost:8080/api/orders`
- `http://localhost:8080/metrics`

The root URL serves a lightweight dashboard for health, sample business data, and
simulation actions. FastAPI's Swagger UI remains available at `/docs`.

When exposed through the Kubernetes `LoadBalancer` service, access the application at:

```text
http://<load-balancer-hostname>/
```

## Kubernetes

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Deploy On EKS

Point `kubectl` at the EKS cluster:

```bash
aws eks update-kubeconfig --region ap-south-1 --name <eks-cluster-name>
kubectl get nodes
```

Make sure `k8s/deployment.yaml` points to an image that EKS can pull, for example:

```yaml
image: fansari9993/faraz_test_repo:local
```

If you changed the application code, rebuild and push the image first:

```bash
docker login
docker build -t fansari9993/faraz_test_repo:local .
docker push fansari9993/faraz_test_repo:local
```

Deploy the application:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/my-observability-service
```

Verify the pods and service:

```bash
kubectl get all
kubectl get svc my-observability-service
```

If the service type is `LoadBalancer`, wait for `EXTERNAL-IP` / hostname, then access:

```bash
curl http://<load-balancer-hostname>/
curl http://<load-balancer-hostname>/health
curl http://<load-balancer-hostname>/api/orders
```

### Docker Hub Image Push

If `k8s/deployment.yaml` points to Docker Hub, the image and tag must exist before EKS
can start the pod.

```bash
docker login
docker build -t fansari9993/faraz_test_repo:local .
docker push fansari9993/faraz_test_repo:local

kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/my-observability-service
```

Verify that Kubernetes is using the expected image:

```bash
kubectl get deployment my-observability-service \
  -o=jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

If the Docker Hub repository is private, create an image pull secret and attach it to
the deployment:

```bash
kubectl create secret docker-registry dockerhub-credentials \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-dockerhub-username> \
  --docker-password=<your-dockerhub-token> \
  --docker-email=<your-email>

kubectl patch deployment my-observability-service \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"dockerhub-credentials"}]}}}}'
```

### EKS Image Push

For EKS, `my-observability-service:latest` must exist in a registry that the cluster can
pull from. Push it to ECR, then update the deployment image:

```bash
AWS_ACCOUNT_ID=454143665149
AWS_REGION=ap-south-1
IMAGE_REPO=my-observability-service
IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_REPO:latest

aws ecr create-repository --repository-name $IMAGE_REPO --region $AWS_REGION || true
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t $IMAGE_REPO:latest .
docker tag $IMAGE_REPO:latest $IMAGE_URI
docker push $IMAGE_URI

kubectl set image deployment/my-observability-service app=$IMAGE_URI
kubectl rollout status deployment/my-observability-service
```

The `ErrImagePull` / `ImagePullBackOff` status means the pod has not started yet because
the node cannot pull the configured container image.
