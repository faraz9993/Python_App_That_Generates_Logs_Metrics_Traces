# My Observability Service

FastAPI microservice demonstrating structured JSON logs, Prometheus/OpenMetrics metrics,
OpenTelemetry tracing, synthetic traffic generation, simulation endpoints, and downstream
service calls.

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
OTLP gRPC receiver, for example `http://grafana-alloy:4317` in Kubernetes. The service
emits W3C trace context through OpenTelemetry FastAPI and HTTPX instrumentation.

Logs are JSON on stdout and include `timestamp`, `level`, `event`, `service_name`,
`environment`, `trace_id`, `span_id`, request metadata, latency, and request ID.

Metrics are exposed from `/metrics` in OpenMetrics format for Prometheus-compatible
scrapers, including HTTP request counters/histograms and business counters.

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

## Kubernetes

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
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
