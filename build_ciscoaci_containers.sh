#!/bin/bash -eux

function build_heat_engine_image() {
    rm -rf ${CONTAINER_BUILD_DIR}
    mkdir -p ${CONTAINER_BUILD_DIR}
   
    cp /var/www/html/acirepo/openstack-heat-gbp-*.rpm ${CONTAINER_BUILD_DIR}/
    cp /var/www/html/acirepo/python-gbpclient-*.rpm ${CONTAINER_BUILD_DIR}/

    cd ${CONTAINER_BUILD_DIR}

    cat > Dockerfile <<_EOFF
    FROM ${LOCAL_REGISTRY_ADDRESS}/openstack-heat-engine:${UPSTREAM_TAG}
    MAINTAINER Cisco Systems
    LABEL name="rhosp12/openstack-heat-engine-ciscoaci" vendor="Cisco Systems" version="12.0" release="1"
    USER root
    COPY openstack-heat-gbp-*.rpm /tmp/
    COPY python-gbpclient-*.rpm /tmp/
    RUN rpm -ihv /tmp/*.rpm --nodeps
    RUN mkdir -p /usr/lib/heat
    RUN cp -r /usr/lib/python2.7/site-packages/gbpautomation /usr/lib/heat
_EOFF

    sudo docker build ./ -t ${CISCOACI_TAG}
    IMAGE_ID=`sudo docker images -q ${CISCOACI_TAG}`
    
    # tag latest build image and push to local registry
    sudo docker tag ${IMAGE_ID} ${LOCAL_REGISTRY_ADDRESS}/openstack-heat-engine-ciscoaci:${CISCOACI_TAG}
    sudo docker push ${LOCAL_REGISTRY_ADDRESS}/openstack-heat-engine-ciscoaci:${CISCOACI_TAG}
}

function build_horizon_image() {
    
    # recreate workspace for container build
    rm -rf ${CONTAINER_BUILD_DIR}
    mkdir -p ${CONTAINER_BUILD_DIR}
    
    # copy required packages to build dir
    cp /var/www/html/acirepo/openstack-dashboard-gbp-*.rpm ${CONTAINER_BUILD_DIR}/
    cp /var/www/html/acirepo/python-django-horizon-gbp-*.rpm ${CONTAINER_BUILD_DIR}/
    cp /var/www/html/acirepo/python-gbpclient-*.rpm ${CONTAINER_BUILD_DIR}/
    
    cd ${CONTAINER_BUILD_DIR}
    
    cat > Dockerfile <<EOF
    FROM ${LOCAL_REGISTRY_ADDRESS}/openstack-horizon:${UPSTREAM_TAG}
    MAINTAINER Cisco Systems
    LABEL name="rhosp12/openstack-horizon-ciscoaci" vendor="Cisco Systems" version="12.0" release="1"
    # switch to root and install a custom RPM, etc.
    USER root
    COPY openstack-dashboard-gbp-*.rpm /tmp/
    COPY python-django-horizon-gbp-*.rpm /tmp/
    COPY python-gbpclient-*.rpm /tmp/
    RUN rpm -ivh /tmp/*.rpm
    RUN cp /usr/share/openstack-dashboard/openstack_dashboard/enabled/_*gbp* /usr/lib/python2.7/site-packages/openstack_dashboard/local/enabled/
    #RUN cp -r /usr/lib/python2.7/site-packages/gbpui /usr/lib/python2.7/site-packages
    #RUN cp -r /usr/lib/python2.7/site-packages/gbpclient /usr/lib/python2.7/site-packages
    # switch the container back to the default user (NOT)
    # doing this has permission denied error during startup. skip it.
    # USER horizon
EOF
    
    sudo docker build ./ -t ${CISCOACI_TAG}
    IMAGE_ID=`sudo docker images -q ${CISCOACI_TAG}`
    
    # tag latest build image and push to local registry
    sudo docker tag ${IMAGE_ID} ${LOCAL_REGISTRY_ADDRESS}/openstack-horizon-ciscoaci:${CISCOACI_TAG}
    sudo docker push ${LOCAL_REGISTRY_ADDRESS}/openstack-horizon-ciscoaci:${CISCOACI_TAG}
}

CONTAINER_BUILD_DIR='/tmp/openstack_ciscoaci_containers'
CISCOACI_TAG='12.0.1'
# container tag_id used to deploy overcloud
UPSTREAM_TAG=`sudo openstack overcloud container image tag discover \
    --image registry.access.redhat.com/rhosp12/openstack-base:latest \
    --tag-from-label version-release`
    
# local registry address to push image
LOCAL_REGISTRY_ADDRESS=`docker images | grep -v redhat.com | grep -o '^.*rhosp12' | sort -u`
build_horizon_image 
build_heat_engine_image


cat > /home/stack/templates/cisco_containers.yaml<<__EOF
parameter_defaults:
   DockerHorizonImage: ${LOCAL_REGISTRY_ADDRESS}/openstack-horizon-ciscoaci:${CISCOACI_TAG}
   DockerHeatEngineImage: ${LOCAL_REGISTRY_ADDRESS}/openstack-heat-engine-ciscoaci:${CISCOACI_TAG}
__EOF
