Amazon EKS > Create Cluster >
Region: Asia Pacific (Mumbai) 
Configuration Option: Custom Configuration
Disable Use EKS Auto Mode
Name: FarazEKSTesting
Cluster IAM Role: AmazonEKSAutoClusterRole
Kubernetes Version: 1.36 latets version
Tags:
Owner Faraj.Ansari@einfochips.com
DM Harshil.Patel2@einfochips.com
Department PES-DevOps
Project Name AmSec
End Date 
BU PES-IA

VPC: Default
Subnets: 1. Faraz_EKS_Testing_Subnet 2. Faraz_EKS_Testing_Subnet_2
While creating subnet make sure to assign auto public IPv4 address. 
Select Security Group: Faraz_Security_Group
Cluster Endpoint Access: Public and Private

Make sure that your Amazon VPC CNI plugin for Kubernetes, kube-proxy, and CoreDNS add-ons are at the minimum versions listed

Create Node Group: EKS > FarazEKSTesting > Compute > Add Node Group > Node group configuration: FarazWorkersNodeGroup
Node IAM Role: AmazonEKSAutoNodeRole

Capacity Type: On Demand
Instance Types: c6i.large
Disk Size: 20
Desired State: 4
Minimum Size: 2
Maximum Size: 4

Subnets: 1. Faraz_EKS_Testing_Subnet (172.31.65.0/24) 
2. Faraz_EKS_Testing_Subnet_2 (172.31.66.0/24)

Connect EKS Cluster in local machine using below command:
aws eks update-kubeconfig --region ap-south-1 --name FarazEKSTesting