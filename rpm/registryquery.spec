%global module_name registryquery

Name: 			python-%{module_name}
Version: 		0.7.0
Release: 		1%{?dist}
License: 		Internal Licence
Summary: 		API interface to IP Studio service registry

Source0: 		%{module_name}-%{version}.tar.gz
Source1:                ips-regquery.service
Source2:                ips-api-nmosquery.conf

BuildArch:      noarch

BuildRequires:	python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-flask              >= 0.10.2
BuildRequires:  python-requests           >= 0.9.3
BuildRequires:  python-ws4py
BuildRequires:	systemd

Requires:       python
Requires:       python-setuptools
Requires:       python-flask              >= 0.10.2
Requires:       python-requests           >= 0.9.3
Requires:       python-ws4py
Requires:       ips-etcd
Requires:       ips-reverseproxy-common
Requires:       nmoscommon
%{?systemd_requires}

%description
Part of the second iteration of the IP-Studio service discovery layer.
Provides an API interface to the shared service registry via HTTP and WebSockets.

%prep
%setup -n %{module_name}-%{version}

%build
%{py2_build}

%install
%{py2_install}

# Install config file
install -d -m 0755 %{buildroot}%{_sysconfdir}/ips-regquery
install -D -p -m 0644 etc/ips-regquery/config.json %{buildroot}%{_sysconfdir}/ips-regquery/config.json

# Install systemd unit file
install -D -p -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/ips-regquery.service

# Install Apache config file
install -D -p -m 0644 %{SOURCE2} %{buildroot}%{_sysconfdir}/httpd/conf.d/ips-apis/ips-api-nmosquery.conf

# Create log dir
mkdir -p %{buildroot}/%{_localstatedir}/log/ipstudio

%pre
getent group ipstudio >/dev/null || groupadd -r ipstudio
getent passwd ipstudio >/dev/null || \
    useradd -r -g ipstudio -d /dev/null -s /sbin/nologin \
        -c "IP Studio user" ipstudio

%post
touch %{_localstatedir}/log/ipstudio/regquery_state.log
chown ipstudio:ipstudio %{_localstatedir}/log/ipstudio/regquery_state.log
%systemd_post ips-regquery.service
systemctl reload httpd
systemctl start ips-regquery

%preun
systemctl stop ips-regquery

%clean
rm -rf %{buildroot}

%files
%{_bindir}/nmosquery

%{_unitdir}/%{name}.service

%{python2_sitelib}/%{module_name}
%{python2_sitelib}/%{module_name}-%{version}*.egg-info

%defattr(-,ipstudio, ipstudio,-)
#%config(noreplace) %{_sysconfdir}/ips-regquery
%config(noreplace) %{_sysconfdir}/ips-regquery/config.json
%config %{_sysconfdir}/httpd/conf.d/ips-apis/ips-api-nmosquery.conf

%ghost %{_localstatedir}/log/ipstudio/regquery_state.log



%changelog
* Tue Apr 25 2017 Sam Nicholson <sam.nicholson@bbc.co.uk> - 0.1.0-1
- Initial packaging for RPM
