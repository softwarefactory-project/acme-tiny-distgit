#!/bin/sh

if test "$(id -u)" -eq 0; then
  echo "Do not run as root!"
  exit 2
fi

DAYS="${1:-7}"

cd /var/lib/acme

if ! test -s private/account.key; then
  touch private/account.key
  chmod 0600 private/account.key
  openssl genrsa 4096 >private/account.key
fi

for csr in csr/*.csr; do
  test -s "$csr" || continue
  test -r "$csr" || continue
  crt="${csr%%.csr}"
  tmp="certs/${crt##csr/}.tmp"
  crt="certs/${crt##csr/}.crt"
  if test -s "$crt" && /usr/sbin/cert-check --days="$DAYS" "$crt"; then
    continue
  fi
  test -w "$crt" || test ! -e "$crt" || continue
  echo acme_tiny --account-key private/account.key --csr "$csr" \
	--acme-dir /var/www/challenges/ --chain --out "$crt"

  if /usr/sbin/acme_tiny --account-key private/account.key --csr "$csr" \
	--acme-dir /var/www/challenges/ --chain > "$tmp"; then
	mv "$tmp" "$crt"
  else
	test -e "$tmp" && test ! -s "$tmp" && rm "$tmp"
  fi
  # append intermediate certs
  #cat *.pem >>"$crt"
done
