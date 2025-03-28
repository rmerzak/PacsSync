#----------sr requirement-----------
FROM ubuntu:22.04
RUN apt-get update


FROM python:3.11 as requirements-stage

WORKDIR /tmp
RUN pip install poetry-plugin-export

RUN pip install poetry
COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# --------- final image build ---------
FROM python:3.11

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
# Install WebSocket support directly in the final image
RUN pip install --no-cache-dir 'uvicorn[standard]' websockets

COPY ./src/app /code/app
COPY ./tests /code/tests
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]