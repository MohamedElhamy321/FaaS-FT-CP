#!/bin/sh

echo " installing Helm ....."
curl -LO https://storage.googleapis.com/kubernetes-helm/helm-v2.16.0-linux-amd64.tar.gz

tar xzf helm-v2.16.0-linux-amd64.tar.gz

mv linux-amd64/helm /usr/local/bin

kubectl -n kube-system create sa tiller
kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller
#helm init --service-account tiller
helm init --service-account tiller --override spec.selector.matchLabels.'name'='tiller',spec.selector.matchLabels.'app'='helm' --output yaml | sed 's@apiVersion: extensions/v1beta1@apiVersion: apps/v1@' | kubectl apply -f -
helm init --stable-repo-url=https://charts.helm.sh/stable --client-only 
## install helm 

#cat << EOF >> ~/.helm/repository/repositories.yaml
#apiVersion: v1

#repositories:
#- caFile: ""
#  cache: ~/.helm/repository/cache/stable-index.yaml
 # certFile: ""
 # keyFile: ""
 # name: stable
 # password: ""
 # url: https://kubernetes-charts.storage.googleapis.com
 # username: ""
#- caFile: ""
 # cache: ~/.helm/repository/cache/local-index.yaml
  #certFile: ""
  #keyFile: ""
  #name: local
  #password: ""
  #url: http://127.0.0.1:8879/charts
  #username: ""
#EOF

#helm init --service-account tiller

