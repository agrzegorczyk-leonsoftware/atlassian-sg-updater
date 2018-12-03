#!/usr/bin/env python3.6
# 20181203 AGR

# syncs given SG with Atlassian ip-range list (IPv4 only)

import argparse
import requests
import boto3
import ipaddress
import datetime

IP_LIST_URL='https://ip-ranges.atlassian.com/'

parser = argparse.ArgumentParser()
parser.add_argument('--region', type=str, required=True)
parser.add_argument('--sg-id', type=str, required=True)
parser.add_argument('--port', type=int, default=443)
parser.add_argument('--identifier', type=str, default='auto-update-atlassian')
args=parser.parse_args()

def get_atlassian_ipv4_nets():
    return [
        # filtering - IPv4 only
        ip_net for ip_net in
            # get ip range list and convert into ipaddress objects
            ( ipaddress.ip_network(item['cidr']) for item in requests.get(IP_LIST_URL).json()['items'] )
        if ip_net.version == 4
    ]


def get_sg_ipv4_ranges(sg_obj):
    return [
        r_range
        for rule in sg_obj.ip_permissions
        for r_range in rule['IpRanges']
        if rule['IpProtocol'] == 'tcp' and rule['FromPort'] == args.port and rule['ToPort'] == args.port
    ]

sg = boto3.resource('ec2', region_name=args.region).SecurityGroup(args.sg_id)

sg_ipv4_ranges = get_sg_ipv4_ranges(sg)
atlassian_ipv4_nets = get_atlassian_ipv4_nets()

# ! script sync only rules with description starting with args.identifier value

temp_sg_ipv4_ranges = [
    ipaddress.ip_network(sg_ipv4_range['CidrIp'])
    for sg_ipv4_range in sg_ipv4_ranges
]

missing_sg_ipv4_ranges = [
    ipv4_net
    for ipv4_net in atlassian_ipv4_nets
    if ipv4_net not in temp_sg_ipv4_ranges
]

obsolete_sg_ipv4_ranges = [
    sg_ip_range
    for sg_ip_range in sg_ipv4_ranges
    if sg_ip_range['Description'].startswith(args.identifier) and ipaddress.ip_network(sg_ip_range['CidrIp']) not in atlassian_ipv4_nets
]

# add missing rules
if missing_sg_ipv4_ranges:
    description=args.identifier+': '+str(datetime.datetime.utcnow())
    sg.authorize_ingress(
        IpPermissions = [
            {
                'FromPort': args.port,
                'ToPort': args.port,
                'IpProtocol': 'tcp',
                'IpRanges': [
                    {
                        'CidrIp': str(ipv4_range),
                        'Description': description
                    }
                    for ipv4_range in missing_sg_ipv4_ranges
                ]
            }
        ]
    )

# revoke obsolete rules
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.SecurityGroup.revoke_ingress
if obsolete_sg_ipv4_ranges:
    sg.revoke_ingress(
        IpPermissions = [
            {
                'FromPort': args.port,
                'ToPort': args.port,
                'IpProtocol': 'tcp',
                'IpRanges': obsolete_sg_ipv4_ranges
            }
        ]
    )

print ("{} added, {} removed".format(
        len(missing_sg_ipv4_ranges),
        len(obsolete_sg_ipv4_ranges)
    )
)
