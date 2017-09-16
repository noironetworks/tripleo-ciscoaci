Name:           tripleo-ciscoaci
Version:        11.0
Release:        %{?release}%{!?release:1}
Summary:        Files for ACI tripleO patch
License:        ASL 2.0
Group:          Applications/Utilities
Source0:        tripleo-ciscoaci.tar.gz
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       libguestfs-tools createrepo

%define debug_package %{nil}

%description
This package contains files that are required for patch tripleO to support ACI

%prep
%setup -q -n tripleo-ciscoaci

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/opt/tripleo-ciscoaci
cp -r * $RPM_BUILD_ROOT/opt/tripleo-ciscoaci
chmod a+x $RPM_BUILD_ROOT/opt/tripleo-ciscoaci/*

%post
rm -rf /var/www/html/acirepo
mkdir -p /var/www/html/acirepo
cp /opt/tripleo-ciscoaci/rpms/* /var/www/html/acirepo
createrepo /var/www/html/acirepo
cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe
cat /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml | awk '{print} /OS::TripleO::Services::NeutronCorePluginMidonet:/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::NeutronCorePluginCiscoAci: OS::Heat::None" }' | awk '{print} /OS::TripleO::Services::HeatEngine:/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::HeatApiCiscoAci: OS::Heat::None" }' | awk '{print} /OS::TripleO::Services::Horizon/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::HorizonCiscoAci: OS::Heat::None" }' > /tmp/.modified_registry
cp /tmp/.modified_registry /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml
cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
cat /usr/share/openstack-tripleo-heat-templates/roles_data.yaml | awk '{print} /- OS::TripleO::Services::Horizon/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::HorizonCiscoAci" }' | awk '{print} /- OS::TripleO::Services::HeatEngine/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::HeatCiscoAci" }' > /tmp/.modified_roles
cp /tmp/.modified_roles /usr/share/openstack-tripleo-heat-templates/roles_data.yaml
cp /opt/tripleo-ciscoaci/files/service-ciscoaci.yaml /opt/tripleo-ciscoaci/ciscoaci.yaml
cp /opt/tripleo-ciscoaci/files/service-ciscoaci-compute.yaml /opt/tripleo-ciscoaci/ciscoaci_compute.yaml
cp /opt/tripleo-ciscoaci/files/service-ciscoaci-horizon.yaml /opt/tripleo-ciscoaci/ciscoaci_horizon.yaml
cp /opt/tripleo-ciscoaci/files/service-ciscoaci-heat.yaml /opt/tripleo-ciscoaci/ciscoaci_heat.yaml
cp /opt/tripleo-ciscoaci/files/nodepre.yaml /opt/tripleo-ciscoaci/nodepre.yaml
cp /opt/tripleo-ciscoaci/files/example_ciscoaci.yaml /opt/tripleo-ciscoaci/example_ciscoaci.yaml

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
/opt/tripleo-ciscoaci/*

%postun
cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe /usr/share/openstack-tripleo-heat-templates/roles_data.yaml || true
cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml || true
