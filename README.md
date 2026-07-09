# My Observability Service

FastAPI microservice demonstrating structured JSON logs, Prometheus/OpenMetrics metrics,
OpenTelemetry tracing, synthetic traffic generation, simulation endpoints, and downstream
service calls along with exemplars feature.

> In this document you can:
1. [Run Application Locally](#run-application-locally)
2. [Deploy Application on Docker](#deploy-application-on-docker)
3. [Deploy Application on Kubernetes](#deploy-application-on-kubernetes)
4. [Deployment of LGTM Stack on EKS](#deployment-of-lgtm-stack-on-eks)
5. [Deployment of Exemplars](#deployment-of-exemplars)
6. [For Troublshooting](#for-troublshooting)

## Run Application Locally

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

## Deploy Application on Docker

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

## Deploy Application on Kubernetes

### Prerequisites / Assumptions

- AWS CLI configured with sufficient IAM permissions (EKS, EC2, IAM, Route53/Resolver)
- `kubectl`, `helm`, `eksctl` installed
- A VPC with at least 2 subnets across 2 AZs, public IPs enabled on nodes (or NAT configured)
- Region used in original setup: `ap-south-1`

---

### Create / Size the EKS Cluster Node Group Correctly

The LGTM stack + Prometheus stack deploys **~30+ pods**. `t3.medium` only supports **~17 pods/node**
(ENI/IP limit, not CPU/memory). Undersizing causes `0/N nodes available: Too many pods` errors.

**Recommended node group sizing:**
- Instance type: `c6i.large` (or larger, e.g. `t3.large` for fewer total nodes)
- Desired size: **3**
- Minimum size: **2**
- Maximum size: **3**
---
Once, EKS Cluster is created, run below three commands:

```bash
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl rollout status deployment/postgres

kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/my-observability-service
```

The application will be deployed in the default namespace.

You can get the Loadbalancer url of the service using below command:
```bash
kubectl get svc | grep my-observability-service
```

You can use the below command to check whether your app is generating logs and metrics and has trace ids.
```bash
kubectl logs -l app=my-observability-service --tail=50 | grep -i database
curl http://<LOAD_BALANCER_URL>/metrics | grep db_calls_total
```

## Deployment of LGTM Stack on EKS

This runbook captures everything needed to deploy the LGTM stack (Loki, Grafana, Tempo, Mimir)
on a **fresh** EKS cluster, including environment-specific fixes discovered during the first
deployment. Follow these in order — skipping steps will reproduce the same failures.

## Install EBS CSI Driver Add-on (Required for PVCs)

EKS does **not** ship the EBS CSI driver by default. Without it, all PVCs (MinIO, Mimir
ingester/compactor/store-gateway) stay `Pending` forever.

### Associate IAM OIDC provider with the cluster
```bash
eksctl utils associate-iam-oidc-provider --cluster <CLUSTER_NAME> --approve
```

### Create IAM service account + role for the CSI driver
> Use a **cluster-specific role name** to avoid collisions in shared AWS accounts
> (a generic name like `AmazonEKS_EBS_CSI_DriverRole` may already exist, owned by a
> different cluster's CloudFormation stack).

```bash
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster <CLUSTER_NAME> \
  --role-name <CLUSTER_NAME>_EBS_CSI_DriverRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --override-existing-serviceaccounts
```

### Install the add-on with that role attached
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws eks create-addon \
  --cluster-name <CLUSTER_NAME> \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/<CLUSTER_NAME>_EBS_CSI_DriverRole \
  --resolve-conflicts OVERWRITE
```

### Verify
```bash
kubectl get pods -n kube-system | grep ebs-csi
```
Expect `ebs-csi-controller-*` pods at `6/6 Running` and `ebs-csi-node-*` at `3/3 Running`.

If controller pods crash with `no EC2 IMDS role found` or STS/DNS errors — see [Fix STS VPC Endpoint](#fix-sts-vpc-endpoint) 

If all controller pods are `6/6 Running` and `3/3 Running` - jump directly to [Deploy the LGTM Stack](#deploy-the-lgtm-stack).

---

## Fix STS VPC Endpoint

**Symptom:** EBS CSI controller (and anything else doing AWS API calls via IRSA) fails with:
```
no EC2 IMDS role found
```
or, after DNS partially resolves:
```
dial tcp <private-ip>:443: i/o timeout
```

**Root cause found in our environment:** This AWS account has a pre-existing STS Interface
VPC Endpoint (`com.amazonaws.<region>.sts`) with **Private DNS enabled**, which silently
overrides public DNS resolution for `sts.<region>.amazonaws.com` inside the VPC. But the
endpoint had:
1. **Zero subnets / zero ENIs** configured — so Private DNS had nothing to resolve to (empty/NODATA responses)
2. Even after adding subnets, its **security group only allowed 443 from `10.0.0.0/16`**, not the VPC's actual CIDR (`172.31.0.0/16`) — so the connection still timed out

**This is an account/VPC-level config issue, not something Helm or EKS sets up — check for
it on every fresh cluster in this same AWS account/VPC.**

### Check if an STS VPC endpoint exists and its current state
```bash
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query "VpcEndpoints[*].[VpcEndpointId,ServiceName,State,PrivateDnsEnabled]" \
  --output table
```
Look for `com.amazonaws.<region>.sts`.

### Check its subnets/ENIs
```bash
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids <STS_ENDPOINT_ID> \
  --query "VpcEndpoints[0].[SubnetIds,NetworkInterfaceIds]"
```
If both are empty `[]`, the endpoint has no network presence — fix below.

### Add your node group's subnets to the endpoint
Get your node group's subnets (EKS Console → Node group → Details → Subnets, or):
```bash
aws eks describe-nodegroup --cluster-name <CLUSTER_NAME> --nodegroup-name <NODEGROUP_NAME> \
  --query "nodegroup.subnets"
```
Then:
```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id <STS_ENDPOINT_ID> \
  --add-subnet-ids <subnet-1> <subnet-2>
```

### Fix the endpoint's security group to allow 443 from your nodes
Check current rules:
```bash
aws ec2 describe-security-groups --group-ids <ENDPOINT_SG_ID> --query "SecurityGroups[0].IpPermissions"
```
Get your EKS cluster security group (the one auto-named `eks-cluster-sg-<cluster>-...`):
```bash
aws ec2 describe-instances \
  --filters "Name=private-dns-name,Values=<any-node-private-dns-name>" \
  --query "Reservations[0].Instances[0].SecurityGroups"
```
Add the rule:
```bash
aws ec2 authorize-security-group-ingress \
  --group-id <ENDPOINT_SG_ID> \
  --protocol tcp \
  --port 443 \
  --source-group <EKS_CLUSTER_SG_ID>
```

### Verify DNS resolves to a private IP from inside the cluster
```bash
kubectl run debug --image=busybox --restart=Never -- sleep 3600
sleep 5
kubectl exec -it debug -- nslookup sts.<region>.amazonaws.com
kubectl delete pod debug
```
Expect a `172.31.x.x` (or your VPC CIDR) private IP, not empty and not a public IP.

### Restart the EBS CSI controller to pick up working STS access
```bash
kubectl rollout restart deployment ebs-csi-controller -n kube-system
kubectl get pods -n kube-system | grep ebs-csi
```
Expect `6/6 Running`.

---

## Deploy the LGTM Stack

### Clone repo and add Helm repos
```bash
git clone git@github.com:daviaraujocc/lgtm-stack.git
cd lgtm-stack

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

kubectl create ns monitoring
```

### Install Prometheus Operator (CRDs + metrics)
```bash
helm install prometheus-operator --version 66.3.1 -n monitoring \
  prometheus-community/kube-prometheus-stack -f helm/values-prometheus.yaml
```

### Install LGTM stack
```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.local.yaml
```
> LGTM will be deployed in a namespace named **monitoring**

> If this is your first install attempt with the STS fix already in place, it should
> complete without timing out (the `lgtm-minio-post-job` hook depends on MinIO's PVC
> binding, which depends on the EBS CSI driver, which depends on STS access).
---

## Post-Install: Fix Tempo's Missing Bucket

**Known issue with this chart:** Mimir's Helm release includes a `make-minio-buckets` Job that
auto-creates Mimir's buckets (`mimir-tsdb`, `mimir-ruler`) — but there's **no equivalent job for
Tempo's bucket** (`tempo`). Tempo pods will crash-loop with:
```
unexpected error from ListObjects on tempo: The specified bucket does not exist
```

Check if the pvc is in **Pending** state or **Bound**:
```
kubectl get pvc -n monitoring
```

If they are in **Pending** state, run the below command
```
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Now, check again:
```
kubectl get pvc -n monitoring
```

### Get MinIO credentials
```bash
kubectl get secret lgtm-minio -n monitoring -o jsonpath='{.data.rootUser}' | base64 -d; echo
kubectl get secret lgtm-minio -n monitoring -o jsonpath='{.data.rootPassword}' | base64 -d; echo
```

### Create the `tempo` bucket manually
```bash
kubectl exec -it <lgtm-minio-pod-name> -n monitoring -- sh
```
Inside the pod:
```bash
export HOME=/tmp
mc alias set local http://localhost:9000 <root-user> <root-password>
mc mb local/tempo
mc ls local
exit
```

### Restart Tempo pods to pick up the new bucket
```bash
kubectl delete pod -n monitoring -l app.kubernetes.io/name=tempo
```
(Or delete each `lgtm-tempo-*` pod individually if the label selector doesn't match.)

### Verify
```bash
kubectl get pods -n monitoring | grep tempo
```
All Tempo pods should reach `1/1 Running` within ~1-2 minutes.

---

### Install Alloy

For the LGTM stack installed in the `monitoring` namespace, install Alloy with:

```bash
helm install grafana-alloy grafana/alloy -n monitoring -f helm/alloy-values.yaml
```

### Verify Everything Is Healthy

```bash
kubectl get pods -n monitoring
kubectl get pvc -n monitoring
```

Expect all PVCs `Bound`, all pods `Running` (except the one-shot `*-make-minio-buckets-*` job,
which should show `Completed`).

---

## Access Grafana

### Method 1:
```bash
kubectl port-forward svc/lgtm-grafana -n monitoring 3000:80
```
Open: `http://localhost:3000`

### Method 2:
Get the **lgtm-grafana** service type LoadBalancer:
```bash
kubectl patch svc lgtm-grafana -n monitoring -p '{"spec": {"type": "LoadBalancer"}}'
```

Wait for 5 minutes for load balancer to get create then enter hit the below command to get the external IP:
```
kubectl get svc lgtm-grafana -n monitoring
curl: http://<EXTERNAL_IP>
```

To get admin credentials:
```bash
kubectl get secret lgtm-grafana -n monitoring -o jsonpath='{.data.admin-user}' | base64 -d; echo
kubectl get secret lgtm-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

In Grafana: **Explore** → confirm Mimir, Loki, and Tempo data sources all query successfully.

---

## Deployment of Exemplars

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

Verify Alloy is forwarding exemplars:

```bash
kubectl port-forward -n monitoring svc/grafana-alloy 12345:12345
curl -s http://localhost:12345/metrics | grep prometheus_remote_storage_exemplars_total
```

Verify Mimir is storing exemplars:

```bash
kubectl port-forward -n monitoring svc/lgtm-mimir-nginx 9009:80
```
```bash
curl -G "http://localhost:9009/prometheus/api/v1/query_exemplars" \
  --data-urlencode 'query=http_request_duration_seconds_bucket' \
  --data-urlencode "start=$(date -u -d '15 minutes ago' +%s)" \
  --data-urlencode "end=$(date -u +%s)"
```

In Grafana, configure new Prometheus datasource for Mimir:

```text
Name: Mimir-2
Prometheus server URL: http://lgtm-mimir-nginx/prometheus

Exemplars:
Internal link: enabled
Data source: Tempo
URL Label: trace_id
Label name: trace_id
```
> **Save & Test** then click on **Explore View**.

In Grafana Explore, select the **Mimir-2** datasource, then click on **code** and enter below mentioned promql query:

```promql
http_request_duration_seconds_bucket{service="my-observability-service", endpoint="/api/orders", le="0.005"}
```

Under **Options** sections:
```
Legend: Auto
Format: Time Series
Type: Range
Exemplers: Enable
```
click on **Run Query** then you will be able to see diamonds on X-axis click on it.

The application exports OTLP traces to:

```text
http://grafana-alloy.monitoring.svc.cluster.local:4317
```

# For Troublshooting:

### Docker Hub Image Push

If `k8s/deployment.yaml` points to Docker Hub, the image and tag must exist before EKS
can start the pod.

```bash
docker login
docker build -t fansari9993/faraz_test_repo:db-v1 .
docker push fansari9993/faraz_test_repo:db-v1

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

### General Flow For Metrics:
```
Application Level Metrics > Grafana Alloy > Mimir
Infrastructure/cluster Level Metrics > Prometheus > Mimir
```