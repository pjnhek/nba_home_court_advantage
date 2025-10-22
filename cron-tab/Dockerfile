FROM continuumio/miniconda3
WORKDIR /CRONTAB
COPY * .

RUN apt-get update && apt-get -y install cron curl

RUN touch /var/log/cron.log

COPY api-cron /etc/cron.d/api-cron

RUN crontab /etc/cron.d/api-cron

CMD ["cron", "-f"] 