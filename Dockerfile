FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

ENV APP_HOME=/app
ENV APP_USER=non-root

RUN groupadd $APP_USER && \
    useradd -m -g $APP_USER -d $APP_HOME $APP_USER

COPY . $APP_HOME
WORKDIR $APP_HOME

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

USER $APP_USER

ENTRYPOINT ["python"]
CMD ["src/app.py"]