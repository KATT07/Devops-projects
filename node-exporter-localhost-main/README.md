# node-exporter-localhost
A config for docker compose to deploy node-exporter+prometheus exposed on port 9090 

Warning : it exposes port 9090 for 0.0.0.0 (All IP Addresses on the same Network)

# Before u start
please ensure Docker compose is installed                                                                                                                                                                                    
if not here is the script to install docker + docker compose -> https://github.com/docker/docker-install
```
curl -fsSL https://get.docker.com -o get-docker.sh
sh ./get-docker.sh
```


# To deploy
Simply git clone this repo and run it 
```bash
git clone https://github.com/KATT07/node-exporter-localhost
cd ./node-exporter-localhost
sudo docker compose up -d
```

Originally by : https://grafana.com/docs/grafana-cloud/quickstart/docker-compose-linux/


# Grafana Dashboard

add prometheus at grafana > connections > datasources > add data source

http://prometheus:9090

import dashboard from grafana > dashboards > new > import dashboard**

id: 1860
