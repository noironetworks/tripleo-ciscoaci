#!/usr/bin/env python

import ConfigParser
import datetime
import glob
import optparse
import os
import shutil
import sys
import subprocess
import tempfile

CISCOACI_RPMDIR = "/var/www/html/acirepo"


def determine_ucloud_ip():
    print("Trying to determine the Undercloud ip from /etc/ironic/ironic.conf file")
    ironic_config_file = "/etc/ironic/ironic.conf"

    if not os.path.exists(ironic_config_file):
        raise Exception(
            "File %s does not exist. Maybe undercloud is not configured." % ironic_config_file)

    config = ConfigParser.SafeConfigParser()
    config.read("/etc/ironic/ironic.conf")
    try:
        uip = config.get('DEFAULT', 'my_ip')
    except:
	return 1
    else:
        return uip


def build_containers(upstream_registry, pushurl, pushtag, container_name, arr):
    print "Building ACI %s container" % container_name

    aci_pkgs = arr['packages']
    docker_run_cmds = arr['run_cmds']
    rhel_container = "%s/%s:latest" % (upstream_registry,
                                       arr['rhel_container'])
    if "aci_container" in arr.keys():
        aci_container = arr['aci_container']
    else:
        aci_container = "%s-ciscoaci" % arr['rhel_container']
    if 'user' in arr.keys():
        user = arr['user']
    else:
        user = ''

    build_dir = tempfile.mkdtemp()
    def_user = subprocess.check_output(
        ['docker', 'run', '--name', container_name, rhel_container, 'whoami'])

    subprocess.check_call(["docker", "rm", container_name])

    for fil in aci_pkgs:
        print fil
        srcfile = glob.glob(os.path.join(CISCOACI_RPMDIR, fil))[0]
        dstfile = os.path.join(build_dir, os.path.basename(srcfile))
        shutil.copy(srcfile, dstfile)
    blob = """
FROM %s
MAINTAINER Cisco Systems
LABEL name="rhosp13/%s" vendor="Cisco Systems" version="13.0" release="1"
USER root
       """ % (rhel_container, aci_container)
    for pkg in aci_pkgs:
        blob = blob + "Copy %s /tmp/ \n" % pkg
    blob = blob + "RUN cd /tmp && rpm -Uvh *.rpm \n"
    for cmd in docker_run_cmds:
        blob = blob + "RUN %s \n" % cmd
    if user == '':
        blob = blob + "USER %s \n" % def_user
    else:
        blob = blob + "USER %s \n" % user

    dockerfile = os.path.join(build_dir, "Dockerfile")
    with open(dockerfile, 'w') as df:
        df.write(blob)

    subprocess.check_call(["docker", "build", build_dir, "-t",
                           "%s/%s:%s" % (pushurl, aci_container, pushtag)])

    subprocess.check_call(
        ["docker", "push", "%s/%s:%s" % (pushurl, aci_container, pushtag)])

    shutil.rmtree(build_dir)

    subprocess.check_call(["docker", "rmi", rhel_container])
    subprocess.check_call(
        ["docker", "rmi", "%s/%s:%s" % (pushurl, aci_container, pushtag)])


