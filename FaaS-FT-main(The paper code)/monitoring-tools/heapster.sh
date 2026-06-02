



#!/bin/bash

#git clone https://github.com/kubernetes/heapster.git
#echo "Create the ressources (heapster,grafana,influxdb)"
#cd heapster

kubectl create -f kube-config/rbac/

kubectl create -f kube-config/influxdb/

echo "command to find the grafana Nodeport "


#kubectl describe service monitoring-grafana --namespace=kube-system | grep NodePort:


echo " installing influxdb Cli "

curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
source /etc/lsb-release
echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list

sudo apt-get update && sudo apt-get install influxdb

sudo systemctl start influxdb
# heapster/deploy/kube-config/influxdb/grafana.yaml
- name: grafana-storage
        hostPath:
          path: /data/shared/heapster/grafana/data

#install server metric 
kubectl apply -f https://raw.githubusercontent.com/pythianarora/total-practice/master/sample-kubernetes-code/metrics-server.yaml
