variable "aws_region" {
  description = "AWS region where resources are created."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for resource names."
  type        = string
  default     = "torre-screening-poc"
}

variable "instance_type" {
  description = "EC2 instance type for application runtime."
  type        = string
  default     = "t4g.small"
}

variable "subnet_id_override" {
  description = "Optional subnet ID override. If empty, Terraform auto-selects a default VPC subnet in an AZ supporting instance_type."
  type        = string
  default     = ""
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB (gp3)."
  type        = number
  default     = 8
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access."
  type        = string
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed to connect through SSH."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
