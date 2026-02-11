provider "aws" {
  region = var.aws_region
}

locals {
  # Graviton families require arm64 AMIs; current fallback keeps x86_64 compatibility.
  ami_arch = can(regex("^t4g\\.", lower(var.instance_type))) ? "arm64" : "amd64"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_ec2_instance_type_offerings" "selected_type" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.instance_type]
  }
}

data "aws_subnets" "default_vpc_supported" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "availability-zone"
    values = data.aws_ec2_instance_type_offerings.selected_type.locations
  }
}

data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-${local.ami_arch}-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_subnet" "selected" {
  id = aws_instance.app.subnet_id
}

resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg"
  description = "Security group for EC2 PoC app"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_cidr_blocks
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu_2204.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id_override != "" ? var.subnet_id_override : sort(data.aws_subnets.default_vpc_supported.ids)[0]
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    delete_on_termination = true
    encrypted             = true
  }

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    apt-get update
    apt-get install -y docker.io docker-compose-plugin git
    systemctl enable --now docker
    usermod -aG docker ubuntu
    mkdir -p /home/ubuntu/torre-screening
    chown ubuntu:ubuntu /home/ubuntu/torre-screening
  EOF

  tags = {
    Name = var.project_name
  }
}
