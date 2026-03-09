import boto3
from botocore.exceptions import BotoCoreError,ClientError
from .base import config_Source

class aws_config_source(config_Source):
    """ 
    Connector to AWS config via IAM role/keys (env vars on instance role)
    """
    def __init__(self, region_name: str | None = None):
        self.client = boto3.client('config', region_name=region_name)
        
    def list_resources(self) -> list[str]:
        paginator = self.client.get_paginator('list_discovered_resources')
        resource_ids: list[str] = []
        for page in paginator.paginate(resourceType="AWS::EC@::Instance"):
            identifiers = page.get('resourceIdentifiers', [])
            for r in identifiers:
                resource_ids.append(r['resourceId'])
        return resource_ids
    
    def fetch_config(self, resource_id: str) -> bytes:
        try:
            resp = self.client.get_resource_config_history(
                resourcetype ='AWS::ECS::Instance',
                resourceId = resource_id,
                limit = 1,
                chronologicalOrder = 'Reverse'
            )
            item = resp['configurationItems'[0]]
            config_blob = item.get('configuration', {})
            return str(config_blob).encode('utf-8')
        except(BotoCoreError, ClientError) as e:
            raise RuntimeError(f"AWS Config failed for {resource_id}: {e}")
        
        