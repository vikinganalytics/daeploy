## Stage 1: Build image
FROM python:3.8 AS build-image

# Install S2i
RUN wget -c https://github.com/openshift/source-to-image/releases/download/v1.3.0/source-to-image-v1.3.0-eed2850f-linux-amd64.tar.gz \
    &&  tar -zxvf source-to-image-v1.3.0-eed2850f-linux-amd64.tar.gz \
    &&  cp s2i /usr/local/bin

# Install Traefik
RUN wget -c https://github.com/traefik/traefik/releases/download/v2.3.1/traefik_v2.3.1_linux_amd64.tar.gz \
    && tar -zxvf traefik_v2.3.1_linux_amd64.tar.gz \
    && cp traefik /usr/local/bin

# Setup virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install python requirements
COPY ./requirements_manager.txt .
RUN pip install -r requirements_manager.txt

## Stage 2: Production image
FROM python:3.8-slim AS production-image

# Install Git
RUN apt-get update && apt-get install -y git

# Grab s2i and traefik
COPY --from=build-image /usr/local/bin /usr/local/bin

# Grab the virtualenv
COPY --from=build-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Add manager source code
COPY manager/ manager/

# Setting up manager instance with environment variables
ENV DAEPLOY_PROXY_HTTP_PORT=80
ENV DAEPLOY_PROXY_HTTPS_PORT=443
ENV DAEPLOY_MANAGER_IN_CONTAINER=True

# Handling version numbering
ARG version="latest"
ENV DAEPLOY_MANAGER_VERSION=${version}

# Expose ports that Traefik listens on (still need to be mapped when starting the container!)
EXPOSE 80
EXPOSE 443

# Set some labels
LABEL daeploy.type="manager"
LABEL daeploy.version="0.1.0"
LABEL maintainer="Viking Analytics AB"

ENTRYPOINT ["uvicorn", "manager.app:app"]