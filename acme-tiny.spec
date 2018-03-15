%global commit		5a7b4e79bc9bd5b51739c0d8aaf644f62cc440e6
%global shortcommit	5a7b4e7
%global checkout	20160810git%{shortcommit}

%if 0%{?rhel} >= 5 && 0%{?rhel} < 7
%global use_systemd 0
%else
%global use_systemd 1
%endif

%if 0%{?fedora}
# Explicity require python3 on Fedora to help track which packages 
# no longer need python2.
%global use_python3 1
%else
%global use_python3 0
%endif

Name:		acme-tiny
Version:	0.1
Release:	11.%{checkout}%{?dist}
Summary:	Tiny auditable script to issue, renew Let's Encrypt certificates

Group:		Applications/Internet
License:	MIT
URL:		https://github.com/diafygi/acme-tiny
Source0:	https://github.com/diafygi/%{name}/archive/%{commit}.tar.gz#/%{name}-%{shortcommit}.tar.gz
Source1:	acme-tiny-sign.sh
Source2:	cert-check.py
Source3:	acme.conf
Source4:	lets-encrypt-x3-cross-signed.pem
Source5:	acme-tiny.cron
Source6:	acme-tiny.timer
Source7:	acme-tiny.service
Source8:	README-fedora.md
# Fetch and include intermediate cert(s), too.
Patch0:		acme-tiny-chain.patch

Requires:	openssl
Requires(pre): shadow-utils
%if %{use_systemd}
# systemd macros are not defined unless systemd is present
BuildRequires: systemd
%{?systemd_requires}
%else
Requires:	cronie
%endif
BuildArch:	noarch
%if 0%{?fedora} > 22
Suggests: httpd, mod_ssl, nginx
Enhances: httpd, mod_ssl, nginx
%endif

%description
This is a tiny, auditable script that you can throw on your server to issue and
renew Let's Encrypt certificates. Since it has to be run on your server and
have access to your private Let's Encrypt account key, I tried to make it as
tiny as possible (currently less than 200 lines). The only prerequisites are
python and openssl.  

Well, that and a web server - but then you only need this with a web server.
This package adds a simple directory layout and timer service that runs
acme_tiny on installed CSRs as the acme user for privilege separation.

%prep
%setup -q -n %{name}-%{commit}
%patch0 -p1 -b .chain
cp -p %{SOURCE1} %{SOURCE2} %{SOURCE8} .
%if %{use_python3}
sed -i.old -e '1,1 s/python$/python3/' *.py
%endif
# Fix new agreement
sed -i 's#letsencrypt.org/documents/LE-SA.*#letsencrypt.org/documents/LE-SA-v1.2-November-15-2017.pdf",#' acme_tiny.py

%build

%install
mkdir -p %{buildroot}/var/www/challenges
mkdir -p %{buildroot}%{_sysconfdir}/httpd/conf.d
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}%{_libexecdir}/%{name}
mkdir -p %{buildroot}%{_sharedstatedir}/acme/{private,csr,certs}
chmod 0700 %{buildroot}%{_sharedstatedir}/acme/private

install -m 0755 acme-tiny-sign.sh %{buildroot}%{_libexecdir}/%{name}/sign
install -m 0755 acme_tiny.py %{buildroot}%{_sbindir}/acme_tiny
ln -sf acme_tiny %{buildroot}%{_sbindir}/acme-tiny
ln -sf %{_libexecdir}/%{name}/sign %{buildroot}%{_sbindir}/acme-tiny-sign
install -m 0755 cert-check.py %{buildroot}%{_sbindir}/cert-check
install -m 0644 %{SOURCE3} %{buildroot}%{_sysconfdir}/httpd/conf.d
install -m 0644 %{SOURCE4} %{buildroot}%{_sharedstatedir}/acme
%if %{use_systemd}
mkdir -p %{buildroot}%{_unitdir}
install -pm 644	 %{SOURCE6} %{buildroot}%{_unitdir}
install -pm 644	 %{SOURCE7} %{buildroot}%{_unitdir}
%else
mkdir -p %{buildroot}%{_sysconfdir}/cron.d
install -m 0644 %{SOURCE5} %{buildroot}%{_sysconfdir}/cron.d/acme-tiny
%endif

%pre
getent group acme > /dev/null || groupadd -r acme
getent passwd acme > /dev/null || /usr/sbin/useradd -g acme \
	-c "Tiny Auditable ACME Client" \
	-r -d %{_sharedstatedir}/acme -s /sbin/nologin acme
exit 0

%if %{use_systemd}

%post
%systemd_post acme-tiny.service acme-tiny.timer

%postun
%systemd_postun_with_restart acme-tiny.service acme-tiny.timer

%preun
%systemd_preun acme-tiny.service acme-tiny.timer

%endif

%files
%{!?_licensedir:%global license %%doc}
%license LICENSE
%doc README.md README-fedora.md
%attr(0755,acme,acme) /var/www/challenges
%attr(-,acme,acme) %{_sharedstatedir}/acme
%{_libexecdir}/%{name}
%config(noreplace) %{_sysconfdir}/httpd/conf.d/acme.conf
%if %{use_systemd}
%{_unitdir}/*
%else
%config(noreplace) %{_sysconfdir}/cron.d/acme-tiny
%endif
/usr/sbin/acme_tiny
/usr/sbin/acme-tiny
/usr/sbin/acme-tiny-sign
/usr/sbin/cert-check

%changelog
* Fri Mar 16 2018 Tristan Cacqueray <tdecacqu@redhat.com> 0.1-11.20160810git5a7b4e7
- Fix agreement url

* Mon Aug 22 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-10.20160810git5a7b4e7
- Fix cert writable check in sign script
- More tips in README-fedora.md

* Mon Aug 22 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-9.20160810git5a7b4e7
- Use %%{systemd_requires}
- Remove unneeded cronie, python dependencies
- Add acme-tiny.timer to systemd scriptlets
- Add README-fedora.md
- acme_tiny: Fix --chain patch for python2.6 (el6)
- acme_tiny: Suppress traceback on error

* Sun Aug 21 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-8
- Add use_systemd flag to use systemd timer and enable on Fedora and epel7
- Enable use_python3 flag for Fedora (but not epel7).

* Sat Aug 20 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-7
- sign: Actually use the new --chain flag
- cron: Make days to expiration explicit
- spec: Set file modes with install
- acme.conf: mark as config

* Fri Aug 19 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-6
- Python3 fixes for cert-check
- acme-tiny: Update patch to leave default behavior unchanged
- make /var/lib/acme readable by all except private

* Thu Aug 11 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-5
- sign: Use tmp output to avoid wiping existing cert on error
- acme_tiny: get intermediate cert from acme protocol

* Thu Aug 11 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-4
- Fix path of acme_tiny and make days explicit in sign script
- Add crontab

* Wed Aug 10 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-3
- Add global acme httpd conf
- Append intermediate certs, add current lets-encrypt intermediate cert

* Tue Aug  9 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-2
- add private, csr, certs directories
- add sign script suitable for cron

* Mon Aug  8 2016 Stuart D. Gathman <stuart@gathman.org> 0.1-1
- Initial RPM
