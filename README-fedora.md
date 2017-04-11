# acme-tiny Fedora package

The Fedora package for acme-tiny adds a tiny framework to make issuing
and renewing [Let's Encrypt](https://letsencrypt.org/) certificates 
convenient.  It does *not* alter your configuration in any way, other
than to drop an acme.conf apache config snippet into `/etc/httpd/conf.d`
and provide a systemd service.

If you want a package that tries to do everything for you as root,
consider the `certbot` package.

The ACME protocol will work with other certificate authorities, but
acme-tiny is currently hardwired to use letencrypt.org - which is
also currently the only ACME certificate authority recognized in
most browsers.

These instructions assume you are using letsencrypt for the first time
with this acme-tiny package.  For example, you should not already have
an account key for the domains it will manage.  If you do, see README.md
for instructions on converting it.  Put any existing account key in
PEM format in `/var/lib/acme/private`, readable by the acme user (only!).

## The web server must already serve your domains on HTTP

If you cannot access your web domains locally with commands like 
`curl` and `wget`, then this framework won't work.  Acme-tiny will work with
any web server package, but if you are not using apache (httpd package), you
must provide the equivalent of `/etc/httpd/conf.d/acme.conf` to map
`/var/www/challenges` to the ACME URL location.  The web server can even
be on a remote machine - provided you have somehow arranged for it to
serve files from `/var/www/challenges` (perhaps via NFS).  

If you are using Apache, and restrict access to `<location "/">`, then this
will override the acme.conf global config snippet, and you must explicitly
make the ACME URL (http://your.domain.here/.well-known/acme-challenge/)
publicly accessible.

## Put your CSRs in `/var/lib/acme/csr`

You can use existing CSRs, or generate a new one using openssl.  Put
all CSRs to be issued and renewed by acme-tiny in `/var/lib/acme/csr`.
I like to symlink the CSRs into /var/lib/acme/csr, just make sure the acme
user can read them (and follow the symlink).  The details for openssl are
beyond the scope of this documentation, but this should work for creating a
certificate for a single domain:
```
cd /etc/pki/tls
ln -s /var/lib/acme/csr .
openssl req -new -nodes -keyout private/your.domain.key \
	-out csr/your.domain.csr
chmod 0400 private/your.domain.key
```
If you have an existing key, replace  `-nodes -keyout` with `-key`.
The default openssl config will ask you for data, be sure to give the
domain you will be serving when it asks for "Common Name".  It is possible
to cover multiple domains with a single certificate using openssl.  First, add
a section to the end of `/etc/pki/tls/openssl.cnf` defining your extension:
```
[MYSERV]
subjectAltName=DNS:your.domain,DNS:www.your.domain
```
Then add `-reqexts MYSERV` to the openssl command line.  One of the domains
must match the common name. 

Make sure the CSR can be read by the acme user.

## Issue the certificate

The timer service in acme-tiny will check the certificate for all CSRs in csr
every 24 hours, and issue or renew the certificate if it is missing or about to
expire (in 7 days by default).  You don't have to wait for the timer, however.
Use 
```
systemctl start acme-tiny
```
to run the service now.  The certificate should appear in `/var/lib/acme/certs`,
and errors will be in journalctl.  Alternatively (and on EL6), run
`/usr/libexec/acme-tiny/sign` as the acme user, and errors will go
to your terminal.

## Use the certificate

The default httpd config uses a self-signed localhost certificate for https.
Edit `/etc/httpd/conf.d/ssl.conf` and change `SSLCertificateFile` and
`SSLCertificateChainFile` to `/var/lib/acme/certs/your.domain.crt` (or use a
symlink to /etc/pki/tls/certs).  Change `SSLCertificateKeyFile` to
`/etc/pki/tls/private/your.domain.key`.  

Obviously, you can change the locations to suit your sysadmin tastes.

Some SSL apps, like dovecot, require SSL certificates to be tagged in selinux.
```
semanage fcontext -a -f 'all files' -t cert_t '/var/lib/acme/certs(/.*)?'
restorecon -rv /var/lib/acme/certs
```
The above will permanently change the selinux tag to work with dovecot
and other apps.  

Sendmail is a special problem - it insists that any certificates it loads be
only writable by root.  This is at odds with the privilege separation of the
acme user.  (Obviously, the private key must be accessible only by root.)  You
can, of course, copy the crt file to /etc/pki/tls/certs as root and change the
mode.  But this has to be done every time the cert is renewed.  You can
install `incron` to do this.  After installing, create `/etc/incron.d/acme`
with the line
```
/var/lib/acme/certs/mail.crt IN_MOVED_TO cp $@ /etc/pki/tls/certs
```
where `mail.crt` is the certificate sendmail will use.  Sendmail
can then load it from /etc/pki/tls/certs and be happy.  This also
solves the file context problem if you add lines for other certificates.
You might wonder why we don't simply supply an acme incrontab as part
of the package with a wildcard, for example:
```
/var/lib/acme/certs/*.crt IN_MOVED_TO cp $@ /etc/pki/tls/certs
```
The answer is that incron is insecure, and very nasty things can be
done by putting shell meta characters (including semicolon and quote!) in
filenames that then become part of a command run as root.  The first example
above uses a fixed filename, so that is safe.  Complain to incron
upstream - they need an option to use a simple execvpe instead of
using the shell.  Then it would at least be possible to carefully
handle [malicious names](https://www.xkcd.com/327/).  

## Virtual Hosts

Most web servers can handle multiple logical web hosts - configuring that is
beyond the scope of this document.  Each virtual host may need to have its own
certificate for SSL.  They can all share the same key file (see above for
how to use an existing key for certificate requests), or use different keys.
Put all the CSRs in /var/lib/acme/csr and the acme-tiny service will keep them
all renewed.  This also works for certificates used by other SSL applications,
such as dovecot, sendmail, jabberd, or znc.
