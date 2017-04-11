#!/usr/bin/python
from __future__ import print_function
from sys import stderr

import subprocess, time, calendar, os, getopt

def usage():
  print("""Usage: cert-check [options] files ...
	-h,--help	this message
	-q,--quiet	do not print cert files needing (re)newing
	-d n,--days=n	days before expiration to renew (default 7)
Succeeds only if all certs exist and are more than <days> from expiration.""",
        file=stderr)
  return 2

def main(argv):
  days = 7	# days ahead to 
  quiet = False

  try:
    opts,args = getopt.getopt(argv,'hqd:',['days=','quiet','help'])
  except getopt.GetoptError as err:
    # print help information and exit:
    print(err,file=stderr) # prints something like "option -a not recognized"
    return usage()

  for opt,val in opts:
    if opt in ('-h','--help'):
      return usage()
    if opt in ('-q','--quiet'):
      quiet = True
    if opt in ('-d','--days'):
      try:
        days = int(val)
      except:
        return usage()
      
  now = time.time()
  soon = now + days * 24 * 60 * 60
  rc = 0

  for fn in args:
      try:
          size = os.path.getsize(fn)
      except:
          size = 0
      if size == 0:
          if not quiet: print(fn)
          rc += 1
          continue
      proc = subprocess.Popen(
          ["openssl", "x509", "-in", fn, "-noout", "-enddate"],
          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      out, err = proc.communicate()
      if proc.returncode != 0:
          raise IOError("{1}: OpenSSL Error: {0}".format(err,fn))
      t = time.strptime(out.decode(),'notAfter=%b %d %H:%M:%S %Y GMT\n')
      t = calendar.timegm(t)
      if soon > t: 
          if not quiet: print(fn)
          rc += 1
  return rc > 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv[1:]))
