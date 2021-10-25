FROM docker

# Install General Requirements
RUN apk update \
    && apk add bash \
    && apk add curl \
    && apk add make \
    && apk add unzip \
    && apk add wget \
    && apk add which \
    && apk add util-linux

# Install GCloud
RUN apk add python3 py3-pip
RUN curl -sSL https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin
RUN gcloud components install beta --quiet

# Copy Oracle Files
RUN mkdir /oracle
COPY oracle/*.rpm /oracle/

CMD ["make"]
