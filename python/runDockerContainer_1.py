import importlib
import subprocess
import argparse
import ast


def run_docker_container(image_name, name=None, protocol='tcp', ports=[], volumes=[], clean_host_volume_dirs=False, environment=[]):
    """_summary_: This function runs a docker image with the given arguments. If the container is already running, it will stop the container and 
        prune all stopped containers. For information on the all other arguments refere to the Docker SDK for Python Documentation 
        - https://github.com/docker/docker-py

        Args:
            image_name (str): image name to run
            command (str): command to run
            ports (dict): Ports to bind inside the container.
            volumes (Dict or List): A dictionary mapping container volumes to host volumes. 
            entrypoint (str or list): The entrypoint for the container.    
            environment (dict or list): Environment variables to set inside
                    format ``["SOMEVARIABLE=xxx"]``.            
            clean_host_volume_dirs (bool): If specified, the container will run with a clean volume directories from the Host.
            healthcheck (dict): Specify a test to perform to check that the
            volumes (dict or list): A dictionary to configure volumes mounted
                              
    """
    # Define default parameters
    default_params = {
        'name': name,
        'protocol': 'tcp',
        'ports': [],
        'volumes': [],
        'environment': [] 
    }
    
    # Merge default parameters with user-provided parameters
    params = default_params.copy()
    params['ports'] = ports
    params['volumes'] = volumes
    protocol = params.pop('protocol')
    
    # Check if docker service is running
    # try:
    #     print('Checking docker service...')
    #     subprocess.check_call(['systemctl', 'is-active', '--quiet', 'docker'])
    #     print('Docker service is running.')
    # except subprocess.CalledProcessError as e:
    #     print('Docker service is not running. Starting docker service...')
    #     try:
    #         subprocess.check_call(['systemctl', 'start', 'docker'])
    #         print('Docker service started successfully.')
    #     except subprocess.CalledProcessError as e:
    #         print('Error starting docker service:', e)
    #         return

    # checking if docker module is installed
    try:
        docker = importlib.import_module('docker')
    except ImportError:
        print('docker module not found, installing...')
        try:
            subprocess.check_call(['pip', 'install', 'docker'])
        except subprocess.CalledProcessError as e:
            print('Error installing docker:', e)
            return
        print('docker module installed successfully.')

    client = docker.from_env()

    # Verify if container is already running
    try:
        print('Checking if container is already running...')
        runningContainers = client.containers.list(
            filters={"status": "running", "ancestor": image_name})
        if (runningContainers):
            print('Container is already running.')
            print('Stopping all containers.')
            for container in runningContainers:
                container.stop()
            # prune docker container
            client.containers.prune()
            print('All containers stopped and pruned all stopped containers.')

    except docker.errors.NotFound:
        print('Container is not running.')
    except docker.errors.APIError as e:
        print('Error:', e)
        return

     # Convert user-friendly parameter format to Docker SDK format
    if 'ports' in params:
        ports_dict = {}
        for port in params['ports']:
            ports = port.split(':')
            host_ports = ports[0]
            container_ports = ports[1]
            ports_dict[f"{container_ports}/{protocol}"] = host_ports

        params['ports'] = ports_dict

    if 'volumes' in params:
        volumes_dict = {}

        for volume in params['volumes']:
            parts = volume.split(':')
            host_path = parts[0]
            container_path = parts[1]
            if clean_host_volume_dirs:    
                try:
                    print('Checking if /opt/data directory exists ....')
                    subprocess.check_call(['test', '-d', host_path])
                    print(f'{host_path} directory cleaned successfully.')
                except subprocess.CalledProcessError as e:
                    print('Error:', e)
                    return
            volumes_dict[host_path] = {'bind': container_path, 'mode': 'rw'}
        params['volumes'] = volumes_dict
                
        
    if 'environment' in params:
        environment_dict = {}
        for env in params['environment']:
            parts = env.split('=')
            var_name = parts[0]
            var_value = parts[1]
            environment_dict[var_name] = var_value
            
        params['environment'] = environment_dict      
    
    
    # Pulling the docker image
    try:
        print('Pulling image...')
        client.images.pull(image_name)
        print('Image pulled successfully.')
    except docker.errors.APIError as e:
        print('Error pulling image:', e)
        return

    try:
        print('Running container with given docker args...')
        
        container = client.containers.run(
            image_name, detach=True, **params)
        if container:
            print(f"{container.short_id} : is running now")
        return
    except docker.errors.APIError as e:
        print('Error running container:', e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a Docker container with specified parameters')
    parser.add_argument('image_name', type=str, help='Docker image name')
    parser.add_argument('--name', type=str, help='Container name')
    parser.add_argument('--protocol', type=str, default='tcp', help='Port protocol (tcp or udp))')
    parser.add_argument('--port', type=str, nargs='+', help='Port mappings in the format "host_port:container_port"')
    parser.add_argument('--volume', type=str, nargs='+', help='Volume mappings in the format "host_path:container_path"')
    parser.add_argument('--environment', type=str, nargs='+', help='Environment variables in the format "var_name=var_value"')
    parser.add_argument('--clean_host_volume_dirs', type=bool, default=False, help='Clean host volume directories')
    args, unknown_args = parser.parse_known_args()

    # Convert unknown arguments to a dictionary and pass to run_container function
    unknown_args_dict = {k: v for k, v in [arg.split('=') for arg in unknown_args]}
    run_docker_container(args.image_name, name=args.name, protocol=args.protocol, ports=args.port, volumes=args.volume, **unknown_args_dict)

    run_docker_container(args.image_name, name=args.name, protocol=args.protocol, ports=args.port, volumes=args.volume)

