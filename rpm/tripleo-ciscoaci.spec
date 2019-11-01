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
mkdir -p $RPM_BUILD_ROOT/var/www/html
cp -r * $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates
chmod a+x $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates/*
cp -r  $RPM_BUILD_ROOT/opt/ciscoaci-tripleo-heat-templates/rpms $RPM_BUILD_ROOT/var/www/html/acirepo
createrepo $RPM_BUILD_ROOT/var/www/html/acirepo

%post

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
/opt/ciscoaci-tripleo-heat-templates
/var/www/html/acirepo

