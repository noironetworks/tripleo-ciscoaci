Name:           tripleo-ciscoaci
Version:        10.3
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

if [ "$1" = "1" ]; then

   #install scenario
   cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave
   cat /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml | awk '{print} /OS::TripleO::Services::NeutronCorePluginMidonet:/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::NeutronCorePluginCiscoAci: OS::Heat::None" }' | awk '{print} /OS::TripleO::Services::HeatEngine:/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::HeatApiCiscoAci: OS::Heat::None" }' | awk '{print} /OS::TripleO::Services::Horizon/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "OS::TripleO::Services::HorizonCiscoAci: OS::Heat::None" }' > /tmp/.modified_registry
   cp /tmp/.modified_registry /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml
   cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave
   cat /usr/share/openstack-tripleo-heat-templates/roles_data.yaml | awk '{print} /- OS::TripleO::Services::Horizon/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::HorizonCiscoAci" }' | awk '{print} /- OS::TripleO::Services::HeatEngine/{ print substr($0,1,match($0,/[^[:space:]]/)-1) "- OS::TripleO::Services::HeatCiscoAci" }' > /tmp/.modified_roles
   cp /tmp/.modified_roles /usr/share/openstack-tripleo-heat-templates/roles_data.yaml

elif [ "$1" = "2" ]; then

   #upgrade scenario
   echo ""
   #to recover cases when postun was wrong before this bug fix
   if [[ -e /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe ]]; then 
      if [[ ! -z $(grep "CiscoAci" "/usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe") ]]; then
         #the safe file has patch, i.e, it was there so that upgrade from buggy to fixed postun wont print a warning
         #this is case of upgrade from 1st version of fixed postun to later
         #do nothing
         echo ""
      else
        #safe file does not have patch, case where upgrade is from buggy to first version of fixed postun
        cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave
        cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe
      fi
   fi

   if [[ -e /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe ]]; then
      if [[ ! -z $(grep "CiscoAci" "/usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe") ]]; then
         #the safe file has patch, i.e, it was there so that upgrade from buggy to fixed postun wont print a warning
         #this is case of upgrade from 1st version of fixed postun to later
         #do nothing
         echo ""
      else
        #safe file does not have patch, case where upgrade is from buggy to first version of fixed postun
        cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave
        cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
      fi
   fi
   #/bin/rm -f /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
   #/bin/rm -f /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe
fi

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
if [ "$1" = "0" ]; then
   #uninstall scenario
   
   #remove any old naming safe files. They will exist during after first upgrade from buggy postun
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe

   [[ -e /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave ]] && cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave /usr/share/openstack-tripleo-heat-templates/roles_data.yaml 
   [[ -e /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave ]] && cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml 
elif [ "$1" = "1" ]; then
   #upgrade
   echo ""
   #remove any old naming safe files. They will exist during after first upgrade from buggy postun
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe
fi
