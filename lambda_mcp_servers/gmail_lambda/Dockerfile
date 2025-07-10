# easydo_backend/lambda_mcp_servers/gmail_lambda/Dockerfile
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Copy requirements and install packages
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy the Lambda function
COPY gmail_server.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["gmail_server.lambda_handler"]