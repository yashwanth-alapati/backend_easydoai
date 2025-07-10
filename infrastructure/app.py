# easydo_backend/infrastructure/app.py
"""
CDK App for Lambda MCP Stack
"""
#!/usr/bin/env python3
import aws_cdk as cdk
from lambda_mcp_stack import LambdaMCPStack

app = cdk.App()

# Deploy the Lambda MCP Stack
LambdaMCPStack(
    app, 
    "LambdaMCPStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    )
)

app.synth()