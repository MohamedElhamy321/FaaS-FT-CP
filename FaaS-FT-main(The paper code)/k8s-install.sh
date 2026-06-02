
#!/bin/sh


#oar_jobID=956101
nodes="$HOME/node.txt"

#oarsub -C $oar_jobID  &

cat $OAR_NODE_FILE | sort -u > $nodes

master=`head -1 $nodes`
nb_nodes=`wc -l $nodes  | awk {'print $1'}`
nb_workers=`expr $nb_nodes - 1`
workers=`tail -$nb_workers $nodes`



RED=`tput setaf 1`
GREEN=`tput setaf 2`
reset=`tput sgr0`
scp install-pkg.sh  root@$master:
ssh root@$master  sh install-pkg.sh  


scp    kubelet.sh    root@$master:
scp    helm-install.sh   root@$master:
scp    master-config.sh  root@$master:
#scp    fission-update/go.sh      root@$master:
scp     reset-config.sh        root@$master:


ssh root@$master  sh kubelet.sh  

echo ".......Running on the master node......."
ssh root@$master  sh reset-config.sh

echo "Initialing the master node..."

tok=$( ssh root@$master kubeadm init   --kubernetes-version stable-1.19 --pod-network-cidr=10.244.0.0/16  | grep -A 2 "kubeadm join" | tr -d \\ )

echo $tok

ssh root@$master sh master-config.sh
#ssh root@$master  sh helm-install.sh   


echo ".......Cluster Information......"
ssh root@$master kubectl get nodes


for worker in $workers; do 
scp install-pkg.sh  root@$worker:
#scp    docker.sh    root@$worker:

#ssh root@$worker  sh install-pkg.sh  


scp kubelet.sh    root@$worker:
scp reset-config.sh   root@$worker:

echo ".......Running on  wrk  node ......."
ssh root@$worker  sh install-pkg.sh 
ssh root@$worker  sh kubelet.sh 
#ssh root@$worker  sh docker.sh  
ssh root@$worker  sh reset-config.sh 
 

echo "Worker joining the cluster..."
ssh root@$worker $tok 
done

echo ".......Cluster Information......"
ssh root@$master kubectl get nodes

if [ $? -eq 0 ]
then
    echo "${GREEN}Cluster validation succeeded${reset}"
    else
    echo "${RED}Cluster validation encountered some problems${reset} "
    fi

#copy files to master node
scp /home/yabouizem/fission-update/app/deploy.yaml   root@$master:
scp /home/yabouizem/k8s-experiments1/fission-app/fibonacci.py  root@$master:
scp -r /monitoring-tools/heapster.sh   root@$master:

# install helm,go and heapster in master node
ssh root@$master sh go.sh
ssh root@$master sh helm-install.sh



#scp -r /home/fission-update/scripts/failure-scripts  root@$master:
#scp -r /home/monitoring-tools/heapster/deploy/kube-config   root@$master:

ssh root@$master  sh heapster.sh 