def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    timestamp = datetime.datetime.now().strftime('%s')

    parser.add_option("-o", "--output_file",
                      help="Environment file to create, default is /home/stack/templates/ciscoaci_containers.yaml",
                      dest='output_file', default='/home/stack/templates/ciscoaci_containers.yaml')
    parser.add_option("-c", "--container",
                      help="Containers to build, comma separated, default is all", dest='containers_tb', default='all')
    parser.add_option("-s", "--upstream",
                      help="Upstream registry to pull base images from, eg. registry.access.redhat.com/rhosp13, defaults to registry.access.redhat.com/rhosp13",
                      default='registry.access.redhat.com/rhosp13',
                      dest='upstream_registry')
    parser.add_option("-d", "--destregistry",
                      help="Destination registry to push to, eg: 1.100.1.1:8787/rhosp13",
                      dest='destination_registry')
    parser.add_option("-t", "--tag", help="tag for images, defaults to 'latest'",
                      default=timestamp, dest='tag')
    (options, args) = parser.parse_args()

    if not options.destination_registry:
        ucloud_ip = determine_ucloud_ip()
	if ucloud_ip == 1:
	    print("Unable to determine undercloud ip. Please specify destination_registry option value.")
	    sys.exit(1)
        pushurl = "%s:8787/rhosp13" % ucloud_ip
    else:
        pushurl = options.destination_registry

    container_array = {
        'horizon': {
            "rhel_container": "openstack-horizon",
            "packages": ["openstack-dashboard-gbp-*.rpm", "python-django-horizon-gbp-*.rpm",
                         "python-gbpclient-*.rpm"],
            "run_cmds": ["mkdir -p /usr/lib/heat",
                         "cp /usr/share/openstack-dashboard/openstack_dashboard/enabled/_*gbp* /usr/lib/python2.7/site-packages/openstack_dashboard/local/enabled"],
            "osd_param_name": ["DockerHorizonImage"],

        },
        'heat': {
            "rhel_container": "openstack-heat-engine",
            "packages": ["openstack-heat-gbp-*.rpm", "python-gbpclient-*.rpm"],
            "run_cmds": ["mkdir -p /usr/lib/heat",
                         "cp -r /usr/lib/python2.7/site-packages/gbpautomation /usr/lib/heat"],
            "osd_param_name": ["DockerHeatEngineImage"],
        },
        'neutron-server': {
            "rhel_container": "openstack-neutron-server",
            "packages": ['python-meld3-*', 'supervisor-*', 'python-click-*',
                         "apicapi-*.rpm", 'libuv-*.rpm', "libmodelgbp-*.rpm",
                         "lldpd-*.rpm", "neutron-opflex-agent-*.rpm",
                         'libopflex-*.rpm', "openstack-neutron-gbp-*.rpm", 
			 "python2-networking-sfc-*.rpm",
                         "python2-tabulate-*.rpm", "python-gbpclient-*.rpm",
                         "python-websocket-client-0.34.*.rpm", 
			 "ciscoaci-puppet*.rpm", "aci-integration-module*.rpm", 
			 "acitoolkit*.rpm", "python-semantic_version*.rpm"],
            "run_cmds": [],
            "osd_param_name": ["DockerNeutronApiImage", "DockerNeutronConfigImage"],
        },
        'ciscoaci-lldp': {
            "rhel_container": "openstack-neutron-server",
            "aci_container": "openstack-ciscoaci-lldp",
            "packages": ['python-meld3-*', 'supervisor-*', 'python-click-*',
                         "apicapi-*.rpm", "python2-tabulate-*.rpm",
                         "python-websocket-client-0.34.*.rpm", "ciscoaci-puppet*.rpm",
                         "aci-integration-module*.rpm", "acitoolkit*.rpm",
                         "ethtool*.rpm", "lldpd*.rpm",
                         "python-semantic_version*.rpm", "neutron-opflex-agent-*.rpm"],
            "run_cmds": [],
            "osd_param_name": ["DockerCiscoLldpImage"],
            "user": 'root',
        },
        'ciscoaci-aim': {
            "rhel_container": "openstack-neutron-server",
            "aci_container": "openstack-ciscoaci-aim",
            "packages": ['python-meld3-*', 'supervisor-*', 'python-click-*',
                         "apicapi-*.rpm", "python2-tabulate-*.rpm",
                         "python-websocket-client-0.34.*.rpm", "ciscoaci-puppet*.rpm",
                         "aci-integration-module*.rpm", "acitoolkit*.rpm",
                         "python-semantic_version*.rpm", "neutron-opflex-agent-*.rpm",
                         "openstack-neutron-gbp-*.rpm", "python-gbpclient-*.rpm"],
            "run_cmds": [],
            "osd_param_name": ["DockerCiscoAciAimImage"],
            "user": 'root',
        },
        'opflex-agent': {
            "rhel_container": "openstack-neutron-openvswitch-agent",
            "aci_container": "openstack-ciscoaci-opflex",
            "packages": ['python-meld3-*', 'supervisor-*', 'python-click-*', 'libicu-*',
                         "apicapi-*.rpm", 'libuv-*.rpm', 'libopflex-*.rpm', "libmodelgbp-*.rpm",
                         "neutron-opflex-agent-*.rpm",
                         "noiro-openvswitch-lib-*.rpm", "noiro-openvswitch-otherlib-*",
                         "openstack-neutron-gbp-*.rpm", "opflex-agent-lib-*.rpm", "opflex-agent-2*.rpm",
                         "opflex-agent-renderer-openvswitch-*.rpm", "python2-networking-sfc-*.rpm",
                         "python2-tabulate-*.rpm", "python-gbpclient-*.rpm",
                         "python-websocket-client-0.34.*.rpm", "ciscoaci-puppet*.rpm", "ethtool*.rpm", "lldpd*.rpm"],
            "run_cmds": [],
            "osd_param_name": ["DockerOpflexAgentImage"],
            "user": 'root',
        },
    }

    if options.containers_tb == 'all':
        containers_list = container_array.keys()
    else:
        containers_list = []
        for co in options.containers_tb.split(','):
            if co in container_array.keys():
                containers_list.append(co)
            else:
                print("Unknown container name %s, skipping" % co)

    for container in containers_list:
        build_containers(options.upstream_registry, pushurl,
                         options.tag, container, container_array[container])

    config_blob = "parameter_defaults:\n"
    for container in containers_list:
        param_names = container_array[container]['osd_param_name']
        if "aci_container" in container_array[container].keys():
            container_name = container_array[container]['aci_container']
        else:
            container_name = "%s-ciscoaci" % container_array[container]['rhel_container']
        for pn in param_names:
            config_blob = config_blob + \
                "   %s: %s/%s:%s \n" % (
                    pn, pushurl, container_name, options.tag)
    with open(options.output_file, "w") as fh:
        fh.write(config_blob)


if __name__ == "__main__":
    main()
