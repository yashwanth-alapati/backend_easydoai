# easydo_backend/infrastructure/lambda_mcp_stack.py
"""
AWS CDK Stack for Lambda MCP Servers
"""
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_ecr as ecr,
    Duration,
)
from constructs import Construct


class LambdaMCPStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Reference existing ECR repositories (don't create new ones)
        gmail_repo = ecr.Repository.from_repository_name(
            self, "GmailMCPRepo", repository_name="easydoai-gmail-mcp"
        )

        calendar_repo = ecr.Repository.from_repository_name(
            self, "CalendarMCPRepo", repository_name="easydoai-calendar-mcp"
        )

        # IAM role for Lambda functions
        lambda_role = iam.Role(
            self,
            "MCPLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Add DynamoDB permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"],
                resources=["arn:aws:dynamodb:*:*:table/easydoai-user-tokens"],
            )
        )

        # Gmail Lambda Function
        gmail_lambda = _lambda.DockerImageFunction(
            self,
            "GmailMCPLambda",
            code=_lambda.DockerImageCode.from_ecr(
                repository=gmail_repo, tag_or_digest="latest"
            ),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={"TOKENS_TABLE_NAME": "easydoai-user-tokens"},
        )

        # Calendar Lambda Function
        calendar_lambda = _lambda.DockerImageFunction(
            self,
            "CalendarMCPLambda",
            code=_lambda.DockerImageCode.from_ecr(
                repository=calendar_repo, tag_or_digest="latest"
            ),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={"TOKENS_TABLE_NAME": "easydoai-user-tokens"},
        )

        # API Gateway
        api = apigateway.RestApi(
            self,
            "MCPToolsAPI",
            rest_api_name="EasyDoAI MCP Tools",
            description="API for MCP tool execution",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        # Gmail API routes
        gmail_resource = api.root.add_resource("gmail")
        gmail_integration = apigateway.LambdaIntegration(gmail_lambda)
        gmail_resource.add_method("POST", gmail_integration)
        gmail_resource.add_method("GET", gmail_integration)

        # Calendar API routes
        calendar_resource = api.root.add_resource("calendar")
        calendar_integration = apigateway.LambdaIntegration(calendar_lambda)
        calendar_resource.add_method("POST", calendar_integration)
        calendar_resource.add_method("GET", calendar_integration)

        # Output the API URL
        self.api_url = api.url
