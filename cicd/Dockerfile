FROM docker

# Install General Requirements
RUN apk update \
    && apk add wget \
    && apk add unzip \
    && apk add make \
    && apk add curl \
    && apk add bash

# Copy Oracle Files
RUN mkdir /oracle
COPY oracle/*.rpm /oracle/

CMD ["make"]
