# IRSA (IAM Roles for Service Accounts) role for the pipeline namespace's
# service account — lets pods assume an AWS IAM role via their K8s identity,
# no static credentials in the cluster. Scoped today to CloudWatch Logs write
# access as a realistic starter use case (shipping pod logs off-cluster);
# a real deployment beyond a one-off verification run should replace the
# managed policy with a least-privilege one scoped to specific log groups.

data "aws_iam_policy_document" "irsa_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }
  }
}

resource "aws_iam_role" "pipeline_service_account" {
  name               = "${var.cluster_name}-${var.namespace}-sa"
  assume_role_policy = data.aws_iam_policy_document.irsa_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = aws_iam_role.pipeline_service_account.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}
