output "role_arn" {
  value = aws_iam_role.pipeline_service_account.arn
}

output "role_name" {
  value = aws_iam_role.pipeline_service_account.name
}
