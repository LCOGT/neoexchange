
#!/bin/sh

# wait for RabbitMQ server to start
sleep 10

cd neox
# run Celery worker for our project myproject with Celery configuration stored in Celeryconf
su -m myuser -c "celery worker -A neox.celery -Q default -n default@%h"
