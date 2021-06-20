#!/bin/sh

cat /usr/share/openstack-tripleo-heat-templates/roles_data.yaml \
    | awk '{print} /- OS::TripleO::Services::NeutronOvsAgent/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::CiscoAciAIM" }' \
    | awk '{print} /- OS::TripleO::Services::CiscoAciAIM/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::CiscoAciLldp" }' \
    | awk '{print} /- OS::TripleO::Services::CiscoAciAIM/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::CiscoAciOpflexAgent" }' \
    | awk '{print} /- OS::TripleO::Services::ComputeNeutronOvsAgent/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::CiscoAciLldp" }' \
    | awk '{print} /- OS::TripleO::Services::ComputeNeutronOvsAgent/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::CiscoAciOpflexAgent" }'
