import os
from collections import OrderedDict
from sys import exit as sys_exit
from datetime import datetime
from ruamel.yaml import YAML
yaml = YAML()

def load_manifest(pathn):
   if not pathn.endswith(".yaml"):
      return None
   try:
      with open(pathn, "r") as f:
         return yaml.load(f)
   except FileNotFoundError:
      print("File can not found")
      exit(2)

def dump_manifest(pathn, manifest):
   with open(pathn, "w") as f:
      yaml.dump(manifest, f)
   return

def get_container(containers_array, container_name):
    for c_container in containers_array:
        if c_container['name'] == container_name:
            return c_container
    return None

timestamp = int(os.getenv('EPOC_TIMESTAMP'))
datetime_time = datetime.fromtimestamp(timestamp)
upstream_csv = load_manifest(os.getenv('CSV_FILE'))

# Add arch support labels
upstream_csv['metadata']['labels'] = upstream_csv['metadata'].get('labels', {})
if os.getenv('AMD64_BUILT'):
	upstream_csv['metadata']['labels']['operatorframework.io/arch.amd64'] = 'supported'
if os.getenv('ARM64_BUILT'):
	upstream_csv['metadata']['labels']['operatorframework.io/arch.arm64'] = 'supported'
if os.getenv('PPC64LE_BUILT'):
	upstream_csv['metadata']['labels']['operatorframework.io/arch.ppc64le'] = 'supported'
if os.getenv('S390X_BUILT'):
	upstream_csv['metadata']['labels']['operatorframework.io/arch.s390x'] = 'supported'
upstream_csv['metadata']['labels']['operatorframework.io/os.linux'] = 'supported'
upstream_csv['metadata']['annotations']['createdAt'] = datetime_time.strftime('%d %b %Y, %H:%M')
upstream_csv['metadata']['annotations']['repository'] = 'https://github.com/os-bservability/konflux-jaeger'
upstream_csv['metadata']['annotations']['containerImage'] = os.getenv('JAEGER_OPERATOR_IMAGE_PULLSPEC', '')

upstream_csv['spec']['relatedImages'] = [
    {'name': 'operator', 'image': os.getenv('JAEGER_OPERATOR_IMAGE_PULLSPEC')},
    {'name': 'collector', 'image': os.getenv('JAEGER_COLLECTOR_IMAGE_PULLSPEC')},
    {'name': 'query', 'image': os.getenv('JAEGER_QUERY_IMAGE_PULLSPEC')},
    {'name': 'agent', 'image': os.getenv('JAEGER_AGENT_IMAGE_PULLSPEC')},
    {'name': 'ingester', 'image': os.getenv('JAEGER_INGESTER_IMAGE_PULLSPEC')},
    {'name': 'all-in-one', 'image': os.getenv('JAEGER_ALL_IN_ONE_IMAGE_PULLSPEC')},
    {'name': 'es-index-cleaner', 'image': os.getenv('JAEGER_INDEX_CLEANER_IMAGE_PULLSPEC')},
    {'name': 'es-rollover', 'image': os.getenv('JAEGER_ROLLOVER_IMAGE_PULLSPEC')}]

with open('./patch_csv.yaml') as pf:
    patch = yaml.load(pf)

    if patch['metadata'].get(['labels']) is not None:
        upstream_csv['metadata']['labels'].update(patch['metadata']['labels'])
    upstream_csv['metadata']['annotations'].update(patch['metadata']['extra_annotations'])
    upstream_csv['spec']['description'] = patch['spec']['description']
    upstream_csv['spec']['displayName'] = patch['spec']['displayName']
    upstream_csv['spec']['icon'] = patch['spec']['icon']
    upstream_csv['spec']['maintainers'] = patch['spec']['maintainers']
    upstream_csv['spec']['provider'] = patch['spec']['provider']
    upstream_csv['spec']['version'] = patch['spec']['version']

    if patch['metadata'].get('name'):
        upstream_csv['metadata']['name'] = patch['metadata']['name']
    if patch['spec'].get('replaces'):
        upstream_csv['spec']['replaces'] = patch['spec']['replaces']

    # volumes
    if not upstream_csv['spec']['install']['spec']['deployments'][0]['spec']['template']['spec'].get('volumes'):
        upstream_csv['spec']['install']['spec']['deployments'][0]['spec']['template']['spec']['volumes']=[]
    upstream_csv['spec']['install']['spec']['deployments'][0]['spec']['template']['spec']['volumes'].extend(patch['spec']['install']['spec']['deployments'][0]['spec']['template']['spec']['extra_volumes'])

    upstream_containers = upstream_csv['spec']['install']['spec']['deployments'][0]['spec']['template']['spec']['containers']
    for container in             patch['spec']['install']['spec']['deployments'][0]['spec']['template']['spec']['containers']:
        upstream_container = get_container(upstream_containers, container['name'])
        if upstream_container is None:
            print("container preset in patch, but not in upstream CSV", container['name'])
            exit(2)
        print("Patching ", container['name'])

        # image
        if container.get('image') is not None:
            upstream_container['image'] = container.get('image')

        # args
        if container.get('extra_args') is not None:
            upstream_container['args'] = upstream_container['args'] + container['extra_args']
        for arg in container.get('remove_args', []):
            upstream_container['args'].remove(arg)

        # env vars
        if container.get('extra_env') is not None:
            if  upstream_container.get('env') is not None:
                upstream_container['env'] = upstream_container.get('env') + container.get('extra_env')
            else:
                upstream_container['env'] = container.get('extra_env')

        if container.get('extra_ports') is not None:
            upstream_container['ports'] = upstream_container['ports'] + container.get('extra_ports')


        # volume mounts
        if container.get('extra_volumeMounts') is not None:
            if  upstream_container.get('volumeMounts') is not None:
                upstream_container['volumeMounts'] = upstream_container.get('volumeMounts') + info.get('extra_volumeMounts')
            else:
                upstream_container['volumeMounts'] = container.get('extra_volumeMounts')

dump_manifest(os.getenv('CSV_FILE'), upstream_csv)