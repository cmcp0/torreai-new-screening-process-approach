output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.app.id
}

output "instance_type" {
  description = "EC2 instance type used for the app host."
  value       = aws_instance.app.instance_type
}

output "ami_architecture" {
  description = "AMI architecture selected from instance family."
  value       = local.ami_arch
}

output "selected_subnet_id" {
  description = "Subnet ID where the EC2 instance is launched."
  value       = aws_instance.app.subnet_id
}

output "selected_availability_zone" {
  description = "Availability Zone selected for the EC2 instance subnet."
  value       = data.aws_subnet.selected.availability_zone
}

output "public_ip" {
  description = "Public IP of the EC2 instance."
  value       = aws_instance.app.public_ip
}

output "public_dns" {
  description = "Public DNS hostname of the EC2 instance."
  value       = aws_instance.app.public_dns
}

output "security_group_id" {
  description = "Security group attached to the instance."
  value       = aws_security_group.app.id
}
