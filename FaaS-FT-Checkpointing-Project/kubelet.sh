
#!/bin/sh

 #apt-get update && apt-get install -y kubeadm=1.11\* kubectl=1.11\* kubelet=1.11\* 
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 8B57C5C2836F4BEB
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FEEA9169307EA071

 apt-get update && apt-get install -y kubelet=1.19.0-00 kubeadm=1.19.0-00 kubectl=1.19.0-00

# kubernetes-cni=0.6.0-00 

