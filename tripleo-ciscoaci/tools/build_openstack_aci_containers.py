#!/usr/libexec/platform-python

import configparser
import datetime
import getpass
import glob
import grp
import argparse
import os
import pwd
import shutil
import shlex
import sys
import subprocess
import tarfile
import tempfile
import json
import re
import pdb
from hashlib import md5

CISCOACI_RPMDIR = "/opt/cisco_aci_rpms"


def determine_ucloud_ip():
    print("Trying to determine the Undercloud ip from /etc/ironic/ironic.conf file")
    ironic_config_file = "/var/lib/config-data/puppet-generated/ironic_api/etc/ironic/ironic.conf"

    if not os.path.exists(ironic_config_file):
        raise Exception(
            "File %s does not exist. Maybe undercloud is not configured." % ironic_config_file)

    config = configparser.SafeConfigParser()
    config.read(ironic_config_file)
    try:
        uip = config.get('DEFAULT', 'my_ip')
    except:
        return 1
    else:
        return uip


def build_containers(ucloud_ip, upstream_registry, regseparator, pushurl, pushtag, container_name, arr, repotext, license_text):
    print("Building ACI %s container" % container_name)

    aci_pkgs = arr['packages']
    docker_run_cmds = arr['run_cmds']
    rhel_container = "%s%s%s:16.1" % (upstream_registry, regseparator,
                                       arr['rhel_container'])
    if "aci_container" in arr.keys():
        aci_container = "%s/%s" %(pushurl, arr['aci_container'])
    else:
        aci_container = "%s/%s-ciscoaci" % (pushurl, arr['rhel_container'])

    if 'user' in arr.keys():
        user = arr['user']
    else:
        user = ''

    if 'summary' in arr.keys():
        summary = arr['summary']
    else:
        summary = ''

    if 'description' in arr.keys():
        description = arr['description']
    else:
        description = ''


    d_user = subprocess.check_output(
        ['podman', 'run', '--net=host', '--name', '%s-temp' % container_name, rhel_container, 'whoami'])
    def_user = d_user.decode('utf-8').strip()

    subprocess.check_call(["podman", "rm", '%s-temp' % container_name])

    build_dir = tempfile.mkdtemp()
    shutil.copytree('/opt/cisco_aci_repo', '%s/opt/cisco_aci_repo' % build_dir)
    repofile = os.path.join(build_dir, 'aci.repo')
    with open(repofile, 'w') as fh:
       fh.write(repotext)

    license_file = os.path.join(build_dir, 'LICENSE.txt')
    with open(license_file, 'w') as fh:
       fh.write(license_text)

    blob = """
FROM %s
MAINTAINER Cisco Systems
LABEL name="%s" vendor="Cisco Systems" version="16.1" release="1" summary="%s" \
description="%s"
USER root
ENV no_proxy="${no_proxy},%s"
       """ % (rhel_container, aci_container, summary, description, ucloud_ip)
    blob = blob + "RUN dnf config-manager --enable openstack-16.1-for-rhel-8-x86_64-rpms \n"
    blob = blob + "ADD /opt/cisco_aci_repo /opt/cisco_aci_repo \n"
    blob = blob + "Copy aci.repo /etc/yum.repos.d \n"
    blob = blob + "RUN mkdir /licenses \n"
    blob = blob + "Copy LICENSE.txt /licenses/ \n"
    for cmd in docker_run_cmds:
        blob = blob + "RUN %s \n" % cmd
    if user == '':
        blob = blob + "USER %s \n" % def_user
    else:
        blob = blob + "USER %s \n" % user

    dockerfile = os.path.join(build_dir, "Dockerfile")
    with open(dockerfile, 'w') as df:
        df.write(blob)

    subprocess.check_call(["podman", "build", build_dir, "-t",
                           "%s:%s" % (aci_container, pushtag)])

    cmd ="openstack tripleo container image push --local %s:%s" % (aci_container, pushtag)
    subprocess.check_call(shlex.split(cmd))

    shutil.rmtree(build_dir)

    subprocess.check_call(["podman", "rmi", rhel_container])

    ccmd ="podman rmi %s:%s" % (aci_container, pushtag)
    subprocess.check_call(shlex.split(ccmd))


