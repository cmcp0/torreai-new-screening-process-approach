# EC2 Minimal Terraform

This template provisions:
- 1 EC2 Ubuntu 22.04 instance
- 1 security group (`22`, `80`, `443` ingress)

It uses the default VPC/subnet for speed and low complexity.

## Required Order

1. Run Terraform first.
2. Set GitHub repository secrets from Terraform outputs.
3. Trigger GitHub Actions deploy manually.

## Usage

```bash
cd infra/terraform/ec2-minimal
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

After apply, use `public_dns` output to access the app.

## Map Terraform Outputs to GitHub Secrets

Run:

```bash
terraform output
```

Set repository secrets:
- `EC2_HOST` = `public_dns`
- `EC2_USER` = `ubuntu`
- `EC2_SSH_KEY` = private key content for `key_name`

Then create `.env.ec2` on the EC2 host (required by deploy workflow), and run workflow `EC2 CI/CD` with **Run workflow**.

You can verify architecture resolution with:
- `terraform output instance_type`
- `terraform output ami_architecture`

## Notes

- Set `ssh_cidr_blocks` to your office/home IP range. Do not keep open SSH in shared environments.
- This template does not create Route 53, ALB, or RDS.
- Deploy app containers using the CI/CD workflow or manually with `docker-compose.ec2.yml`.

## Cost-Oriented Defaults (Safe for PoC)

- Default instance type is `t4g.small` (Graviton ARM, generally lower cost for same 2 vCPU/2 GB class).
- Root disk is explicitly `gp3` with `8 GB` to keep storage spend low and predictable.

AMI architecture is auto-selected:
- `t4g.*` => `arm64` Ubuntu AMI
- non-`t4g.*` => `amd64` Ubuntu AMI

Subnet/AZ handling for instance compatibility:
- Terraform auto-selects a default VPC subnet in an AZ that supports `instance_type`.
- Optional override: set `subnet_id_override` in `terraform.tfvars` if you want to pin a specific subnet/AZ.

If you observe memory pressure with `nginx + backend + postgres`, move to `t4g.medium` (or `t3a.medium` if using x86 instances).
