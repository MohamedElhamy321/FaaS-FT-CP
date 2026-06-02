# Comprehensive Guide to Testing Checkpointing Improvements in FaaS

This guide provides detailed, step-by-step instructions for setting up your environment, deploying the FaaS project with checkpointing, and running a specific test scenario to demonstrate the benefits of checkpointing for long-running functions. This will allow you to observe how your function recovers from failures by resuming from a saved state, rather than restarting from the beginning.

## 1. Environment Setup: Kubernetes, Fission, and Chaos Mesh

To run the tests, you need a Kubernetes cluster, the Fission FaaS platform deployed on it, and Chaos Mesh for injecting faults. This guide assumes you are using Minikube for a local Kubernetes cluster, but the principles apply to any Kubernetes environment.

### 1.1 Kubernetes Cluster Setup (Minikube Recommended)

Minikube provides a quick way to set up a local Kubernetes cluster. It requires a hypervisor like Docker or VirtualBox.

**Prerequisites:**
*   **Docker:** [Install Docker](https://docs.docker.com/get-docker/) if you don't have it. It's the recommended driver for Minikube.
*   **`kubectl`:** The Kubernetes command-line tool. If you don't have it, you can install it via:
    ```bash
    curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    ```

**Installation Steps:**

1.  **Download and Install Minikube:**
    ```bash
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube
    ```

2.  **Start Minikube Cluster:**
    This command starts a local Kubernetes cluster using the Docker driver. This process can take several minutes as Minikube downloads necessary components.
    ```bash
    minikube start --driver=docker
    ```

3.  **Verify Cluster Status:**
    Confirm that your Kubernetes cluster is running and `kubectl` is configured correctly:
    ```bash
    kubectl cluster-info
    kubectl get nodes
    ```
    You should see output indicating your Minikube cluster is running and a node is in `Ready` status.

### 1.2 Fission Deployment

Fission is the FaaS platform we will use. It runs on Kubernetes and manages your functions.

**Installation Steps:**

1.  **Install Fission CLI:**
    Download and install the Fission command-line interface (CLI) tool:
    ```bash
    curl -LO https://github.com/fission/fission/releases/download/v1.16.0/fission-cli-linux-amd64
    sudo mv fission-cli-linux-amd64 /usr/local/bin/fission
    sudo chmod +x /usr/local/bin/fission
    ```

2.  **Deploy Fission to Kubernetes:**
    This command installs all Fission components into a dedicated `fission` namespace in your Kubernetes cluster. This will take some time.
    ```bash
    fission install
    ```

3.  **Verify Fission Deployment:**
    Monitor the deployment until all Fission pods are in a `Running` or `Completed` state:
    ```bash
    kubectl get pods -n fission
    ```

### 1.3 Chaos Mesh Installation

Chaos Mesh is a powerful tool for injecting various types of faults into your Kubernetes cluster, which is essential for testing fault tolerance mechanisms like checkpointing.

**Installation Steps (using Helm):**

1.  **Add Chaos Mesh Helm Repository:**
    ```bash
    helm repo add chaos-mesh https://charts.chaos-mesh.org
    helm repo update
    ```

2.  **Create Chaos Mesh Namespace:**
    ```bash
    kubectl create ns chaos-testing
    ```

3.  **Install Chaos Mesh:**
    ```bash
    helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-testing --set chaosDaemon.runtime=containerd --set chaosDaemon.socketPath=/run/containerd/containerd.sock
    ```
    **Note:** If your Minikube (or Kubernetes) environment uses `docker` as its container runtime, you might need to adjust the `chaosDaemon.runtime` and `chaosDaemon.socketPath` parameters to `docker` and `/var/run/docker.sock` respectively.

4.  **Verify Chaos Mesh Installation:**
    Ensure all Chaos Mesh pods are running:
    ```bash
    kubectl get pods -n chaos-testing
    ```

## 2. Deploying the FaaS Project with Checkpointing

Now, you will deploy the modified Fibonacci function (with checkpointing enabled) to your Fission environment.

### 2.1 Navigate to the Project Directory

First, navigate to the `FaaS-FT-Checkpointing-Project` directory that contains the modified `fibonacci.py` and other necessary files. If you downloaded the ZIP, extract it and `cd` into the main directory.

```bash
cd /path/to/FaaS-FT-Checkpointing-Project
```

### 2.2 Create a Fission Environment

Fission functions run within specific environments. Since `fibonacci.py` is a Python function, create a Python environment:

```bash
fission env create --name python --image fission/python-env
```

### 2.3 Create a Fission Package

Create a Fission package from your `fibo-app` directory. This packages your function code for deployment.

```bash
fission package create --name fibonacci-pkg --source ./fibo-app --env python
```

### 2.4 Create a Fission Function

Define your Fibonacci function in Fission, linking it to the package and specifying the entry point.

```bash
fission function create --name fibonacci-func --env python --pkg fibonacci-pkg --entrypoint fibonacci.main
```

### 2.5 Create an HTTP Trigger

Create an HTTP trigger to make your function accessible via a URL. This will be the endpoint you send requests to.

```bash
fission route create --name fibonacci-route --url /fibonacci --function fibonacci-func --method POST
```

**Note:** The URL is `/fibonacci` in this example. You can get the Fission router's external IP to access this URL:

```bash
minikube service router -n fission --url
```

This command will output a URL like `http://192.168.49.2:30783`. Your function will be accessible at `http://<FISSION_ROUTER_IP>:<PORT>/fibonacci`.

## 3. Demonstrating Checkpointing Improvements

This section outlines the specific test scenario to demonstrate how checkpointing helps in recovering from failures in long-running functions.

### Scenario: Interrupted Long-Running Fibonacci Calculation

**Objective:** To show that with checkpointing, the Fibonacci function can resume its calculation from a saved intermediate state after its pod is killed, significantly reducing the re-computation time compared to restarting from scratch.

**Files Used:**
*   `fibonacci.py` (located in `fibo-app/`): The modified function with checkpointing logic.
*   `test_checkpoint_recovery.sh`: The bash script to automate the test scenario.
*   `pod_failure.yaml`: The Chaos Mesh configuration to inject a pod-kill fault.

### 3.1 Understanding `test_checkpoint_recovery.sh`

This script automates the process of invoking the function, injecting a fault, and re-invoking to observe recovery. Here's a breakdown of its steps:

1.  **Initial Invocation (Interrupted):**
    The script first invokes the `fibonacci-func` with a large `N_VALUE` (defaulting to 100). This is done in the background to simulate a long-running task. The function will start computing the Fibonacci sequence and periodically save its intermediate state to `/tmp/fibonacci_checkpoint.json`.

2.  **Fault Injection:**
    After a set delay (30 seconds by default), the script applies `pod_failure.yaml`. This Chaos Mesh configuration targets the `fibonacci-func` pod and kills it. This simulates an unexpected failure that would normally cause the function to lose all its in-memory progress.

3.  **Re-invocation and Recovery:**
    After another short delay (10 seconds) to allow Kubernetes to restart the pod, the script re-invokes the `fibonacci-func` with the same `N_VALUE`. Because checkpointing is enabled, the newly started function instance will detect the `fibonacci_checkpoint.json` file, load the last saved state, and resume computation from that point, rather than starting from `fib(0)`.

4.  **Observation and Analysis:**
    The script measures the time taken for the re-invocation to complete. It also provides instructions on how to check the function's logs for messages indicating that a checkpoint was loaded, confirming the recovery mechanism.

### 3.2 Running the Test

1.  **Ensure Correct Paths:**
    Make sure `test_checkpoint_recovery.sh` and `pod_failure.yaml` are in the root of your `FaaS-FT-Checkpointing-Project` directory.

2.  **Update Fission Router URL:**
    Open `test_checkpoint_recovery.sh` and update the `FISSION_ROUTER_URL` variable with the actual URL obtained from `minikube service router -n fission --url`. Remember to append `/fibonacci` to the URL, as that's the route we created.
    For example, if `minikube service router -n fission --url` outputs `http://192.168.49.2:30783`, then `FISSION_ROUTER_URL` should be `http://192.168.49.2:30783/fibonacci`.

3.  **Execute the Test Script:**
    From the root of your `FaaS-FT-Checkpointing-Project` directory, run the script:
    ```bash
    bash test_checkpoint_recovery.sh
    ```

### 3.3 Observing Improvements

As the script runs, pay attention to the output. After the re-invocation, the script will print the time taken for the function to complete. To truly see the checkpointing in action, you need to examine the logs of the `fibonacci-func` pod:

1.  **Get the Pod Name:**
    ```bash
    kubectl get pods -n fission -l function=fibonacci-func
    ```
    Look for the name of the `fibonacci-func` pod (it will likely be something like `fibonacci-func-xxxx-yyyy`).

2.  **View Pod Logs:**
    ```bash
    kubectl logs -f <fibonacci-pod-name> -n fission
    ```
    In the logs of the *new* pod that starts after the kill, you should see messages similar to:
    `Loaded checkpoint: {'last_n': 30, 'sequence': ['0', '1', '1', ..., '514229']}` (the numbers will vary based on when the pod was killed).
    This message confirms that the function successfully loaded its state from the checkpoint file and resumed computation from `last_n`.

**Comparison (Conceptual):**

To fully appreciate the improvement, you would conceptually compare this to a scenario *without* checkpointing. If checkpointing were not implemented, after the pod kill, the re-invoked function would restart from `fib(0)`, taking the full computation time again. With checkpointing, the recovery time is significantly reduced, as only the remaining portion of the computation needs to be performed.

This setup provides a clear and observable demonstration of how checkpointing enhances the reliability and efficiency of long-running FaaS functions by enabling quick recovery from failures.

