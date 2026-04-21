FROM public.ecr.aws/lambda/python:3.11

COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY model/model.onnx ${LAMBDA_TASK_ROOT}/model/model.onnx
COPY docker/etl.py ${LAMBDA_TASK_ROOT}/etl.py

CMD ["etl.handler"]
