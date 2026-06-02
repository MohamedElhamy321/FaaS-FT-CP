#!/bin/sh



# we have already build the container image for Fission vanilla, AS and RR 

#install fission with the new image 

#install of Fission vanilla
helm install --set "image=cloudfaas/fission-bundle,imageTag=1.10.0,pullPolicy=IfNotPresent,analytics=false,serviceType=NodePort,routerServiceType=NodePort" charts/fission-all
#install of Fission Request Replication qnd deploy Router-RR
helm install --set "image=cloudfaas/fission-bundle,imageTag=1.10.1,pullPolicy=IfNotPresent,analytics=false,serviceType=NodePort,routerServiceType=NodePort" charts/fission-all
Kubectl apply -f deploy-router/deploy-routerRR.yaml
#install of Fission Active-Standby qnd deploy Router-AS
helm install --set "image=cloudfaas/fission-bundle,imageTag=1.10.2,pullPolicy=IfNotPresent,analytics=false,serviceType=NodePort,routerServiceType=NodePort" charts/fission-all
Kubectl apply -f deploy-router/deploy-routerAS.yaml

echo "Installing the fission CLI..."
 
curl -Lo fission https://github.com/fission/fission/releases/download/1.10.0/fission-cli-linux && chmod +x fission && sudo mv fission /usr/local/bin/






