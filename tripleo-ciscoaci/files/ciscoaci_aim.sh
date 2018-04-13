#!/bin/bash
set -eu

# Parse Args
script=$(basename "$0")
action=${1:-''}
if [ "${action}" != 'start' -a "${action}" != 'stop' -a "${action}" != 'status' ] ; then
    echo "USAGE: ${script} <action> (where action is one of start, stop, or status)"
    echo "Invalid argument: '${action}'" 1>&2
    exit 1
fi

# check for correct openstack env, will exit if env is not set
echo "Validating overcloud env ..."
nova list 3>/dev/null 2>&1 1>&3

# get list of controllers
echo "Finding an available overcloud server ..."
ocloud_server_str=$(openstack server list -f json 2>/dev/null | jq .[0].Networks 2>/dev/null)
if [ "${ocloud_server_str}" != "null" ] ; then
    echo "Using overcloud server from: ${ocloud_server_str}"
    ocloud_server=$(echo ${ocloud_server_str} | tr -d '"' | cut -d= -f2)
    echo "Finding all overcloud controllers ..."
    ocloud_ctrls_str=$(ssh -q -o 'UserKnownHostsFile /dev/null' -o 'StrictHostKeyChecking no' \
        heat-admin@${ocloud_server} sudo cat /etc/puppet/hieradata/all_nodes.json | \
        jq .controller_node_ips)
    if [ "${ocloud_ctrls_str}" != "null" ] ; then
        echo "Using overcloud ctrls from: ${ocloud_ctrls_str}"
        ocloud_ctrls_list=$(echo ${ocloud_ctrls_str} | tr -d '"')
        for ctrl in $(echo ${ocloud_ctrls_list} | tr ',' '\n') ; do
            echo "Overcloud controller: ${ctrl} ..."
            ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
                heat-admin@${ctrl} \
                "sudo systemctl ${action} aim-event-service-rpc; \
                 sudo systemctl ${action} aim-aid; \
                 sudo systemctl ${action} aim-event-service-polling" ;
        done
    else
        echo "No overcloud controller found." 1>&2
        exit 3
    fi
else
    echo "No overcloud controller found" 1>&2
    exit 2
fi
