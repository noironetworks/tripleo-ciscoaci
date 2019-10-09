Name:           tripleo-ciscoaci
Version:        13.0
Release:        %{?release}%{!?release:1}
Summary:        Files for ACI tripleO patch
License:        ASL 2.0
Group:          Applications/Utilities
Source0:        tripleo-ciscoaci.tar.gz
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       createrepo

%define debug_package %{nil}

%description
This package contains files that are required for patch tripleO to support ACI

%prep
%setup -q -n tripleo-ciscoaci

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates
cp -r * $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates
chmod a+x $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates/*

%post
if [ "$1" = "1" ]; then

   echo ""

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
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
/opt/ciscoaci-tripleo-heat-templates/*

%postun
/bin/rm -rf /var/www/html/acirepo
if [ "$1" = "0" ]; then
   #uninstall scenario
   
   #remove any old naming safe files. They will exist during after first upgrade from buggy postun
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe

   if [[ -e /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave ]]; then
      cp /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.rpmsave /usr/share/openstack-tripleo-heat-templates/roles_data.yaml 
   fi
   if [[ -e /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave ]]; then
      cp /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.rpmsave /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml 
   fi
   /bin/rm -rf /opt/ciscoaci-tripleo-heat-templates
elif [ "$1" = "1" ]; then
   #upgrade
   echo ""
   #remove any old naming safe files. They will exist during after first upgrade from buggy postun
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/roles_data.yaml.safe
   /bin/rm -f /usr/share/openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.j2.yaml.safe
fi

%posttrans
rm -rf /var/www/html/acirepo
mkdir -p /var/www/html/acirepo
cp /opt/ciscoaci-tripleo-heat-templates/rpms/* /var/www/html/acirepo
createrepo /var/www/html/acirepo
