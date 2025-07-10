# easydo_backend/lambda_mcp_servers/calendar_lambda/Dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum update -y && yum install -y gcc

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY calendar_server.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["calendar_server.lambda_handler"]