def main():
    timestamp = datetime.datetime.now().strftime('%s')

    def extant_file(x):
        if not os.path.exists(x):
           raise argparse.ArgumentTypeError("{0} does not exist".format(x))
        return x

    parser = argparse.ArgumentParser(description='Build containers for ACI Plugin')

    parser.add_argument("-u", "--ucloud_ip",
	              help="Undercloud ip address",
		      dest="ucloud_ip")
    parser.add_argument("-o", "--output_file",
                      help="Environment file to create, default is /home/stack/templates/ciscoaci_containers.yaml",
                      dest='output_file', default='/home/stack/templates/ciscoaci_containers.yaml')
    parser.add_argument("-c", "--container",
                      help="Containers to build, comma separated, default is all", dest='containers_tb', default='all')
    parser.add_argument("-s", "--upstream",
                      help="Upstream registry to pull base images from, eg. registry.access.redhat.com/rhosp13, defaults to registry.access.redhat.com/rhosp13",
                      default='registry.redhat.io/rhosp-rhel8',
                      dest='upstream_registry')
    parser.add_argument("-d", "--destregistry",
                      help="Destination registry to push to, eg: 1.100.1.1:8787/rhosp13",
                      dest='destination_registry')
    parser.add_argument("-r", "--regseparator",
                      help="Upstream registry separator for images, eg. '/' for normal upstream registrys (default). Will be added between upstream registry name and container name. Use '_' for satellite based registries.",
                      default="/",
                      dest='regseparator')
    parser.add_argument("-t", "--tag", help="tag for images, defaults to current timestamp",
                      default=timestamp, dest='tag')
    parser.add_argument("--force", help="Override check for md5sum mismatch",
	              dest='force', action='store_true')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--aci_repo_file",
                      dest='aci_repo_file',
		      type=extant_file,
		      metavar="FILE",
                      help="Path to yum repoistory file, which describes the repository which provides ACI plugin rpm files.\n If you want this script to create a repository on undercloud, please use the -z option to provide path to openstack-aci-rpms-repo tar file downloaded from cisco website")
    group.add_argument("-z", "--aci_rpm_repo_tar_file",
                      dest='repo_tar_file',
		      type=extant_file,
		      metavar="FILE",
                      help="Path to openstack-aci-rpms-repo tar file. This will be use to create a local yum repository on undercloud")
    options = parser.parse_args()


    current_user = getpass.getuser()
    current_grp = grp.getgrgid(pwd.getpwnam('stack').pw_gid).gr_name

    if not options.ucloud_ip:
       ucloud_ip = determine_ucloud_ip()
       if ucloud_ip == 1:
          print("Unable to determine undercloud ip. Please use -u option to specify")
          sys.exit(1)
    else:
          ucloud_ip = options.ucloud_ip

    if options.repo_tar_file:
       m=md5()
       with open(options.repo_tar_file, 'rb') as fh:
         data = fh.read()
       m.update(data)
       md5sum = m.hexdigest()

       with open('/opt/ciscoaci-tripleo-heat-templates/tools/dist_md5sum') as fh:
           expected_md5sum = fh.read()

       if not (md5sum == expected_md5sum.strip()):
          if not options.force:
             print("md5sum of provided tar file does not match with expected. Use --force to disable this check'")
             sys.exit(1)


       os.system("sudo rm -rf /opt/cisco_aci_repo")
       os.system("sudo /usr/bin/mkdir -p /opt/cisco_aci_repo")
       os.system("sudo chown {0} /opt/cisco_aci_repo".format(current_user))
       os.system("sudo chgrp {0} /opt/cisco_aci_repo".format(current_grp))
       tf = tarfile.open(options.repo_tar_file)
       tf.extractall('/opt/cisco_aci_repo')
       repotext = """
[acirepo]
name=aci repo
baseurl=file:///opt/cisco_aci_repo
enabled=1
gpgcheck=0
       """ 

       license_text = """
         Copyright 2020 Cisco Systems, Inc.
  
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

""" 
       os.system("sudo rm -rf /var/lib/image-serve/v2/__acirepo")
       os.system("sudo mkdir -p /var/lib/image-serve/v2/__acirepo")
       os.system("cp /opt/cisco_aci_repo/ciscoaci-puppet-* /var/lib/image-serve/v2/__acirepo")
       os.system("createrepo /var/lib/image-serve/v2/__acirepo")
    else:
       with open(options.aci_repo_file, 'r') as fh:
          repotext = fh.read()

    pushurl = None
    if options.destination_registry:
        pushurl = options.destination_registry
    else:
        cmd = "openstack tripleo container image list -f json"
        print("Running cmd '%s' to get local registry" % cmd)
        output = subprocess.check_output(shlex.split(cmd))
        jl = json.loads(output)
        for el in jl:
           if re.search('ironic', el['Image Name']):
              rg = re.search('^docker://([^/]*)' , el['Image Name'])
              if rg:
                 pushurl = "%s/ciscoaci" % rg.groups()[0]
              else:
                 print("Unable to determine local registry")
                 sys.exit(1)
              break
    if pushurl == None:
        print("Unable to determine local registry")
        sys.exit(1)

    container_array = {
        'horizon': {
            "rhel_container": "openstack-horizon",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install python3-openstack-dashboard-gbp",
                         "mkdir -p /usr/lib/heat",
                         "cp /usr/share/openstack-dashboard/openstack_dashboard/enabled/_*gbp* /usr/lib/python3.6/site-packages/openstack_dashboard/local/enabled"],
            "osd_param_name": ["ContainerHorizonImage"],
            "summary":"This is Ciscoaci modified Horizon container",
            "description":"This will be deployed on the controller  nodes",

        },
        'heat': {
            "rhel_container": "openstack-heat-engine",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install python3-openstack-heat-gbp python3-gbpclient",
                         "mkdir -p /usr/lib/heat",
                         "cp -r /usr/lib/python3.6/site-packages/gbpautomation /usr/lib/heat"],
            "osd_param_name": ["ContainerHeatEngineImage"],
            "summary":"This is Ciscoaci modified HeatEngine container",
            "description":"This will be deployed on the controller  nodes",
        },
        'neutron-server': {
            "rhel_container": "openstack-neutron-server",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install python3-apicapi python3-neutron-opflex-agent libmodelgbp python3-openstack-neutron-gbp ciscoaci-puppet python3-gbpclient python3-aci-integration-module "],
            "osd_param_name": ["ContainerNeutronApiImage", "ContainerNeutronConfigImage"],
            "summary":"This is Ciscoaci modified Neutron API container",
            "description":"This will be deployed on the controller  nodes",
        },
        'ciscoaci-lldp': {
            "rhel_container": "openstack-neutron-server",
            "aci_container": "openstack-ciscoaci-lldp",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install python3-aci-integration-module python3-neutron-opflex-agent ciscoaci-puppet ethtool python3-apicapi lldpd "],
            "osd_param_name": ["ContainerCiscoLldpImage"],
            "user": 'root',
            "summary":"This is Ciscoaci LLDP container",
            "description":"This will be deployed on the controller and compute nodes",
        },
        'ciscoaci-aim': {
            "rhel_container": "openstack-neutron-server",
            "aci_container": "openstack-ciscoaci-aim",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install python3-apicapi ciscoaci-puppet python3-aci-integration-module python3-neutron-opflex-agent python3-openstack-neutron-gbp python3-gbpclient ",
                         "update-crypto-policies --set LEGACY"],
            "osd_param_name": ["ContainerCiscoAciAimImage", "ContainerCiscoAciAimConfigImage"],
            "user": 'root',
            "summary":"This is Ciscoaci AIM container",
            "description":"This will be deployed on the controller nodes",
        },
        'opflex-agent': {
            "rhel_container": "openstack-neutron-openvswitch-agent",
            "aci_container": "openstack-ciscoaci-opflex",
            "packages": [],
            "run_cmds": ["yum --releasever=8.2 -y install opflex-agent opflex-agent-renderer-openvswitch noiro-openvswitch-lib noiro-openvswitch-otherlib ciscoaci-puppet ethtool python3-neutron-opflex-agent python3-apicapi python3-openstack-neutron-gbp lldpd os-net-config"],
            "osd_param_name": ["ContainerOpflexAgentImage"],
            "user": 'root',
            "summary":"This is Ciscoaci Opflex Agent container",
            "description":"This will be deployed on the controller and compute nodes",
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
        build_containers(ucloud_ip, options.upstream_registry, options.regseparator, pushurl,
              options.tag, container, container_array[container], repotext, license_text)

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
