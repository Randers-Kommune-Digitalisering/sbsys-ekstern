FROM python:3.11-alpine

ENV APP_HOME=/app
ENV APP_USER=non-root

RUN addgroup $APP_USER && \
    adduser $APP_USER -D -G $APP_USER

RUN apk update
RUN apk add musl-dev gcc libpq-dev postgresql-dev python3-dev

COPY . $APP_HOME
WORKDIR $APP_HOME

RUN pip install -r requirements.txt

EXPOSE 8080

USER $APP_USER

ENTRYPOINT ["python"]
CMD ["src/app.py"]
