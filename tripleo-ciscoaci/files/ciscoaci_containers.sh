#!/bin/bash
set -eu

# Process Args, use defaults for common case
CISCOACI_YAML=${1:-'/home/stack/templates/cisco_containers.yaml'}
CISCOACI_RPMDIR=${2:-'/var/www/html/acirepo'}
SCRIPT_NAME=$(basename $0)

# functions to build images
function build_tag_push() {
    CONTAINER_DIR=$1
    CONTAINER_NAME=$2
    (
        cd ${CONTAINER_DIR}
        sudo docker build ./ -t ${CISCOACI_TAG}
        IMAGE_ID=`sudo docker images -q ${CISCOACI_TAG}`
        sudo docker tag ${IMAGE_ID} ${LOCAL_REGISTRY_ADDRESS}/${CONTAINER_NAME}:${CISCOACI_TAG}
        sudo docker push ${LOCAL_REGISTRY_ADDRESS}/${CONTAINER_NAME}:${CISCOACI_TAG}
    )
}

function build_heat_engine_image() {
    # create the build dir
    CONTAINER_BUILD_DIR=$(mktemp -d /tmp/ciscoaci_XXXX)
    cp ${CISCOACI_RPMDIR}/openstack-heat-gbp-*.rpm ${CONTAINER_BUILD_DIR}
    cp ${CISCOACI_RPMDIR}/python-gbpclient-*.rpm ${CONTAINER_BUILD_DIR}
    cat > ${CONTAINER_BUILD_DIR}/Dockerfile <<EOF
        FROM registry.access.redhat.com/rhosp12/openstack-heat-engine:${UPSTREAM_TAG}
        MAINTAINER Cisco Systems
        LABEL name="rhosp12/openstack-heat-engine-ciscoaci" vendor="Cisco Systems" version="12.0" release="1"
        USER root
        COPY openstack-heat-gbp-*.rpm /tmp
        COPY python-gbpclient-*.rpm /tmp
        RUN rpm -ihv /tmp/*.rpm --nodeps
        RUN mkdir -p /usr/lib/heat
        RUN cp -r /usr/lib/python2.7/site-packages/gbpautomation /usr/lib/heat
EOF

    # build, tag and push latest build image and push to local registry
    build_tag_push ${CONTAINER_BUILD_DIR} openstack-heat-engine-ciscoaci
    rm -rf ${CONTAINER_BUILD_DIR}
}

function build_horizon_image() {
    # create the build dir
    CONTAINER_BUILD_DIR=$(mktemp -d /tmp/ciscoaci_XXXX)
    cp ${CISCOACI_RPMDIR}/openstack-dashboard-gbp-*.rpm ${CONTAINER_BUILD_DIR}
    cp ${CISCOACI_RPMDIR}/python-django-horizon-gbp-*.rpm ${CONTAINER_BUILD_DIR}
    cp ${CISCOACI_RPMDIR}/python-gbpclient-*.rpm ${CONTAINER_BUILD_DIR}
    cat > ${CONTAINER_BUILD_DIR}/Dockerfile <<EOF
        FROM registry.access.redhat.com/rhosp12/openstack-horizon:${UPSTREAM_TAG}
        MAINTAINER Cisco Systems
        LABEL name="rhosp12/openstack-horizon-ciscoaci" vendor="Cisco Systems" version="12.0" release="1"
        USER root
        COPY openstack-dashboard-gbp-*.rpm /tmp
        COPY python-django-horizon-gbp-*.rpm /tmp
        COPY python-gbpclient-*.rpm /tmp
        RUN rpm -ivh /tmp/*.rpm
        RUN cp /usr/share/openstack-dashboard/openstack_dashboard/enabled/_*gbp* /usr/lib/python2.7/site-packages/openstack_dashboard/local/enabled
EOF

    # build, tag and push latest build image and push to local registry
    build_tag_push ${CONTAINER_BUILD_DIR} openstack-horizon-ciscoaci
    rm -rf ${CONTAINER_BUILD_DIR}
}

function create_cisco_yaml() {
    cat > ${CISCOACI_YAML} <<EOF
parameter_defaults:
   DockerHorizonImage: ${LOCAL_REGISTRY_ADDRESS}/openstack-horizon-ciscoaci:${CISCOACI_TAG}
   DockerHeatEngineImage: ${LOCAL_REGISTRY_ADDRESS}/openstack-heat-engine-ciscoaci:${CISCOACI_TAG}
EOF
}

# main()
echo ""
echo "Running as: ${SCRIPT_NAME} ${CISCOACI_YAML} ${CISCOACI_RPMDIR}"
echo ""

# Local variables
LOCAL_REGISTRY_ADDRESS=$(docker images | grep -v redhat.com | grep -o '^.*rhosp12' | sort -u)
UPSTREAM_TAG=$(sudo openstack overcloud container image tag discover \
    --image registry.access.redhat.com/rhosp12/openstack-base:latest \
    --tag-from-label version-release)
CISCOACI_TAG=${UPSTREAM_TAG}

build_horizon_image
build_heat_engine_image
create_cisco_yaml

echo ""
echo "Created Openstack director env file: ${CISCOACI_YAML}"
echo "Please include '${CISCOACI_YAML}' as the last env file when deploying OSD"
echo ""
